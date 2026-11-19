"""独立18824端口的4B精度诊断，不改变采集客户端配置。"""
from unittest.mock import patch
from stability.inspect_teacher import main


if __name__ == '__main__':
    with patch('stability.teacher.ENDPOINT', 'http://127.0.0.1:18824'):
        main()
