from __future__ import annotations
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QListWidgetItem,
    QHBoxLayout, QLabel, QPushButton
)

from GUI.bindingcheckbox import BindingCheckbox
from module.UI.UIWidgets import CloverComboBox
from module.utils import save_settings, resource_path

if TYPE_CHECKING:
    from TenchiCardEnhancer import TenchiCardsEnhancer


class GemUI:
    def __init__(self, enhancer: TenchiCardsEnhancer):
        super().__init__()

        self.enhancer = enhancer

        # 设置星级范围（0-15星）
        self.enhancer.min_gem_level.setRange(0, 14)
        self.enhancer.max_gem_level.setRange(1, 15)

        # 读取设置的星级范围
        self.enhancer.min_gem_level.setValue(self.enhancer.settings.get("宝石方案", {}).get("等级范围", [0, 5])[0])
        self.enhancer.max_gem_level.setValue(self.enhancer.settings.get("宝石方案", {}).get("等级范围", [0, 5])[1])

        # 初始化宝石选择框
        self.init_gem_combo()

        # 初始化宝石列表
        self.init_gem_list()

        # 连接信号
        self.enhancer.min_gem_level.valueChanged.connect(self.update_plan_list)
        self.enhancer.max_gem_level.valueChanged.connect(self.update_plan_list)
        self.enhancer.crystal_bind_check.stateChanged.connect(self.on_crystal_bind_changed)
        self.enhancer.min_gem_level.valueChanged.connect(self.on_gem_level_range_changed)
        self.enhancer.max_gem_level.valueChanged.connect(self.on_gem_level_range_changed)
        self.enhancer.add_gem_btn.clicked.connect(self.add_gem_to_list)

        # 初始加载列表
        self.update_plan_list()

    def init_gem_combo(self):
        gem_dir = resource_path("items/gem")
        if os.path.exists(gem_dir):
            for filename in os.listdir(gem_dir):
                clover_name = filename.replace(".png", "")
                self.enhancer.gem_combo.addItem(clover_name)

    def init_gem_list(self):
        for gem_name, bind in self.enhancer.settings["宝石方案"]["宝石选择"].items():
            self.add_gem_to_list(gem_name, bind)

    def add_gem_to_list(self, gem_name=None, bind=None):
        """
        将选项框中的宝石名称和绑定复选框加入到列表中，并实时保存配置
        """
        if not gem_name:
            gem_name = self.enhancer.gem_combo.currentText()
            if gem_name in self.enhancer.settings["宝石方案"]["宝石选择"]:
                return

        # 创建列表项控件
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)

        # 名称标签
        label = QLabel(gem_name)

        # 绑定复选框
        bind_checkbox = BindingCheckbox()
        bind_checkbox.gem_name = gem_name
        bind_checkbox.stateChanged.connect(
            lambda state: self.on_gem_bind_changed(gem_name, state)
        )

        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon(resource_path("items/icon/垃圾桶.png")))

        # 添加控件到布局
        item_layout.addWidget(label)
        item_layout.addWidget(bind_checkbox)
        item_layout.addStretch()
        item_layout.addWidget(delete_btn)

        # 创建列表项
        list_item = QListWidgetItem()
        list_item.setData(Qt.ItemDataRole.UserRole, gem_name)  # 存储宝石名称到数据角色
        list_item.setSizeHint(item_widget.sizeHint())

        # 添加到列表
        self.enhancer.gem_list.addItem(list_item)
        self.enhancer.gem_list.setItemWidget(list_item, item_widget)

        if bind is None:
            # 更新设置并保存
            self.enhancer.settings["宝石方案"]["宝石选择"][gem_name] = 0
            save_settings(self.enhancer.settings)

        # 连接删除信号
        delete_btn.clicked.connect(
            lambda _, item=list_item: self._remove_list_item(item)
        )

    def _remove_list_item(self, item):
        """安全移除列表项并更新配置"""
        row = self.enhancer.gem_list.row(item)
        if row >= 0:
            gem_name = item.data(Qt.ItemDataRole.UserRole)  # 从数据角色获取宝石名称

            # 从设置中移除并保存
            if gem_name in self.enhancer.settings["宝石方案"]["宝石选择"]:
                del self.enhancer.settings["宝石方案"]["宝石选择"][gem_name]
                save_settings(self.enhancer.settings)

            # 从列表移除
            self.enhancer.gem_list.takeItem(row)
            item = None  # 释放引用

    def on_gem_bind_changed(self, gem_name, state):
        """当宝石绑定状态变化时更新设置"""
        if gem_name in self.enhancer.settings["宝石方案"]["宝石选择"]:
            self.enhancer.settings["宝石方案"]["宝石选择"][gem_name] = state
            save_settings(self.enhancer.settings)

    def update_plan_list(self):
        """更新强化方案列表"""
        self.enhancer.gem_plan_list.clear()

        min_star = self.enhancer.min_gem_level.value()
        max_star = self.enhancer.max_gem_level.value()

        if min_star >= max_star:
            return

        # 获取当前宝石方案设置
        gem_settings = self.enhancer.settings.get("宝石方案", {})
        plan_settings = gem_settings.get("方案", {})

        for current_star in range(min_star, max_star):
            next_star = current_star + 1
            step_key = str(current_star + 1)  # 对应方案中的键

            # 创建列表项
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)

            # 星级标签
            label = QLabel(f"{current_star}→{next_star}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("min-width: 80px;")

            # 四叶草选择框
            clover_combo = CloverComboBox()
            clover_combo.step_key = step_key  # 存储对应的设置键

            # 从设置初始化选择状态
            selected = plan_settings.get(step_key, "无")
            idx = clover_combo.findText(selected)
            clover_combo.setCurrentIndex(idx if idx != -1 else 0)

            # 连接信号
            clover_combo.currentIndexChanged.connect(self.on_clover_changed)

            item_layout.addWidget(label)
            item_layout.addWidget(clover_combo)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())

            self.enhancer.gem_plan_list.addItem(list_item)
            self.enhancer.gem_plan_list.setItemWidget(list_item, item_widget)

    def on_clover_changed(self):
        """当选择框变化时更新设置"""
        combo = self.enhancer.sender()
        if not combo or not hasattr(combo, "step_key"):
            return

        # 更新设置字典
        gem_settings = self.enhancer.settings.setdefault("宝石方案", {
            "水晶绑定": 0,
            "等级范围": [0, 5],
            "宝石选择": {},
            "方案": {}
        })
        gem_settings["方案"][combo.step_key] = combo.currentText()

        # 保存
        save_settings(self.enhancer.settings)

    def on_crystal_bind_changed(self, state):
        """当选择框变化时更新设置"""
        gem_settings = self.enhancer.settings.setdefault("宝石方案", {
            "水晶绑定": 0,
            "等级范围": [0, 5],
            "宝石选择": {},
            "方案": {}
        })
        gem_settings["水晶绑定"] = state

        # 保存
        save_settings(self.enhancer.settings)

    def on_gem_level_range_changed(self):
        """当等级范围变化时更新设置"""
        gem_settings = self.enhancer.settings.setdefault("宝石方案", {
            "水晶绑定": 0,
            "等级范围": [0, 5],
            "宝石选择": [],
            "方案": {}
        })
        gem_settings["等级范围"] = [self.enhancer.min_gem_level.value(), self.enhancer.max_gem_level.value()]

        # 保存
        save_settings(self.enhancer.settings)
