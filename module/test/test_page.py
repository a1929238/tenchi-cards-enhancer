import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QLabel

from module.core.GetImg import get_image
from module.test.test_units import test, get_pixel_position, img_save
from module.utils import resource_path


class TestPage(QtWidgets.QWidget):
    """继承自父窗口的测试分页"""

    def __init__(self, enhancer_instance):
        super().__init__()
        self.enhancer = enhancer_instance

        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # 测试按钮
        test_button = QtWidgets.QPushButton("测试按钮1")
        test_button.clicked.connect(test)
        layout.addWidget(test_button)

        # 创建坐标参数输入区域
        input_layout = QtWidgets.QHBoxLayout()

        # 各坐标输入控件
        input_layout.addWidget(QtWidgets.QLabel("X:"))
        self.x_input = QtWidgets.QLineEdit()
        input_layout.addWidget(self.x_input)

        input_layout.addWidget(QtWidgets.QLabel("Y:"))
        self.y_input = QtWidgets.QLineEdit()
        input_layout.addWidget(self.y_input)

        input_layout.addWidget(QtWidgets.QLabel("Width:"))
        self.width_input = QtWidgets.QLineEdit()
        input_layout.addWidget(self.width_input)

        input_layout.addWidget(QtWidgets.QLabel("Height:"))
        self.height_input = QtWidgets.QLineEdit()
        input_layout.addWidget(self.height_input)

        layout.addLayout(input_layout)

        # 截图按钮
        capture_btn = QtWidgets.QPushButton("截图")
        capture_btn.clicked.connect(self.capture_screen)
        layout.addWidget(capture_btn)

        # 放大镜组件
        self.note = QLabel("拖动这个生气的芙芙以获取鼠标在目标窗口的坐标")
        self.note.setWordWrap(True)  # 允许自动换行

        self.pointer = DraggablePointer()
        self.magnifier = Magnifier()  # 独立窗口，无父级

        # 将note和指针放在同一行
        pointer_layout = QtWidgets.QHBoxLayout()
        pointer_layout.addWidget(self.note, stretch=1)
        pointer_layout.addWidget(self.pointer, stretch=0)

        self.lbl_position = QLabel("当前位置：未获取")

        # 信号连接
        self.pointer.drag_started.connect(self.magnifier.show)
        self.pointer.drag_finished.connect(self.magnifier.hide)
        self.pointer.position_changed.connect(self.update_ui)

        # 添加组件到主布局
        layout.addLayout(pointer_layout)
        layout.addWidget(self.lbl_position)

    def update_ui(self, x, y):
        """更新界面和放大镜"""
        relative_x, relative_y = get_pixel_position(x, y)
        self.lbl_position.setText(f"当前位置：({relative_x}, {relative_y})")
        self.magnifier.update_view(x, y)  # 确保放大镜更新

    def capture_screen(self):
        """处理截图逻辑"""
        try:
            # 参数获取和截图逻辑保持不变
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())

            img = get_image(x, y, width, height)
            path = resource_path("module\\test\\test_image")
            img_name = f"{x}_{y}_{width}_{height}.png"
            print(f"已保存截图到{os.path.join(path, img_name)}")
            img_save(img, os.path.join(path, img_name))

        except ValueError:
            error_dialog = QtWidgets.QErrorMessage(self)
            error_dialog.setWindowTitle("输入错误")
            error_dialog.showMessage("请输入有效的整数数值")


class Magnifier(QLabel):
    """优化后的放大镜组件"""

    def __init__(self):
        super().__init__()  # 保持为独立窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 200)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 180); border-radius: 4px; border: 1px solid gray;")

    def update_view(self, x, y):
        """使用物理像素精确捕捉"""
        screen = QApplication.primaryScreen()
        capture_size = 10  # 实际捕捉10x10物理像素
        ratio = screen.devicePixelRatio()

        # 获取原始像素数据
        pixmap = screen.grabWindow(0,
                                   int((x - 5) * ratio),  # 中心点向左上偏移5像素
                                   int((y - 5) * ratio),
                                   int(capture_size * ratio),
                                   int(capture_size * ratio))

        # 创建放大后的画布（每个物理像素放大20倍）
        scaled = QPixmap(capture_size * 20, capture_size * 20)
        scaled.fill(Qt.GlobalColor.transparent)

        painter = QPainter(scaled)
        for i in range(capture_size):
            for j in range(capture_size):
                color = pixmap.toImage().pixelColor(int(i * ratio), int(j * ratio))
                painter.fillRect(i * 20, j * 20, 20, 20, color)

        # 绘制网格和中心线
        painter.setPen(QPen(QColor(0, 0, 0, 50), 1))
        for pos in range(0, 201, 20):
            painter.drawLine(pos, 0, pos, 200)
            painter.drawLine(0, pos, 200, pos)

        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawLine(100, 0, 100, 200)
        painter.drawLine(0, 100, 200, 100)
        painter.end()

        self.setPixmap(scaled)
        # 自动调整显示位置（避开屏幕边缘）
        screen_geo = screen.availableGeometry()
        if y + 220 > screen_geo.bottom():
            self.move(x - 220, y - 220)
        else:
            self.move(x + 20, y + 20)


class DraggablePointer(QLabel):
    """优化后的可拖拽指针"""
    position_changed = pyqtSignal(int, int)
    drag_started = pyqtSignal()
    drag_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(QPixmap(resource_path("items//icon//angry_furina.png")).scaled(32, 32))
        self.setFixedSize(32, 32)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self.position_changed.emit(global_pos.x(), global_pos.y())

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.drag_finished.emit()