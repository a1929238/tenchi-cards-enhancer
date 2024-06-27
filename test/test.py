import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtGui import QPalette, QColor

def main():
    app = QApplication(sys.argv)

    # 创建一个调色板，设置浅色主题
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))        # 窗口背景颜色
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))    # 窗口文本颜色
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))          # 输入框的背景颜色
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F0F0F0")) # 辅助背景颜色
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))   # 工具提示的背景颜色
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))   # 工具提示的文本颜色
    palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))          # 一般文本颜色
    palette.setColor(QPalette.ColorRole.Button, QColor("#E0E0E0"))        # 按钮背景颜色
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))    # 按钮文本颜色
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF0000"))    # 亮文本颜色
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3399FF"))     # 高亮颜色
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF")) # 高亮文本颜色

    # 设置禁用状态下的按钮文本颜色
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#888888"))

    app.setPalette(palette)

    window = QWidget()
    layout = QVBoxLayout()

    enabled_button = QPushButton("Enabled Button")
    disabled_button = QPushButton("Disabled Button")
    disabled_button.setEnabled(False)

    layout.addWidget(enabled_button)
    layout.addWidget(disabled_button)

    window.setLayout(layout)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
