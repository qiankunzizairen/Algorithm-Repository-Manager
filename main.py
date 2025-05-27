#!/usr/bin/env python3
# main.py
"""
启动入口：先初始化数据库与表，再加载 PyQt GUI 应用。
"""
import sys
import config
import db
from gui import App
from PyQt5.QtWidgets import QApplication

def main():
    # 1. 初始化数据库与默认账号
    try:
        db.init_db()
        print("数据库初始化完成。")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return

    # 2. 创建 QApplication，然后再创建并显示主窗口
    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(qt_app.exec_())

if __name__ == '__main__':
    main()