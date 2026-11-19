"""独立进程先初始化项目路径；原冻结审计和物理记录不变。"""
from reflection.__main__ import bootstrap
bootstrap()
from rb_audit import main


if __name__ == '__main__':
    main()
