from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtCore import Qt

class ClickableSlot(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置鼠标悬停时的光标形状
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 设置提示
        self.setToolTip("点击删除当前槽位内容")
    
    def mousePressEvent(self, event):
        # 获得主窗口的实例
        main_window = self.get_main_window()
        # 获得自身的对象名
        name = self.objectName()
        # 根据对象名，删除并刷新槽位
        main_window.enhance_simulator.delete_slot(name)
        super().mousePressEvent(event)
    
    def get_main_window(self):
        # 递归地向上遍历父窗口直到找到 QMainWindow 实例
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent