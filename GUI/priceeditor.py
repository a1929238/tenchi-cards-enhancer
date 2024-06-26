from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QApplication, QDoubleSpinBox
from PyQt6.QtCore import Qt

class PriceEditor(QDialog):
    def __init__(self, item_dict, parent=None):
        super().__init__(parent)
        
        self.table = QTableWidget()
        self.table.setRowCount(len(item_dict))  # 设置表格行数为物品数量
        self.table.setColumnCount(2)  # 设置表格列数为2：一列是物品名，另一列是价格
        self.table.setHorizontalHeaderLabels(['物品名', '价格'])
        
        row = 0
        for item_name, price in item_dict.items():
            item_name_cell = QTableWidgetItem(item_name)
            item_name_cell.setFlags(item_name_cell.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 设置物品名单元格不可编辑
            self.table.setItem(row, 0, item_name_cell)
            spin_box = QDoubleSpinBox()
            spin_box.setSuffix("d")
            spin_box.setRange(0, 1000000)  # 设置价格范围
            spin_box.setValue(price)
            self.table.setCellWidget(row, 1, spin_box)  # 价格单元格
            row += 1
        
        self.save_button = QPushButton('保存')
        self.save_button.clicked.connect(self.accept)  # 当点击保存按钮时关闭对话框并返回结果
        
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.save_button)
        
        self.setLayout(layout)
    
    def get_data(self):
        data = {}
        for row in range(self.table.rowCount()):
            item_name = self.table.item(row, 0).text()
            spin_box = self.table.cellWidget(row, 1)
            price = spin_box.value()  # 获取 QDoubleSpinBox 的值
            data[item_name] = price
        return data