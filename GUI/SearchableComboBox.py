import sys

import qtawesome as qta
from PyQt6.QtCore import QRect, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QListWidget,
    QDialog,
    QVBoxLayout,
    QStyle,
    QProxyStyle,
    QStyleOptionComboBox,
    QLabel,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QPushButton
)


class SearchableComboBox(QComboBox):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        if items:
            self.addItems(items)
        self.setStyle(CustomComboBoxStyle(self))
        # 默认放大镜图标色
        self.theme_line_color = QColor(240, 240, 240)
        # 根据主题变色
        self.theme = self.set_style()

    def mousePressEvent(self, event):
        if self.is_search_icon_clicked(event.pos()):
            self.open_search_dialog()
        else:
            super().mousePressEvent(event)

    def is_search_icon_clicked(self, pos: QPoint) -> bool:
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        search_icon_rect = self.get_search_icon_rect(option)
        return search_icon_rect.contains(pos)

    def get_search_icon_rect(self, option):
        style = self.style()
        arrow_rect = style.subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxArrow,
            self
        )
        icon_size = 16
        margin = 4
        return QRect(
            arrow_rect.left() - icon_size - margin,
            arrow_rect.center().y() - icon_size // 2,
            icon_size,
            icon_size
        )

    def open_search_dialog(self):
        dialog = SearchDialog([self.itemText(i) for i in range(self.count())], self.theme, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_item:
            self.setCurrentText(dialog.selected_item)

    def set_style(self):
        """设置样式"""
        palette = self.palette()
        if palette.color(QPalette.ColorRole.Window).lightness() < 128:
            theme = "dark"
        else:
            theme = "light"
        self.theme_line_color = QColor(240, 240, 240) if theme == "dark" else QColor(15, 15, 15)
        self.update()  # 触发重绘
        return theme


class CustomComboBoxStyle(QProxyStyle):
    def __init__(self, combo_box):
        super().__init__()
        self._combo_box = combo_box

    def drawComplexControl(self, control, option, painter, widget):
        super().drawComplexControl(control, option, painter, widget)
        if control == QStyle.ComplexControl.CC_ComboBox:
            arrow_rect = self.subControlRect(
                QStyle.ComplexControl.CC_ComboBox,
                option,
                QStyle.SubControl.SC_ComboBoxArrow,
                widget
            )
            search_icon_rect = widget.get_search_icon_rect(option)  # 获取 QRect 对象
            # 使用 qtawesome 创建 Font Awesome 图标
            search_icon = qta.icon(
                "fa5s.search",  # 使用 Font Awesome 5 Solid 的 search 图标
                color=self._combo_box.theme_line_color,  # 设置图标颜色
            )
            search_icon.paint(painter, search_icon_rect)  # 使用 QRect 对象绘制图标


class TitleBar(QWidget):
    windowMoved = pyqtSignal(QPoint)

    def __init__(self, title, theme, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)  # 减小高度
        self.mouse_pos = None
        self.theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)  # 调整左边距
        layout.setSpacing(0)

        self.title_label = QLabel(title)
        layout.addWidget(self.title_label)

        # 使用qtawesome美化关闭按钮
        self.close_btn = QPushButton()
        if self.theme == "light":
            self.close_btn.setIcon(qta.icon("fa.close", color='black'))
        else:
            self.close_btn.setIcon(qta.icon("fa.close", color='white'))
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.parent().reject)

        layout.addStretch()  # 添加伸缩，使关闭按钮靠右
        layout.addWidget(self.close_btn)

        self.set_stylesheet()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mouse_pos:
            delta = event.globalPosition().toPoint() - self.mouse_pos
            self.windowMoved.emit(delta)
            self.mouse_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def set_stylesheet(self):
        if self.theme == "light":
            bg_color = "#F0F8FF"  # AliceBlue
            text_color = "#333333"
            close_btn_hover_bg = "#E0E8EF"
        else:
            bg_color = "#283148"  # 深色调
            text_color = "#F0F8FF"
            close_btn_hover_bg = "#3A4860"

        self.setStyleSheet(f"""
            TitleBar {{
                background-color: {bg_color};
                border-top-left-radius: 8px; /* 圆角 */
                border-top-right-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 18px;
            }}
            QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background-color: {close_btn_hover_bg};
                 border-top-right-radius: 8px;
            }}
        """)


