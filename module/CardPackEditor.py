import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QInputDialog, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class CardPackEditor(QWidget):
    save_signal = pyqtSignal(dict)

    def __init__(self, card_packs=None):
        super().__init__()

        # 卡包数据,格式为{卡包名称:[卡片1,卡片2,etc]}
        if card_packs:
            self.card_packs = card_packs
        else:
            self.card_packs = {}

        # 主布局
        main_layout = QVBoxLayout()

        # 卡包名称编辑
        pack_name_layout = QHBoxLayout()
        self.pack_name_label = QLabel("卡包名称:")
        self.pack_name_edit = QLineEdit()
        # 添加卡包按钮
        self.add_pack_button = QPushButton("添加新的卡包")
        self.add_pack_button.clicked.connect(self.add_pack)
        # 修改卡包名称按钮
        self.modify_pack_button = QPushButton("修改当前卡包名")
        self.modify_pack_button.clicked.connect(self.modify_pack)
        pack_name_layout.addWidget(self.pack_name_label)
        pack_name_layout.addWidget(self.pack_name_edit)
        pack_name_layout.addWidget(self.add_pack_button)
        pack_name_layout.addWidget(self.modify_pack_button)

        # 当前选中卡包
        current_pack_layout = QHBoxLayout()
        self.current_pack_label = QLabel("当前选中卡包:")
        # 删除卡包按钮
        self.delete_pack_button = QPushButton("删除当前选中卡包")
        self.delete_pack_button.clicked.connect(self.delete_pack)
        current_pack_layout.addWidget(self.current_pack_label)
        current_pack_layout.addWidget(self.delete_pack_button)

        # 卡包列表
        self.pack_list_widget = QListWidget()
        # 初始化卡包列表
        if self.card_packs:
            self.pack_list_widget.addItems(self.card_packs.keys())
        self.pack_list_widget.itemClicked.connect(self.display_pack_contents)

        # 卡片列表
        self.card_list_widget = QListWidget()

        # 按钮布局
        button_layout = QHBoxLayout()

        # 卡片选择框
        self.card_select_label = QLabel("选择卡片:")
        self.card_select_box = QComboBox()
        # 添加卡片按钮
        self.add_card_button = QPushButton("添加卡片")
        self.add_card_button.clicked.connect(self.add_card)
        # 删除卡片按钮
        self.delete_card_button = QPushButton("删除选中卡片")
        self.delete_card_button.clicked.connect(self.delete_card)
        button_layout.addWidget(self.card_select_label)
        button_layout.addWidget(self.card_select_box)
        button_layout.addWidget(self.add_card_button)
        button_layout.addWidget(self.delete_card_button)
        # 保存卡包修改按钮
        self.save_pack_button = QPushButton("保存卡包配置")
        self.save_pack_button.clicked.connect(self.save_pack)

        # 主布局添加部件
        main_layout.addLayout(pack_name_layout)
        main_layout.addLayout(current_pack_layout)
        main_layout.addWidget(QLabel("卡包列表:"))
        main_layout.addWidget(self.pack_list_widget)
        main_layout.addWidget(QLabel("卡片列表:"))
        main_layout.addWidget(self.card_list_widget)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.save_pack_button)

        self.setLayout(main_layout)

    def add_pack(self):
        pack_name = self.pack_name_edit.text().strip()
        if pack_name and pack_name not in self.card_packs:
            self.card_packs[pack_name] = []
            self.pack_list_widget.addItem(pack_name)
            self.pack_name_edit.clear()
        else:
            QMessageBox.warning(self, "错误", "卡包名称无效或已存在")

    def delete_pack(self):
        current_item = self.pack_list_widget.currentItem()
        if current_item:
            pack_name = current_item.text()
            del self.card_packs[pack_name]
            self.pack_list_widget.takeItem(self.pack_list_widget.row(current_item))
            self.card_list_widget.clear()
            # 更新当前选中卡包
            current_item = self.pack_list_widget.currentItem()
            if current_item:
                self.current_pack_label.setText("当前选中卡包:" + current_item.text())
            else:
                self.current_pack_label.setText("当前选中卡包:无")

    def modify_pack(self):
        current_item = self.pack_list_widget.currentItem()
        if current_item:
            old_pack_name = current_item.text()
            pack_name = self.pack_name_edit.text().strip()
            if pack_name and pack_name not in self.card_packs:
                self.card_packs[pack_name] = self.card_packs.pop(old_pack_name)
                current_item.setText(pack_name)
                self.current_pack_label.setText("当前选中卡包: " + pack_name)
            else:
                QMessageBox.warning(self, "谔谔", "卡包名称为空或已存在")

    def add_card(self):
        current_item = self.pack_list_widget.currentItem()
        if current_item:
            card_name = self.card_select_box.currentText().split("-")[0]
            if card_name and card_name not in self.card_packs[current_item.text()]:
                self.card_packs[current_item.text()].append(card_name)
                self.card_list_widget.addItem(card_name)
            else:
                QMessageBox.warning(self, "谔谔", "卡片名已存在")
        else:
            QMessageBox.warning(self, "哎呦", "你还没选择卡包呢！")

    def delete_card(self):
        current_item = self.pack_list_widget.currentItem()
        card_item = self.card_list_widget.currentItem()
        if current_item and card_item:
            pack_name = current_item.text()
            card_name = card_item.text()
            self.card_packs[pack_name].remove(card_name)
            self.card_list_widget.takeItem(self.card_list_widget.row(card_item))

    def display_pack_contents(self):
        current_item = self.pack_list_widget.currentItem()
        if current_item:
            pack_name = current_item.text()
            # 修改当前卡包显示
            self.current_pack_label.setText("当前选中卡包: " + pack_name)
            self.card_list_widget.clear()
            self.card_list_widget.addItems(self.card_packs[pack_name])

    def save_pack(self):
        # 保存卡包，将卡包配置文件在信号中发送到主窗口
        self.save_signal.emit(self.card_packs)
        QMessageBox.information(self, "当当", "保存并刷新卡包成功")
