from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtCore import Qt

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit_window = None  # 用于存储当前打开的编辑窗口

        # 设置鼠标悬停时的光标形状
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 设置默认样式
        self.setStyleSheet("""
            ClickableLabel {
                background-color: rgba(240, 248, 255, 0.6);
                border: 1px solid transparent;
                padding: 2px;
            }
        """)  # 默认样式为空

        # 设置工具提示
        self.setToolTip("点我一下试试~")

    def mousePressEvent(self, event):
        # 通过主窗口打开编辑窗口
        main_window = self.get_main_window()
        if main_window:
            main_window.open_edit_window(self.objectName())
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        # 鼠标悬停时的样式
        self.setStyleSheet("ClickableLabel { color: blue; text-decoration: underline; background-color: rgb(240, 248, 255); }")
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标不悬停时恢复默认样式
        self.setStyleSheet("""
            ClickableLabel {
                background-color: rgba(240, 248, 255, 0.6);
                border: 1px solid transparent;
                padding: 2px;
            }
        """)  # 恢复默认样式
        super().leaveEvent(event)

    def get_main_window(self):
        # 递归地向上遍历父窗口直到找到 QMainWindow 实例
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent