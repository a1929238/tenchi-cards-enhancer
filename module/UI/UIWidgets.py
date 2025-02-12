from PyQt6.QtWidgets import QComboBox

clover_list = [
            "无",
            "1级",
            "2级",
            "3级",
            "4级",
            "5级",
            "6级",
            "超能",
            "SS",
            "SSS",
            "SSR",
        ]

class CloverComboBox(QComboBox):
    """
    负责四叶草的选项框
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        for clover in clover_list:
            self.addItem(clover)
