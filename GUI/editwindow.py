from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QGridLayout, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6 import uic

from GUI.SearchableComboBox import SearchableComboBox
from GUI.bindingcheckbox import BindingCheckbox
from module.utils import resource_path
import sys
import os
import qtawesome as qta


light_theme_css = """
/* 整个窗口的样式 */
#content_widget {
    background-color: #F0F8FF; /* 爱丽丝蓝 */
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}

/* 标题栏样式 */
#title_bar {
    background-color: #D1E9F7; /* 稍深的爱丽丝蓝 */
    color: #333333; /* 深灰色文本 */
    font-size: 14px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

#close_btn:hover {
    background-color: #F08080; /* 浅红色 */
    color: white;
    border-radius: 5px;
}

#close_btn {
     border: none; /* 移除按钮边框 */
}
"""

dark_theme_css = """
/* 整个窗口的样式 */
#content_widget {
    background-color: rgb(33, 41, 54);
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}

/* 标题栏样式 */
#title_bar {
    background-color: #283148;
    color: #F0F8FF;
    font-size: 14px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

#close_btn:hover {
    background-color: #FF0000; /* 红色 */
    color: white;
    border-radius: 5px;
}

#close_btn {
    border: none;  /* 移除按钮边框 */
}

/* 标签样式 */
QLabel {
    color: #DDDDDD; /* 浅灰色文本 */
}
"""


class EditWindow(QWidget):
    closed = pyqtSignal()

    # 编辑窗口，编辑选定强化星级的主卡，副卡1，副卡2，副卡3的全部属性
    def __init__(self, enhance_level, theme, parent=None):
        super().__init__()
        # 拆解传入的对象名，弄出强化星级
        level = int(enhance_level.replace("E", ""))
        self.enhance_type = f'{level - 1}-{level}'

        self.theme = theme
        self.parent_widget = parent  # 保存父窗口的引用

        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 设置窗口背景透明，以便实现圆角效果
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置初始窗口大小
        self.resize(300, 300)

        # 鼠标拖动相关变量
        self.dragging = False
        self.offset = QPoint()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.content_widget = QWidget(self)
        self.content_widget.setObjectName("content_widget")

        # 添加自定义标题栏
        self.title_bar = QLabel(self)
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setText(f'强化类型： {self.enhance_type}')
        self.title_bar.setAlignment(Qt.AlignCenter)
        # 让标题栏扁一些
        self.title_bar.setFixedHeight(40)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.content_widget)

        # 使用qtawesome美化关闭按钮
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("close_btn")
        if self.theme == "light":
            self.close_btn.setIcon(qta.icon("fa.close", color='black'))
        else:
            self.close_btn.setIcon(qta.icon("fa.close", color='white'))
        self.close_btn.clicked.connect(self.close)

        title_bar_layout = QGridLayout(self.title_bar)
        title_bar_layout.setContentsMargins(0, 0, 0, 0)
        title_bar_layout.addWidget(self.close_btn, 0, 0, alignment=Qt.AlignmentFlag.AlignRight)

        # 初始化控件
        self.grid_layout = QGridLayout(self.content_widget)  # 使用 self.grid_layout
        self.setLayout(self.grid_layout)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)  # 上边距增加，给标题栏留空间

        # 创建并添加控件到布局
        labels = ["主卡", "副卡1", "副卡2", "副卡3", "四叶草"]
        for i in range(5):
            # 添加标签
            label = QLabel(labels[i] + ":", self)
            self.grid_layout.addWidget(label, i, 0)
            if i < 4:
                recipe_box = SearchableComboBox(None, self)
                recipe_box.setObjectName(f"card_box{i}")
                setattr(self, f'card_box{i}', recipe_box)
                self.grid_layout.addWidget(recipe_box, i, 1)
            if i == 4:
                clover_name_label = QLabel("四叶草", self)
                clover_name_label.setObjectName(f"clover_name_label")
                setattr(self, f'clover_name_label', clover_name_label)
                self.grid_layout.addWidget(clover_name_label, i, 1)
            bind_checkbox = BindingCheckbox(self)
            bind_checkbox.setObjectName(f"bind_btn{i}")
            setattr(self, f'bind_btn{i}', bind_checkbox)
            self.grid_layout.addWidget(bind_checkbox, i, 2)

        if theme == "light":
            self.setStyleSheet(light_theme_css)
        elif theme == "dark":
            self.setStyleSheet(dark_theme_css)

    def showEvent(self, event):
        """
        重写showEvent方法，在窗口显示时调整位置
        """
        super().showEvent(event)
        if self.parent_widget:
            # 获取父窗口左上角的全局坐标
            parent_pos = self.parent_widget.mapToGlobal(self.parent_widget.rect().topLeft())
            # 计算编辑窗口应该放置的位置（紧贴父窗口左侧）
            x = parent_pos.x() - self.width() - 2  # 减去边框宽度
            y = parent_pos.y()
            self.move(x, y)

    def closeEvent(self, event):
        self.closed.emit()  # 当窗口关闭时，发出关闭信号
        super().closeEvent(event)

    # 重写鼠标事件以实现窗口拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 只有在标题栏上点击才允许拖动
            if self.title_bar.geometry().contains(event.pos()):
                self.dragging = True
                self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
