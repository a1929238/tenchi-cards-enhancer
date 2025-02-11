from PyQt6 import QtCore, QtWidgets, QtGui
import win32gui
import ctypes
from ctypes.wintypes import POINT

from module.utils import resource_path


# 拖曳图片控件
class DraggableLabel(QtWidgets.QLabel):
    handleChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # 开启鼠标跟踪
        self.dragging = False  # 添加一个标志来跟踪是否正在拖动
        self.float_window = None
        self.furina_movie = QtGui.QMovie(resource_path("items/icon/furina_shake.gif"))
        self.setMovie(self.furina_movie)
        self.furina_movie.start()
        self.float_window_timer = QtCore.QTimer(self)  # 创建计时器
        self.float_window_timer.setSingleShot(True)  # 设置计时器为单次触发
        self.float_window_timer.timeout.connect(self.closeFloatWindow)  # 连接超时信号到关闭窗口的槽

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True  # 设置拖动标志为True
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ClosedHandCursor))  # 更改鼠标样式
            self.createFloatWindow(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.dragging and self.float_window:
            # 更新悬浮窗口的位置
            cursor_pos = event.globalPosition().toPoint()
            self.float_window.move(cursor_pos.x() - self.float_window.width() // 2,
                                   cursor_pos.y() - self.float_window.height() // 2)
            self.float_window_timer.start(3000)  # 重置计时器，每次移动时给3秒时间

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = False  # 设置拖动标志为False
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))  # 恢复默认鼠标样式
            self.closeFloatWindow()  # 释放鼠标时关闭悬浮窗口
            # 获取鼠标释放时的全局位置
            cursor_x, cursor_y = self.get_physical_cursor_pos()
            # 获取当前位置的窗口句柄
            handle = win32gui.WindowFromPoint((cursor_x, cursor_y))
            self.handleChanged.emit(handle)

    def createFloatWindow(self, position):
        if self.float_window is None:
            self.float_window = QtWidgets.QDialog(None)  # 将父窗口设置为 None
            self.float_window.setWindowFlags(
                QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint)
            self.float_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
            self.float_window_layout = QtWidgets.QVBoxLayout(self.float_window)
            self.float_window_layout.setContentsMargins(0, 0, 0, 0)
            float_window_label = QtWidgets.QLabel()
            float_window_label.setMovie(self.furina_movie)
            self.float_window_layout.addWidget(float_window_label)
            self.float_window.setGeometry(position.x(), position.y(), self.width(), self.height())
            self.float_window.show()
            self.float_window_timer.start(3000)  # 启动计时器，3秒后关闭悬浮窗口

    def closeFloatWindow(self):
        if self.float_window:
            self.float_window.close()
            self.float_window = None
        self.float_window_timer.stop()  # 停止计时器

    def get_physical_cursor_pos(self):
        # 定义POINT结构
        pt = POINT()
        # 调用函数获取鼠标的物理位置
        ctypes.windll.user32.GetPhysicalCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
