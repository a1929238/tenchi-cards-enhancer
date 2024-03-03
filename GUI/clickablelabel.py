from PyQt6.QtWidgets import QLabel, QMainWindow
from .editwindow import EditWindow

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit_window = None  # 用于存储当前打开的编辑窗口

    def mousePressEvent(self, event):
        # 通过主窗口打开编辑窗口
        main_window = self.get_main_window()
        if main_window:
            main_window.open_edit_window(self.objectName())
        super().mousePressEvent(event)

    def get_main_window(self):
        # 递归地向上遍历父窗口直到找到 QMainWindow 实例
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent