from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtCore import Qt

CLICKABLE_LABEL_LIGHT = """
    ClickableLabel {
        background-color: rgb(170, 255, 255);  
        border: 1px solid #dcdcdc; 
        padding: 2px;
        border-radius: 8px;  
    }
"""

CLICKABLE_LABEL_DARK = """
    ClickableLabel {
        background-color: #283148;  
        border: 1px solid #333333; 
        padding: 2px;
        border-radius: 8px;  
    }
"""

CLICKABLE_LABEL_HOVER_LIGHT = """
    ClickableLabel {
        color: #0057b7;
        text-decoration: underline; 
        background-color: #e6e6e6; 
        border: 1px solid #c3c3c3;
        padding: 2px;
        border-radius: 8px;
    }
"""

CLICKABLE_LABEL_HOVER_DARK = """
    ClickableLabel {
        color: #add8e6; /* 浅蓝色，类似于原有的 #0057b7 在深色背景下的感觉 */
        text-decoration: underline;
        background-color: #333333; /* 深灰，代替浅灰 #e6e6e6 */
        border: 1px solid #555555; /* 较亮的深灰边框，代替 #c3c3c3 */
        padding: 2px;
        border-radius: 8px;
    }
"""

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit_window = None  # 用于存储当前打开的编辑窗口

        palette = self.palette()
        self.theme = 'dark' if palette.color(QPalette.ColorRole.Window).lightness() < 128 else 'light'

        # 设置鼠标悬停时的光标形状
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 设置默认样式
        if self.theme == 'dark':
            self.setStyleSheet(CLICKABLE_LABEL_DARK)
        else:
            self.setStyleSheet(CLICKABLE_LABEL_LIGHT)

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
        if self.theme == 'dark':
            self.setStyleSheet(CLICKABLE_LABEL_HOVER_DARK)
        else:
            self.setStyleSheet(CLICKABLE_LABEL_HOVER_LIGHT)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标不悬停时恢复默认样式
        if self.theme == 'dark':
            self.setStyleSheet(CLICKABLE_LABEL_DARK)
        else:
            self.setStyleSheet(CLICKABLE_LABEL_LIGHT)
        super().leaveEvent(event)

    def get_main_window(self):
        # 递归地向上遍历父窗口直到找到 QMainWindow 实例
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent
