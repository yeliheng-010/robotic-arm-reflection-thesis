"""大模型调用层：ModelScope(OpenAI 兼容) + 磁盘缓存 + JSON 解析。

缓存的意义：
  * ModelScope API-Inference 有每日调用额度，批量实验必须节省调用；
  * 仿真场景是确定性的，相同输入（同一张图、同一段提示）在低温度下输出基本一致，
    缓存既保证实验可复现，也不改变方法之间的公平性。
可通过环境变量 REFLECTION_LLM_CACHE=0 关闭缓存。
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CACHE_PATH = os.path.join(ROOT_DIR, "logs", "reflection", "llm_cache.sqlite3")


class LLMServiceError(RuntimeError):
    """The model service could not supply a response after bounded retries."""


def _ensure_http_proxy():
    """httpx 不支持 socks:// 代理；若系统代理为 socks，则沿用 main_vlm.py 的 HTTP 代理设置。"""
    for key in ("all_proxy", "ALL_PROXY", "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        value = os.environ.get(key, "")
        if value.startswith("socks"):
            os.environ[key] = os.environ.get("REFLECTION_HTTP_PROXY", "http://127.0.0.1:7897")


def image_to_data_url(image: Union[np.ndarray, Image.Image, str], *, bgr: bool = True, max_side: int = 768) -> str:
    """ndarray(BGR)/PIL/路径 → JPEG data URL，并限制尺寸以控制 token 开销。"""
    if isinstance(image, str):
        if image.startswith("data:image/"):
            return image
        image = Image.open(image).convert("RGB")
    elif isinstance(image, np.ndarray):
        arr = image[:, :, ::-1] if (bgr and image.ndim == 3) else image
        image = Image.fromarray(np.ascontiguousarray(arr).astype(np.uint8)).convert("RGB")
    image = image.copy()
    image.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def strip_code_fences(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text or "", flags=re.I)
    return text.replace("```", "").strip()


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """从模型输出中取出第一个完整的 JSON 对象（容忍代码块与前后说明文字）。"""
    text = strip_code_fences(text)
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:i + 1], strict=False)
                        if isinstance(value, dict):
                            return value
                    except json.JSONDecodeError:
                        break
                    break
        start = text.find("{", start + 1)
    return None


class _ResponseCache:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, model TEXT, content TEXT, created_at REAL)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute("SELECT content FROM responses WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def put(self, key: str, model: str, content: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses(key, model, content, created_at) VALUES (?,?,?,?)",
                (key, model, content, time.time()),
            )
            self._conn.commit()

    def close(self):
        self._conn.close()


