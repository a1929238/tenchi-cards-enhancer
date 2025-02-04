from PyQt6.QtWidgets import QApplication, QWidget, QCheckBox, QHBoxLayout, QButtonGroup, QSizePolicy
from PyQt6.QtCore import pyqtSignal


class BindingCheckbox(QWidget):
    # 状态改变信号
    stateChanged = pyqtSignal(int)  # 发送 0, 1, 2 表示状态

    def __init__(self, parent=None):
        super().__init__(parent)

        self.unbind_checkbox = QCheckBox("不绑")
        self.bind_checkbox = QCheckBox("绑定")

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.unbind_checkbox)
        self.button_group.addButton(self.bind_checkbox)
        self.button_group.setExclusive(False)  # 允许同时选中

        # 连接信号槽，确保至少选择一种情况，并发送 stateChanged 信号
        self.bind_checkbox.stateChanged.connect(self._on_state_changed)
        self.unbind_checkbox.stateChanged.connect(self._on_state_changed)

        layout = QHBoxLayout()
        layout.addWidget(self.unbind_checkbox)
        layout.addWidget(self.bind_checkbox)
        layout.setSpacing(0)  # 设置间距为0
        layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0 (左，上，右，下)
        self.setLayout(layout)

        # 大小策略
        self.setFixedSize(100, 22)

        # 默认选择“不绑”
        self.unbind_checkbox.setChecked(True)

    def _on_state_changed(self, state):
        """内部方法，处理状态改变，确保至少选择一个并发送信号。"""
        self.ensure_selection(state)
        self.stateChanged.emit(self.get_state())

    def ensure_selection(self, state):
        """确保至少选择一个复选框。"""
        bind_checked = self.bind_checkbox.isChecked()
        unbind_checked = self.unbind_checkbox.isChecked()

        if not bind_checked and not unbind_checked:
            # 如果两者都未选中，根据最后改变的状态选择另一个
            if self.sender() == self.bind_checkbox:
                self.unbind_checkbox.setChecked(True)
            else:
                self.bind_checkbox.setChecked(True)

    def get_state(self):
        """返回当前状态，用数字表示: 0, 1, 2."""
        bind_checked = self.bind_checkbox.isChecked()
        unbind_checked = self.unbind_checkbox.isChecked()

        if bind_checked and not unbind_checked:
            return 1  # 绑定
        elif not bind_checked and unbind_checked:
            return 0  # 不绑
        elif bind_checked and unbind_checked:
            return 2  # 绑定与不绑
        else:
            return 1  # 默认为不绑 (实际不会触发，因为 ensure_selection 会保证至少选中一个)

    def set_state(self, state):
        """
        :param state: int 0,1,2
        根据给定的状态设置复选框状态.
        """
        if state == 0:  # 不绑
            self.bind_checkbox.setChecked(False)
            self.unbind_checkbox.setChecked(True)
        elif state == 1:  # 绑定
            self.bind_checkbox.setChecked(True)
            self.unbind_checkbox.setChecked(False)
        elif state == 2:  # 绑定与不绑
            self.bind_checkbox.setChecked(True)
            self.unbind_checkbox.setChecked(True)
        else:
            self.bind_checkbox.setChecked(False)
            self.unbind_checkbox.setChecked(True)  # 默认不绑


# 示例用法
if __name__ == '__main__':
    app = QApplication([])
    window = BindingCheckbox()
    window.show()
    app.exec()