class SearchDialog(QDialog):
    def __init__(self, items, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        # 设置无标题栏窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 窗口大小
        self.resize(400, 400)

        self.selected_item = None

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 自定义标题栏
        self.title_bar = TitleBar("芙芙搜索栏~", theme, self)
        self.title_bar.windowMoved.connect(self.move_window)
        main_layout.addWidget(self.title_bar)

        # 内容区域
        content_widget = QWidget()
        if self.theme == "light":
            content_widget.setStyleSheet("""
            background-color: rgba(255, 255, 255, 240);
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            """)  # 白色，稍微透明
        else:
            content_widget.setStyleSheet("""
            background-color: rgba(33, 41, 54, 240);
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            """)  # 深色，稍微透明

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # 搜索框
        self.search_bar = QLineEdit(placeholderText="输入搜索关键词...")
        self.search_bar.setClearButtonEnabled(True)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.addItems(items)

        # 空状态提示
        self.empty_label = QLabel("没有找到匹配项")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()

        content_layout.addWidget(self.search_bar)
        content_layout.addWidget(self.list_widget)
        content_layout.addWidget(self.empty_label)

        main_layout.addWidget(content_widget)

        # 信号连接
        self.search_bar.textChanged.connect(self.filter_items)
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)
        self.list_widget.itemClicked.connect(self.select_item)

        self.set_stylesheet()

    def move_window(self, delta):
        self.move(self.pos() + delta)

    def filter_items(self, text):
        visible_count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            match = text.lower() in item.text().lower()
            item.setHidden(not match)
            if match:
                visible_count += 1
        self.empty_label.setVisible(visible_count == 0)

    def select_item(self):
        if selected := self.list_widget.currentItem():
            self.selected_item = selected.text()
            self.accept()

    def accept_selection(self):
        if selected := self.list_widget.currentItem():
            self.selected_item = selected.text()
        super().accept()

    def set_stylesheet(self):
        if self.theme == "light":
            search_bar_bg = "#F5F5F5"
            search_bar_border = "#E0E0E0"
            list_item_hover_bg = "#E0E8EF"
            text_color = "#333333"
            empty_label_color = "#777777"
            scrollbar_bg = "#F0F0F0"  # 滚动条背景色
            scrollbar_handle = "#C0C0C0"  # 滚动条滑块颜色
            scrollbar_handle_hover = "#A0A0A0"  # 鼠标悬停时滑块颜色
        else:
            search_bar_bg = "#313D4F"
            search_bar_border = "#4A5568"
            list_item_hover_bg = "#4A5568"
            text_color = "#F0F8FF"
            empty_label_color = "#AAAAAA"
            scrollbar_bg = "#333D4F"  # 滚动条背景色
            scrollbar_handle = "#5A677A"  # 滚动条滑块颜色
            scrollbar_handle_hover = "#7B889B"  # 鼠标悬停时滑块颜色

        self.setStyleSheet(f"""
            QDialog {{
                background-color: transparent;
                border-radius: 10px;
            }}
            QLineEdit {{
                background-color: {search_bar_bg};
                border: 1px solid {search_bar_border};
                border-radius: 10px;
                padding: 10px;
                color: {text_color};
                selection-background-color: #6CB2EB;
                font-size: 14px;
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {text_color};
                outline: none;
                border-radius: 10px;

            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {list_item_hover_bg};
            }}
            QListWidget::item:selected {{
                background-color: #6CB2EB;
                color: white;
            }}
            QLabel {{
                color: {empty_label_color};
                font-size: 14px;
            }}

            /* 滚动条样式 */
            QScrollBar:vertical {{
                background-color: {scrollbar_bg};
                width: 10px; /* 滚动条宽度 */
                margin: 0px 0px 0px 0px; /* 外边距 */
                border-radius: 5px; /* 圆角 */
            }}
            QScrollBar::handle:vertical {{
                background-color: {scrollbar_handle};
                min-height: 20px; /* 最小高度 */
                border-radius: 5px; /* 圆角 */
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {scrollbar_handle_hover}; /* 悬停颜色 */
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px; /* 隐藏上下箭头 */
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none; /* 隐藏上下箭头后面的区域 */
            }}
        """)


if __name__ == "__main__":
    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("现代化搜索组合框示例")
            self.resize(600, 400)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(40, 40, 40, 40)

            self.combo_box = SearchableComboBox([f"选项 {i:03d}" for i in range(1, 101)])
            layout.addWidget(QLabel("请选择项目:"))
            layout.addWidget(self.combo_box)
            layout.addStretch()


    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
