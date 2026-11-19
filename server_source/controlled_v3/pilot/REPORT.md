# 受控噪声开发实验

状态：completed；完成 144/144 次任务。

|因素|方法|成功/任务|恢复/首次失败|无效输出|服务错误|
|---|---|---|---|---|---|
|clean|retry|5/8|0/3|0|0|
|clean|rule|6/8|1/3|1|0|
|clean|flash|7/8|2/3|1|0|
|layout|retry|2/8|0/6|0|0|
|layout|rule|5/8|3/6|0|0|
|layout|flash|4/8|2/6|0|0|
|sensor|retry|5/8|0/3|0|0|
|sensor|rule|6/8|1/3|1|0|
|sensor|flash|7/8|2/3|0|0|
|physics|retry|5/8|0/3|0|0|
|physics|rule|7/8|2/3|0|0|
|physics|flash|7/8|2/3|0|0|
|feedback|retry|5/8|0/3|0|0|
|feedback|rule|5/8|0/3|2|0|
|feedback|flash|6/8|1/3|0|0|
|mixed|retry|2/8|0/6|0|0|
|mixed|rule|3/8|1/6|1|0|
|mixed|flash|3/8|1/6|2|0|

全部为开发条件；未读取封存测试。反馈误差是模拟测量误差，错误类别和阶段仍是理想检测。
任务失败保留在分母；服务故障与无效回答单独统计。此报告不声明统计显著性。

同条件配对净增益（百分点）：
- clean/rule: 12.5，配对数 8
- clean/flash: 25.0，配对数 8
- layout/rule: 37.5，配对数 8
- layout/flash: 25.0，配对数 8
- sensor/rule: 12.5，配对数 8
- sensor/flash: 25.0，配对数 8
- physics/rule: 25.0，配对数 8
- physics/flash: 25.0，配对数 8
- feedback/rule: 0.0，配对数 8
- feedback/flash: 12.5，配对数 8
- mixed/rule: 12.5，配对数 8
- mixed/flash: 12.5，配对数 8
