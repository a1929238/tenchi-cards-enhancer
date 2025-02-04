from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic
from module.utils import resource_path
import sys
import os


class EditWindow(QWidget):
    closed = pyqtSignal()

    # 编辑窗口，编辑选定强化星级的主卡，副卡1，副卡2，副卡3的全部属性
    def __init__(self, enhance_level, parent=None):
        super().__init__()
        # 加载UI文件
        ui_path = resource_path('GUI/editwindow.ui')
        uic.loadUi(ui_path, self)
        # 拆解传入的对象名，弄出强化星级
        level = int(enhance_level.replace("E", ""))
        self.enhance_type = f'{level - 1}-{level}'

        # 给窗口设置标题
        self.setWindowTitle(f'强化类型： {self.enhance_type}')
        # 禁止调整窗口大小
        self.setFixedSize(self.size())
        # 如果有主窗口，将编辑窗口放在主窗口的左侧
        if parent:
            main_window_geom = parent.geometry()
            self.move(main_window_geom.left() - self.width(), main_window_geom.top())

    def closeEvent(self, event):
        self.closed.emit()  # 当窗口关闭时，发出关闭信号
        super().closeEvent(event)