class LLMClient:
    """统一的多模态对话接口。统计调用次数/耗时，供实验报告使用。"""

    def __init__(self, model: Optional[str] = None, *, use_cache: Optional[bool] = None,
                 cache_path: str = DEFAULT_CACHE_PATH, temperature: float = 0.1):
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv(os.path.join(ROOT_DIR, ".env"))
        _ensure_http_proxy()
        api_key = (os.getenv("MODELSCOPE_API_KEY") or "").strip()
        base_url = (os.getenv("MODELSCOPE_BASE_URL") or "https://api-inference.modelscope.cn/v1").rstrip("/")
        if not api_key:
            raise RuntimeError("缺少 MODELSCOPE_API_KEY，请在 .env 中配置")
        self.model = model or os.getenv("REFLECTION_MODEL_ID") or os.getenv("MODELSCOPE_MODEL_ID", "Qwen/Qwen3.5-397B-A17B")
        self.temperature = temperature
        self._client = OpenAI(api_key=api_key, base_url=base_url,
                              timeout=float(os.getenv("REFLECTION_LLM_TIMEOUT", "45")), max_retries=0)
        if use_cache is None:
            use_cache = os.getenv("REFLECTION_LLM_CACHE", "1") != "0"
        self._cache = _ResponseCache(cache_path) if use_cache else None
        self.stats = {"calls": 0, "cache_hits": 0, "latency_s": 0.0}

    # ---- 底层 ----
    def _key(self, model: str, messages: Sequence[Dict[str, Any]], extra: Dict[str, Any]) -> str:
        payload = json.dumps({"model": model, "messages": messages, "extra": extra}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create(self, *, model: Optional[str] = None, messages: List[Dict[str, Any]],
               temperature: Optional[float] = None, max_tokens: Optional[int] = None,
               cache_tag: str = "") -> str:
        model = model or self.model
        temperature = self.temperature if temperature is None else temperature
        extra = {"temperature": temperature, "max_tokens": max_tokens, "tag": cache_tag}
        key = self._key(model, messages, extra)
        if self._cache is not None:
            hit = self._cache.get(key)
            if hit is not None:
                self.stats["cache_hits"] += 1
                return hit

        kwargs: Dict[str, Any] = dict(model=model, messages=messages, temperature=temperature,
                                      extra_body={"enable_thinking": False}, stream=True)
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        content = None
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            t0 = time.time()
            try:
                # ModelScope 的非流式接口会间歇性返回 HTTP 200 + choices=null，流式接口不受影响
                parts, chunks = [], 0
                for chunk in self._client.chat.completions.create(**kwargs):
                    chunks += 1
                    if chunk.choices:
                        parts.append(chunk.choices[0].delta.content or "")
                content = "".join(parts)
                if not content:
                    last_exc = RuntimeError(f"空响应（流式分片数={chunks}）")
            except Exception as exc:  # 网络抖动/限流时退避重试
                last_exc = exc
                content = None
                if "insufficient_quota" in str(exc):
                    break  # 当日额度用尽，重试只会继续失败
            self.stats["calls"] += 1
            self.stats["latency_s"] += time.time() - t0
            if content:
                break
            if attempt < 2 and "insufficient_quota" not in str(last_exc):
                # limit_burst_rate 要求平滑请求速率，退避要足够长
                burst = "limit_burst_rate" in str(last_exc)
                time.sleep((15.0 if burst else 2.0) * (attempt + 1))
        # 两次调用之间保持最小间隔，避免触发 ModelScope 的突发速率限制
        time.sleep(float(os.getenv("REFLECTION_LLM_MIN_INTERVAL", "1.5")))
        if not content:
            raise LLMServiceError(f"大模型调用失败：{last_exc}")
        if self._cache is not None:
            self._cache.put(key, model, content)
        return content

    def close(self):
        if self._cache is not None:
            self._cache.close()
        self._client.close()

    # ---- 便捷接口 ----
    def ask(self, prompt: str, *, images: Sequence[Any] = (), system: Optional[str] = None,
            max_tokens: Optional[int] = None, cache_tag: str = "") -> str:
        content: List[Dict[str, Any]] = [{"type": "image_url", "image_url": {"url": image_to_data_url(img)}}
                                         for img in images]
        content.append({"type": "text", "text": prompt})
        messages: List[Dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        return self.create(messages=messages, max_tokens=max_tokens, cache_tag=cache_tag)

    def ask_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        text = self.ask(prompt, **kwargs)
        data = extract_json_object(text)
        if data is None:
            # 再给一次机会，明确要求只输出 JSON
            text = self.ask(prompt + "\n\n只输出一个 JSON 对象，不要输出任何其他文字。",
                            **{**kwargs, "cache_tag": kwargs.get("cache_tag", "") + "#json-retry"})
            data = extract_json_object(text)
        if data is None:
            raise ValueError(f"模型输出无法解析为 JSON：{text[:300]}")
        return data


class _CachedCompletions:
    def __init__(self, owner: "LLMClient", default_model: str):
        self._owner = owner
        self._default_model = default_model

    def create(self, *, model=None, messages, temperature=None, max_tokens=None, **_ignored):
        content = self._owner.create(model=model or self._default_model, messages=messages,
                                     temperature=temperature, max_tokens=max_tokens, cache_tag="vision_agent")
        choice = type("Choice", (), {"message": type("Msg", (), {"content": content})()})()
        return type("Resp", (), {"choices": [choice]})()


class CachedOpenAIShim:
    """伪装成 openai.OpenAI，使 vision_agent 中已有的规划/定位调用也走缓存与统计。"""

    def __init__(self, owner: LLMClient):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _CachedCompletions(owner, owner.model)


def install_vision_agent_cache(client: LLMClient):
    """把 vision_agent 的模型客户端替换为带缓存的版本（不修改 vision_agent 源码）。"""
    import vision_agent

    shim = CachedOpenAIShim(client)
    vision_agent._get_client = lambda: (shim, client.model)
    os.environ.setdefault("PLANNER_PROVIDER", "modelscope")
