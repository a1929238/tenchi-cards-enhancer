from PyQt6 import QtCore, QtWidgets
import win32gui

# 拖曳图片控件
class DraggableLabel(QtWidgets.QLabel):
    handleChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # 开启鼠标跟踪

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            # 获取鼠标释放时的全局位置
            cursor_pos = event.globalPosition().toPoint()
            # 获取当前位置的窗口句柄
            handle = win32gui.WindowFromPoint((cursor_pos.x(), cursor_pos.y()))
            self.handleChanged.emit(handle)