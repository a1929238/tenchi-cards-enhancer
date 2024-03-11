import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QLabel, QComboBox, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from module.utils import resource_path

class MultiSelectComboBox(QWidget):
    recipeAdded = pyqtSignal(str)  # 添加配方时发出的信号
    recipeRemoved = pyqtSignal(str)  # 删除配方时发出的信号
    recipeClicked = pyqtSignal(str)  # 配方被点击时发出的信号
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # 创建一个 QListWidget
        self.listWidget = QListWidget(self)
        self.layout.addWidget(self.listWidget)

        # 连接 itemClicked 信号到 onItemClicked 方法
        self.listWidget.itemClicked.connect(self.onItemClicked)

        # 创建一个 QComboBox，叫做recipeSelectBox
        self.recipeSelectBox = QComboBox(self)
        self.recipeSelectBox.insertItem(0, "哈，请选择你的配方吧。")  # 在索引 0 处插入占位项
        self.recipeSelectBox.setCurrentIndex(0)  # 设置当前选中的索引为占位项
        self.recipeSelectBox.currentIndexChanged.connect(self.onComboBoxChanged)  # 连接信号
        self.layout.addWidget(self.recipeSelectBox)

    def addItem(self, text):
        # 创建一个 QListWidgetItem
        item = QListWidgetItem()

        # 存储文本到 QListWidgetItem
        item.setData(Qt.ItemDataRole.UserRole, text)

        # 创建一个 QWidget 作为 QListWidgetItem 的自定义部件
        widget = QWidget()

        # 创建水平布局
        hbox = QHBoxLayout()

        # 创建标签和删除按钮
        label = QLabel(text)
        btnDelete = QPushButton()

        # 给按钮设置图案
        btnDelete.setIcon(QIcon(resource_path("items/icon/垃圾桶.png")))

        # 设置按钮和标签的样式表
        label.setStyleSheet("font-size: 14px;")
        btnDelete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)  # 设置按钮样式表
        btnDelete.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # 设置按钮大小策略
        btnDelete.clicked.connect(lambda: self.deleteItem(item))

        # 添加标签和按钮到布局
        hbox.addWidget(label)
        hbox.addStretch()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(btnDelete)
        hbox.setSpacing(10)  # 设置间距

        # 设置 QWidget 的布局
        widget.setLayout(hbox)

        # 将自定义的 QWidget 设置为 QListWidgetItem 的子部件
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)

        # 发送添加配方信号,传出配方名
        self.recipeAdded.emit(text)
        

    def deleteItem(self, item):
        # 事先保留该 item 的文本
        text = item.data(Qt.ItemDataRole.UserRole)
        # 删除指定的 QListWidgetItem
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        # 发出删除项目的信号
        self.recipeRemoved.emit(text)
    
        

    def onComboBoxChanged(self, index):
        # 当 QComboBox 的选项改变时添加新的 QListWidgetItem
        text = self.recipeSelectBox.itemText(index)

        # 检查是否选择的是占位项
        if index == 0:
            return  # 如果是占位项，则不执行任何操作
        
        # 检查 QListWidget 中是否已经存在该文本的 item
        exists = False
        for i in range(self.listWidget.count()):
            if self.listWidget.item(i).data(Qt.ItemDataRole.UserRole) == text:
                exists = True
                break

        if not exists:
            # 如果不存在，则添加新的 item
            self.addItem(text)
    
    def onItemClicked(self, item):
        text = item.data(Qt.ItemDataRole.UserRole)
        # 发出单击项目的信号
        self.recipeClicked.emit(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MultiSelectComboBox()
    ex.show()
    sys.exit(app.exec())
