# 天知强卡器，打算用pyqt5做GUI
# setting字典的结构为:setting[type][name][count]
# 统计数据字典的结构为:statistics[type][name][count]
# 0.2.1更新计划：用金币变动图像识别制作是否成功；改进配方识别方法；用空格图像识别是否还需要往下滑动
# 已完成计划：
# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets, QtCore, QtGui, uic
import sys
import win32gui
import win32api
import win32con
import win32ui
import json
from ctypes import windll, c_void_p
import numpy as np
import os
import cv2
import plyer
import queue
import copy
from module.ResourceInit import ResourceInit
from module.utils import imread, resource_path, hide_layout
from GUI.editwindow import EditWindow

class tenchi_cards_enhancer(QtWidgets.QMainWindow):
    # 定义信号
    show_dialog_signal = QtCore.pyqtSignal(str, str)
    log_signal = QtCore.pyqtSignal(str)
    
    """
    Initializes the GUI by loading the UI file, setting the window icon, initializing variables, connecting signals/slots, starting background threads, etc.
    
    Key initialization steps:
    
    - Load UI file
    - Set window icon 
    - Initialize variables like version, handle, card dict, etc.
    - Load settings
    - Connect GUI widgets to script 
    - Initialize log output
    - Start furina animation
    - Make furina label draggable
    - Connect start/stop buttons
    - Start enhancer threads
    - Initialize recipe, clover, subcard, spice menus
    - Initialize settings page
    - Connect test button
    """

    # GUI界面初始化
    def __init__(self):
        super(tenchi_cards_enhancer, self).__init__()
        # ... 其余的初始化代码 ...
        # 加载UI文件
        ui_path = resource_path('GUI/天知强卡器.ui')
        uic.loadUi(ui_path, self)
        # 设置窗口图标
        self.setWindowIcon(QtGui.QIcon(resource_path("items/icon/furina.ico")))
        # 固定大小
        self.setFixedSize(self.size())
        # 设置窗口背景图
        background_image_path = resource_path('items/icon/furina_background.jpg')
        # 设置样式表，插入绝对路径
        self.setStyleSheet(f"""
            QMainWindow {{
                border-image: url("{background_image_path}") 0 0 0 0 stretch stretch;
            }}
            QToolTip {{
                background-color: rgb(170, 255, 255);
                color: black;
                border: 3px dotted rgb(170, 255, 255);
            }}
        """)

        # 初始化窗口dpi
        self.dpi = self.get_system_dpi()
        
        # 变量初始化
        self.version = "0.2.1"
        self.handle = None
        self.card_dict = {}
        self.is_running = False
        self.offset = 0
        self.cards_enough = False
        self.enhance_times = 0
        self.enhance_count = 0
        self.produce_count = 0
        self.card_name = '无'
        self.found_clover = True
        self.card_info_dict = {}
        self.enhance_type = '无'

        # 初始化香料列表
        # 从default_constants中获取香料列表
        filename = resource_path('GUI/default/default_constants.json')
        with open(filename, 'r', encoding='utf-8') as f:
            default_constants = json.load(f)
        self.spice_dict = default_constants['默认香料字典']
        self.best_enhance_plan = default_constants['强化最优路径']

        self.spice_used = {}
        for i in range(9):
            self.spice_used[i] = 0
        # 初始化临时卡片星级字典，作用是判断此时已有的星级
        self.temp_card_level_dict = {}
        self.settings = self.load_settings()  # 读取设置作为全局变量
        self.statistics = self.load_statistics()  # 读取统计数据作为全局变量
        self.min_level = int(self.settings["个人设置"]["最小星级"])
        self.max_level = int(self.settings["个人设置"]["最大星级"])
        self.reload_count = int(self.settings["个人设置"]["刷新次数"])
        self.produce_interval = int(self.settings["个人设置"]["制卡间隔"])
        self.produce_check_interval = int(self.settings["个人设置"]["制卡检测间隔"])
        self.enhance_interval = int(self.settings["个人设置"]["强卡间隔"])
        self.enhance_check_interval = int(self.settings["个人设置"]["强卡检测间隔"])

        # 背景遮盖层初始化
        self.frosted_layer.lower()  # 将半透明层放到底层

        # 将GUI控件与脚本连接
        # 初始化日志信息
        self.output_log.setOpenExternalLinks(True)
        self.init_log_message()
        
        # 召唤动态芙芙！
        self.furina_movie = QtGui.QMovie(resource_path("items/icon/furina_shake.gif"))
        self.furina.setMovie(self.furina_movie)
        self.furina_movie.start()
        self.furina.handleChanged.connect(self.update_handle_display)

        # 初始化芙宁娜助手
        self.init_furina_helper()

        # 配置开始和停止按钮，将开始与停止连接上槽
        self.startbtn.setEnabled(False) # 没有句柄时，开始与仅强化都不可用
        self.enhanceronlybtn.setEnabled(False)
        self.stopbtn.setEnabled(False)  # 初始时停止按钮不可用
        self.startbtn.clicked.connect(self.onStart)
        self.stopbtn.clicked.connect(self.onStop)
        self.enhanceronlybtn.clicked.connect(self.enhanceronly)

        # 连上工作线程
        self.EnhancerThread = EnhancerThread(self)
        self.enhanceonlyThread = enhanceonlyThread(self)
        
        # 连接上工作线程的信号
        self.EnhancerThread.showDialogSignal.connect(self.show_dialog)
        self.enhanceonlyThread.showDialogSignal.connect(self.show_dialog)
        self.show_dialog_signal.connect(self.show_dialog)
        self.log_signal.connect(self.send_log_message)



        # 配置，初始化配方选择菜单
        self.select_list = self.recipe_select
        self.init_recipe_box(self.recipe_select.recipeSelectBox)
        self.init_recipe_select_list()
        # 连接配方选择窗口信号
        self.select_list.recipeAdded.connect(self.on_recipe_added)
        self.select_list.recipeRemoved.connect(self.on_recipe_removed)
        self.select_list.recipeClicked.connect(self.on_recipe_selected)
        # 配置，初始化模式选择菜单
        self.init_mode()
        # 配置，初始化四叶草选择菜单
        self.init_clover()
        # 配置，初始化副卡选择菜单
        self.init_subcard()
        # 初始化香料菜单
        self.init_spice()
        self.init_spice_limit()
        # 初始化个人设置页
        self.init_setting()
        # 初始化统计数据页
        self.init_statistics()
        # 初始化状态栏
        self.init_statusbar()

        # 连接测试按钮
        # self.test_btn.clicked.connect(self.test)

        # 创建ResourcesInit实例
        self.resources = ResourceInit()

        # 创建生产队列实例
        self.produce_queue = queue.Queue()

        # 在主窗口中创建一个编辑窗口的属性
        self.edit_window = None
        # 追踪目前窗口的对象名
        self.current_label_object_name = None
    
    # 统计数据页GUI
    def init_statistics(self):
        # 创建一个新实例
        stats_tab_widget = QtWidgets.QTabWidget(self.tab_3)
        # 为每个统计数据类别创建一个标签页和表格视图
        for category, data in self.statistics.items():
            # 创建一个新的QWidget作为标签页
            tab_statistics = QtWidgets.QWidget()
            stats_tab_widget.addTab(tab_statistics, category)

            # 创建表格视图
            table = QtWidgets.QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(['项目', '数量'])

            # 填充数据
            table.setRowCount(len(data))
            for i, (key, value) in enumerate(data.items()):
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(key))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(value)))

            # 创建布局并添加表格到新标签页
            layout = QtWidgets.QVBoxLayout(self.tab_3)
            layout.addWidget(table)
            tab_statistics.setLayout(layout)
        # 创建布局并添加新的 QTabWidget 到 tab_3
        layout = QtWidgets.QVBoxLayout(self.tab_3)
        layout.addWidget(stats_tab_widget)
    
    # 获取系统dpi
    def get_system_dpi(self):
        # 创建一个设备上下文（DC）用于屏幕
        hdc = windll.user32.GetDC(0)
        # 获取屏幕的水平DPI
        dpi = windll.gdi32.GetDeviceCaps(hdc, 88)  # 88 is the index for LOGPIXELSX
        windll.user32.ReleaseDC(0, hdc)
        return dpi

    # 开始按钮
    def onStart(self):
        # 确保不会重复点击开始
        self.enhanceronlybtn.setEnabled(False)
        self.startbtn.setEnabled(False)
        self.stopbtn.setEnabled(True)
        # 正式开始前先防呆
        self.dull_detection()
        self.EnhancerThread.start_loop()

    # 停止按钮
    def onStop(self):
        # 点击停止后可以重新点击开始
        self.is_running = False
        self.startbtn.setEnabled(True)
        self.enhanceronlybtn.setEnabled(True)
        self.stopbtn.setEnabled(False)
    
    # 仅强卡按钮
    def enhanceronly(self):
        # 初始化按钮
        self.is_running = True
        self.stopbtn.setEnabled(True)
        self.startbtn.setEnabled(False)
        # 正式开始前先防呆
        self.dull_detection()
        self.enhanceonlyThread.start_enhance()
    
    # 芙芙助手，功能强大
    def init_furina_helper(self):
        # 乌瑟勋爵，一键统一所有强化方案用卡
        # 初始化配方选择框
        self.init_recipe_box(self.GentilhommeUsher_box)
        # 将按钮连接上一键统一功能
        self.GentilhommeUsher_btn.clicked.connect(self.gentilhomme_usher)
        # 海薇玛夫人，一键将副卡星级设置为最优路径
        self.SurintendanteChevalmarin_btn.clicked.connect(self.surintendante_chevalmarin)
        # 蟹贝蕾妲小姐，一键设置所有强化方案用料为绑定/不绑
        self.MademoiselleCrabaletta_btn.clicked.connect(self.mademoiselle_crabaletta)

    # 乌瑟勋爵！
    def gentilhomme_usher(self):
        # 获取选择框当前文本
        text = self.GentilhommeUsher_box.currentText()
        # 分离出卡片名
        card_name = text.split("-")[0]
        enhance_plan = self.settings["强化方案"]
        # 迭代强化方案的所~有主副卡，将其名称设置为卡片名
        for i in range(16):
            for j in range(4):
                if j == 0:
                    enhance_plan[f'{i}-{i+1}']['主卡']['卡片名称'] = card_name
                elif j in [1, 2, 3]:
                    enhance_plan[f'{i}-{i+1}'][f'副卡{j}']['卡片名称'] = card_name
        self.settings["强化方案"] = enhance_plan
        # 保存强化方案！
        self.save_settings(self.settings)

    # 海薇玛夫人！
    def surintendante_chevalmarin(self):
        # 替换所有副卡的星级为最优路径
        for enhance_type, enhance_info in self.best_enhance_plan.items():
            if enhance_type in self.settings["强化方案"]:
                for material, count in enhance_info.items():
                    if material in self.settings["强化方案"][enhance_type]:
                        # 更新第二个字典中的对应用料
                        self.settings["强化方案"][enhance_type][material].update(count)
        # 初始化副卡与四叶草菜单
        self.init_subcard()
        self.init_clover()
        # 保存强化方案
        self.save_settings(self.settings)
    
    # 蟹贝蕾妲小姐！
    def mademoiselle_crabaletta(self):
        # 获取绑定/不绑按钮的选择状态
        is_bind = self.bind_radio_btn.isChecked()
        enhance_plan = self.settings["强化方案"]
        # 迭代所有主副卡，将其绑定设置为选择的状态
        for i in range(16):
            for j in range(5):
                if j == 0:
                    enhance_plan[f'{i}-{i+1}']['主卡']['绑定'] = is_bind
                elif j in [1, 2, 3]:
                    enhance_plan[f'{i}-{i+1}'][f'副卡{j}']['绑定'] = is_bind
                elif j == 4:
                    enhance_plan[f'{i}-{i+1}']['四叶草']['绑定'] = is_bind
        self.settings["强化方案"] = enhance_plan
        # 保存强化方案！
        self.save_settings(self.settings)

    # 保存当前设置
    def save_current_settings(self):
        # 调用保存设置函数
        self.save_settings(self.settings)

    # 初始化日志信息
    def init_log_message(self):
        self.send_log_message(f"当当！天知强卡器启动成功！目前版本号为{self.version}")
        self.send_log_message("使用前请关闭二级密码")
        self.send_log_message("目前仅支持360游戏大厅,但支持任何系统缩放，所以说我是高性能的呦")
        self.send_log_message("目前无法应对美食大赛任务，请注意自己的美食大赛完成进度")
        self.send_log_message("最新版本 [github] <a href=https://github.com/a1929238/tenchi-cards-enhancer>https://github.com/a1929238/tenchi-cards-enhancer</a>")
        self.send_log_message("[QQ群 交流·反馈·催更] 786921130 ")
        self.send_log_message("如果觉得好用的话，把软件推荐给更多的人嘛，反正不要钱~")

    def open_edit_window(self, label_object_name):
        if self.edit_window is not None:
            # 如果已经有一个编辑窗口打开，并且是由相同的ClickableLabel触发的，则关闭它
            if self.current_label_object_name == label_object_name:
                self.edit_window.close()
                self.edit_window = None
                self.current_label_object_name = None
                return
            else:
                # 如果是由不同的ClickableLabel触发的，则关闭当前窗口
                self.edit_window.close()

        # 创建一个新的编辑窗口
        self.edit_window = EditWindow(label_object_name, self)
        # 设置编辑窗口图标
        self.edit_window.setWindowIcon(QtGui.QIcon(resource_path("items\icon\hutao.ico")))
        # 初始化编辑窗口
        self.init_edit_window(label_object_name)
        self.edit_window.show()
        self.current_label_object_name = label_object_name  # 更新当前激活的ClickableLabel的对象名
        # 连接关闭信号，以便在窗口关闭时更新状态
        self.edit_window.closed.connect(self.on_edit_window_closed)

    def on_edit_window_closed(self):
        # 当编辑窗口关闭时，将其设置为None
        self.edit_window = None
        self.current_label_object_name = None
    
    # 初始化编辑窗口
    def init_edit_window(self, label_object_name):
        # 从窗口名读取信息
        level = int(label_object_name.replace("E", ""))
        self.enhance_type = f'{level - 1}-{level}'
        # 初始化配方选择框
        for i in range(4):
            recipe_box = getattr(self.edit_window, f'card_box{i}')
            self.init_recipe_box(recipe_box)
            # 将配方选择框更改的信号连接上字典的编辑和保存
            recipe_box.currentIndexChanged.connect(self.on_recipe_box_changed)

        # 根据设置文件，初始化选择框的索引，并在星级不存在时，隐藏对应的配方选择框
        for i in range(4):
            recipe_box = getattr(self.edit_window, f'card_box{i}')
            if i == 0:
                card_name = self.settings["强化方案"][self.enhance_type]["主卡"].get("卡片名称", "无")
            else:
                # 只会隐藏部分副卡的选择框
                layout = getattr(self.edit_window, f'horizontalLayout_{i}')
                card_name = self.settings["强化方案"][self.enhance_type][f"副卡{i}"].get("卡片名称", "无")
                card_level = self.settings["强化方案"][self.enhance_type][f"副卡{i}"].get("星级", "无")
                if card_level == "无":
                    hide_layout(layout)
            index = recipe_box.findText(card_name, QtCore.Qt.MatchFlag.MatchContains | QtCore.Qt.MatchFlag.MatchCaseSensitive)
            recipe_box.setCurrentIndex(index)

        # 初始化绑定按钮，绑定按钮有五个,0是主卡，1-3是副卡，4是四叶草
        for i in range(5):
            bind_btn = getattr(self.edit_window, f'bind_btn{i}')
            self.init_bind_btn(bind_btn, i)
            
    
    # 初始化编辑窗口的绑定编辑
    def init_bind_btn(self, checkBox, index):
        # 根据设置，初始化勾选框当前选项
        if index == 0:
            # 主卡绑定
            bind_flag = self.settings["强化方案"][self.enhance_type]["主卡"].get("绑定", False)
        elif index in [1, 2, 3]:
            # 副卡绑定
            bind_flag = self.settings["强化方案"][self.enhance_type][f"副卡{index}"].get("绑定", False)
        elif index == 4:
            # 四叶草绑定
            bind_flag = self.settings["强化方案"][self.enhance_type]["四叶草"].get("绑定", False)
        # 设置是否被勾选
        checkBox.setChecked(bind_flag)
        # 将绑定勾选框点击的信号连接上字典的编辑和保存
        checkBox.clicked.connect(self.on_bind_btn_clicked)
    
    # 初始化选卡菜单及索引
    def init_recipe_select_list(self):
        # 尝试从设置文件中获取所有生产方案的键
        produce_cards = self.settings["生产方案"].keys()
        if produce_cards:
            for produce_card in produce_cards:
                # 处理卡片名
                card_name = f'{produce_card}-{self.card_info_dict[produce_card]}'
                # 调用控件的方法，把卡片加到选择列表中
                self.select_list.addItem(card_name)
            # 加入之后，将索引为0的卡片，作为开始时选择卡片
            self.card_name = self.select_list.listWidget.item(0).data(QtCore.Qt.ItemDataRole.UserRole).split("-")[0]
        # 初始化选卡文本
        self.current_card_name.setText(f'当前选择配方：{self.card_name}')

    # 初始化选卡菜单
    def init_recipe_box(self, comboBox):
        recipe_dir = resource_path("items/recipe")
        # 获取卡片属性字典
        with open(resource_path('GUI/card_dict/card_info_dict.json'), 'r', encoding='utf-8') as f:
            self.card_info_dict = json.load(f)
        if os.path.exists(recipe_dir):
            # 获取卡片名列表
            filenames = os.listdir(recipe_dir)
            # 根据评级对文件名进行排序
            sorted_filenames = sorted(filenames, key=self.sort_key)
            for filename in sorted_filenames: 
                # 获取卡片名
                recipe_name = filename.replace("配方.png", "")
                # 在卡片名后面加上卡片的属性
                card_text = f"{recipe_name}-{self.card_info_dict.get(recipe_name, '未知')}"
                comboBox.addItem(card_text)

    def on_recipe_added(self, text):
        # 分离text，使其变成卡片名
        card_name = text.split("-")[0]
        # 添加 item 时初始化香料字典，因为要使用初始的常量字典，所以要使用字典的副本
        self.settings['生产方案'][card_name] = copy.deepcopy(self.spice_dict)
        self.save_settings(self.settings)

    def on_recipe_removed(self, text):
        # 分离text，使其变成卡片名
        card_name = text.split("-")[0]
        # 删除 item 时删除对应字典
        if card_name in self.settings['生产方案']:
            del self.settings['生产方案'][card_name]
        self.save_settings(self.settings)
        # 检查列表是否为空
        if not self.select_list.listWidget.count():
            # 更新UI显示为默认提示或空
            self.current_card_name.setText('当前选择配方：无')
            # 更新当前所选卡片名
            self.card_name = "无"
            # 禁用所有香料框
            self.init_spice()
        else:
            # 如果列表不为空，选择第一个项目
            self.select_list.listWidget.setCurrentRow(0)
            self.card_name = self.select_list.listWidget.item(0).data(QtCore.Qt.ItemDataRole.UserRole).split("-")[0]
            self.current_card_name.setText(f'当前选择配方：{self.card_name}')
            # 重新初始化香料框
            self.init_spice()
    
    # 好中差卡排序函数
    def sort_key(self, filename):
        recipe_name = filename.replace("配方.png", "")
        rating = self.card_info_dict.get(recipe_name, "")
        if rating == "好卡":
            return 1, recipe_name
        elif rating == "中卡":
            return 2, recipe_name
        elif rating == "差卡":
            return 3, recipe_name
        else:
            return 4, recipe_name  # 对于没有评级的卡片，放在最后
    
    # 初始化模式选择菜单
    def init_mode(self):
        # 为模式选择菜单添加制卡模式
        self.produce_mode_box.addItem("固定制卡")
        self.produce_mode_box.addItem("混合制卡")
        self.produce_mode_box.addItem("动态制卡")
        # 读取设置中的制卡模式
        produce_mode = self.settings["个人设置"].get("制卡模式", "0")
        # 初始化模式选择菜单
        self.produce_mode_box.setCurrentIndex(int(produce_mode))
        # 连接信号，每次更改选项时，都发出信号，保存字典
        self.produce_mode_box.currentIndexChanged.connect(self.on_produce_mode_selected)

    # 初始化副卡菜单
    def init_subcard(self):
        for i in range(3):
            for j in range(16):
                subcard_box_name = f"subcard{i+1}_{j}"
                subcard_box = getattr(self, subcard_box_name)\
                # 阻止信号发射
                subcard_box.blockSignals(True)
                # 清除现有的选项
                subcard_box.clear()
                # 给每个副卡菜单添加上对应等级的副卡选项
                for n in range(3):
                    value = j - n
                    if value >= 0:
                        subcard_box.addItem(str(value))
                # 不要忘记加上无
                subcard_box.addItem("无")
                # 菜单选项添加完后，根据设置文件，设置菜单的当前选中项
                selected_subcard = self.settings.get("强化方案", {}).get(f"{j}-{j+1}", {}).get(f"副卡{i+1}", "无").get("星级", "无")
                # 在 QComboBox 中查找这个卡片名称对应的索引
                index = subcard_box.findText(selected_subcard)
                if index >= 0:
                    # 如果找到了，设置 QComboBox 当前选中的索引
                    subcard_box.setCurrentIndex(index)
                # 允许信号发射
                subcard_box.blockSignals(False)
                # 尝试断开旧的连接信号
                try:
                    subcard_box.currentIndexChanged.disconnect()
                except TypeError:
                    pass
                # 每次更改选项时，都要保存字典
                subcard_box.currentIndexChanged.connect(self.on_subcard_selected)
    
    # 初始化四叶草菜单
    def init_clover(self):
        for i in range(16):
            clover_box_name = f"clover{i}"
            clover_box = getattr(self, clover_box_name)
            # 阻止信号发射
            clover_box.blockSignals(True)
            # 清除现有的选项
            clover_box.clear()
            # 给每个四叶草菜单加上所有四叶草
            clover_dir = resource_path("items/clover")
            if os.path.exists(clover_dir):
                for filename in os.listdir(clover_dir):
                    clover_name = filename.replace("四叶草.png", "")
                    clover_box.addItem(clover_name)
            # 加上无
            clover_box.addItem("无")
            # 菜单选项添加完后，根据设置文件，设置菜单的当前选中项
            selected_clover = self.settings.get("强化方案", {}).get(f"{i}-{i+1}", {}).get("四叶草", "无").get("种类", "无")
            # 在 QComboBox 中查找这个卡片名称对应的索引
            index = clover_box.findText(selected_clover)
            if index >= 0:
                # 如果找到了，设置 QComboBox 当前选中的索引
                clover_box.setCurrentIndex(index)
            # 允许信号发射
            clover_box.blockSignals(False)
            # 尝试断开旧的连接信号
            try:
                clover_box.currentIndexChanged.disconnect()
            except TypeError:
                pass
            # 每次更改选项时，都要保存字典
            clover_box.currentIndexChanged.connect(self.on_clover_selected)

    # 初始化香料菜单,根据设置字典，初始化香料使用次数选择
    def init_spice(self):
        # 如果当前所选卡片不是无，就初始化香料菜单
        if self.card_name != "无":
            # 获取生产方案字典
            production_plan = self.settings["生产方案"][self.card_name]
            # 将字典的键（香料名）提取到一个列表中
            spices = list(production_plan.keys())
            for i in range(len(spices)):
                spice_name = spices[i]
                spice_count = production_plan[spice_name].get("数量", "0")
                # 获取对应的香料控件
                spice_box_name = f"spice{i}"
                spice_box = getattr(self, spice_box_name)
                # 不用香料肯定是不绑,设定香料的绑定状态
                if i != 0:
                    spice_bind = production_plan[spice_name].get("绑定", False)
                    spice_bind_box_name = f"spice_bind{i}"
                    spice_bind_box = getattr(self, spice_bind_box_name)
                    spice_bind_box.setChecked(spice_bind)
                    # 每次更改绑定状态时，都要保存字典
                    spice_bind_box.stateChanged.connect(self.on_spice_bind_selected)
                    # 重新启用这些菜单
                    spice_bind_box.setEnabled(True)  
                spice_box.setEnabled(True)
                # 设置香料盒的数量
                spice_box.setValue(int(spice_count))
                # 每次更改次数时，都要保存字典
                spice_box.valueChanged.connect(self.on_spice_selected)
        # 如果是无，就把这些香料菜单，香料绑定按钮都禁用
        else:
            spice_list = list(self.spice_dict.keys())
            for i in range(len(spice_list)):
                spice_box_name = f"spice{i}"
                spice_box = getattr(self, spice_box_name)
                if i != 0:
                    spice_bind_box_name = f"spice_bind{i}"
                    spice_bind_box = getattr(self, spice_bind_box_name)
                    spice_bind_box.setEnabled(False)
                spice_box.setEnabled(False)
                
    def init_spice_limit(self):
        # 因为更改了香料编辑菜单，把香料上限初始化独立出来
        produce_limit_dict = self.settings["香料使用上限"]
        spices_limits = list(produce_limit_dict.keys())
        for i in range(len(spices_limits)):
            # 获取香料名称与数量
            spice_name = spices_limits[i]
            spice_count_limit = self.settings["香料使用上限"][spice_name]
            # 获取对应的上限控件
            spice_limit_box_name = f"spice{i}_2"
            spice_limit_box = getattr(self, spice_limit_box_name)
            # 设置当前控件的数量
            spice_limit_box.setValue(int(spice_count_limit))
            # 将每个香料输入控件都连接上保存函数
            spice_limit_box.valueChanged.connect(self.on_spice_limit_selected)
        
    # 初始化个人设置菜单
    def init_setting(self):
        # 从个人设置字典中读取数据，初始化控件
        bind_only = self.settings.get("个人设置", {}).get("只用绑定卡", False)
        unbind_clover_replace = self.settings.get("个人设置", {}).get("不绑草替代", False)
        self.max_level_input.setValue(self.max_level)
        self.min_level_input.setValue(self.min_level)
        self.reload_count_input.setValue(self.reload_count)
        self.produce_interval_input.setValue(self.produce_interval)
        self.produce_check_interval_input.setValue(self.produce_check_interval)
        self.enhance_interval_input.setValue(self.enhance_interval)
        self.enhance_check_interval_input.setValue(self.enhance_check_interval)
        self.produce_times_input.setValue(int(self.settings.get("个人设置", {}).get("制卡次数上限", 0)))

        # 把控件都连接上字典
        self.max_level_input.valueChanged.connect(self.on_setting_changed)
        self.min_level_input.valueChanged.connect(self.on_setting_changed)
        self.reload_count_input.valueChanged.connect(self.on_setting_changed)
        self.produce_interval_input.valueChanged.connect(self.on_setting_changed)
        self.produce_check_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_check_interval_input.valueChanged.connect(self.on_setting_changed)
        self.produce_times_input.valueChanged.connect(self.on_setting_changed)

    # 初始化状态栏
    def init_statusbar(self):
        # 设置颜色蒙版
        self.statusBar.setStyleSheet("QStatusBar{background-color: rgba(240, 248, 255, 0.8);}")
        # 获取打开程序的时间
        self.start_time = QtCore.QElapsedTimer()
        self.start_time.start()  # 开始计时

        # 创建并添加当前时间标签
        self.current_time_label = QtWidgets.QLabel()
        self.statusBar.addWidget(self.current_time_label)

        # 创建并添加程序运行时间标签
        self.run_time_label = QtWidgets.QLabel()
        self.statusBar.addWidget(self.run_time_label)

        # 创建并添加强化次数标签
        self.enhance_count_label = QtWidgets.QLabel()
        self.statusBar.addWidget(self.enhance_count_label)

        # 创建并添加版本号标签
        self.version_label = QtWidgets.QLabel(f'版本号:{self.version}')
        self.statusBar.addPermanentWidget(self.version_label)
        # 让样式表偏移一些
        self.version_label.setStyleSheet("QLabel { margin-right: 5px; }")
        
        # 设置定时器更新当前时间和程序运行时间
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_status_bar)
        self.timer.start(1000)  # 每秒更新一次

        self.update_status_bar()  # 初始化状态栏显示
    
    def update_status_bar(self):
        # 更新当前时间
        current_time = QtCore.QTime.currentTime().toString()
        self.current_time_label.setText(f'当前时间: {current_time}')

        # 更新程序运行时间
        elapsed_time = self.start_time.elapsed()
        hours, remainder = divmod(elapsed_time, 3600000)
        minutes, seconds = divmod(remainder, 60000)
        run_time = f'{hours:02d}:{minutes:02d}:{seconds//1000:02d}'
        self.run_time_label.setText(f'运行时间: {run_time}')

        # 更新运行期间强化次数
        self.enhance_count_label.setText(f'本次运行期间共强化: {self.enhance_count}次')



    
    # 编辑正在选择配方的制卡方案
    def on_recipe_selected(self, text):
        # 分离出卡片名
        self.card_name = text.split('-')[0]
        # 更改显示的卡片名
        self.current_card_name.setText(f"当前选择配方：{self.card_name}")
        # 初始化当前卡片的香料配置
        self.init_spice()
    
    # 实时保存强化方案的选卡
    def on_recipe_box_changed(self, index):
        # 获取选择框的卡片名
        sender = self.sender()
        # 获取选择框的对象名
        sub_card_index = int((sender.objectName()).replace('card_box', ''))
        card_name = (sender.itemText(index)).split('-')[0]
        # 修改字典
        if sub_card_index == 0:
            # 0说明是主卡，更改主卡的卡片选择
            self.settings["强化方案"][self.enhance_type]['主卡']['卡片名称'] = card_name
        else:
            # 更改副卡的卡片选择
            self.settings["强化方案"][self.enhance_type][f'副卡{sub_card_index}']['卡片名称'] = card_name
        # 保存设置
        self.save_settings(self.settings)

    # 实时保存编辑窗口的绑定编辑
    def on_bind_btn_clicked(self):
        sender = self.sender()
        # 获取绑定按钮的对象名,0是主卡,1-3是副卡,4是四叶草
        index = int((sender.objectName()).replace('bind_btn', ''))
        # 保存到字典
        if index == 0:
            self.settings["强化方案"][self.enhance_type]['主卡']['绑定'] = sender.isChecked()
        elif index in [1, 2, 3]:
            self.settings["强化方案"][self.enhance_type][f'副卡{index}']['绑定'] = sender.isChecked()
        elif index == 4:
            self.settings["强化方案"][self.enhance_type]['四叶草']['绑定'] = sender.isChecked()
        # 保存设置
        self.save_settings(self.settings)

    # 实时保存制卡模式
    def on_produce_mode_selected(self, index):
        self.settings["个人设置"]["制卡模式"] = f'{index}'
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存香料配置
    def on_spice_selected(self, value):
        # 从信号发出名分离出数字
        sender = self.sender()
        spice_level = int(sender.objectName().replace('spice', ''))
        # 更新字典中的香料配置
        production_plan = self.settings["生产方案"][self.card_name]
        spice_name = list(production_plan)[spice_level]
        production_plan[spice_name]['数量'] = f"{value}"
        self.settings["生产方案"][self.card_name] = production_plan
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存香料绑定配置
    def on_spice_bind_selected(self):
        # 从信号发出对象中分离出数字
        sender = self.sender()
        spice_level = int(sender.objectName().replace('spice_bind', ''))
        # 更新字典中的香料绑定配置
        production_plan = self.settings["生产方案"][self.card_name]
        spice_name = list(production_plan)[spice_level]
        production_plan[spice_name]['绑定'] = sender.isChecked()
        self.settings["生产方案"][self.card_name] = production_plan
        # 保存设置
        self.save_settings(self.settings)

    # 实时保存香料使用上限配置
    def on_spice_limit_selected(self, value):
        # 从信号发出名分离出数字
        sender = self.sender()
        spice_level = int((sender.objectName().replace('spice', '')).split("_")[0])
        # 更新字典中的香料上限配置
        production_plan = self.settings.get("香料使用上限", {})
        spice_name = list(production_plan)[spice_level]
        production_plan[spice_name] = f"{value}"
        self.settings["香料使用上限"] = production_plan
        # 保存设置
        self.save_settings(self.settings)

    # 实时保存四叶草配置
    def on_clover_selected(self, index):
        # 从信号发出名分离出数字
        sender = self.sender()
        clover_level = int(sender.objectName().replace('clover', ''))
        selected_clover = sender.itemText(index)
        # 更新字典中的四叶草配置
        scheme_key = f"{clover_level}-{clover_level+1}"
        if scheme_key not in self.settings["强化方案"]:
            self.settings["强化方案"][scheme_key] = {}
        self.settings["强化方案"][scheme_key]["四叶草"]["种类"] = selected_clover
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存副卡配置
    def on_subcard_selected(self, index):
        # 从信号发出名分离出数字
        sender = self.sender()
        subcard_type, subcard_level = sender.objectName().split("_")[0].replace('subcard', ''), int(sender.objectName().split("_")[1])
        selected_subcard_level = sender.itemText(index)
        # 更新字典中的副卡配置
        scheme_key = f"{subcard_level}-{subcard_level+1}"
        self.settings["强化方案"][scheme_key][f"副卡{subcard_type}"]['星级'] = selected_subcard_level
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存个人设置
    def on_setting_changed(self, value):
        # 判断信号发出名，给字典的不同部分更改并保存
        sender = self.sender()
        sender_name = sender.objectName()
        if sender_name == "max_level_input":
            self.settings["个人设置"]["最大星级"] = f"{value}"
            self.max_level = value
        elif sender_name == "min_level_input":
            self.settings["个人设置"]["最小星级"] = f"{value}"
            self.min_level = value
        elif sender_name == "reload_count_input":
            self.settings["个人设置"]["刷新次数"] = f"{value}"
            self.reload_count = value
        elif sender_name == "produce_interval_input":
            self.settings["个人设置"]["制卡间隔"] = f"{value}"
            self.produce_interval = value
        elif sender_name == "produce_check_interval_input":
            self.settings["个人设置"]["制卡检测间隔"] = f"{value}"
            self.produce_check_interval = value
        elif sender_name == "enhance_interval_input":
            self.settings["个人设置"]["强卡间隔"] = f"{value}"
            self.enhance_interval = value
        elif sender_name == "enhance_check_interval_input":
            self.settings["个人设置"]["强卡检测间隔"] = f"{value}"
            self.enhance_check_interval = value
        elif sender_name == "produce_times_input":
            self.settings["个人设置"]["制卡次数上限"] = f"{value}"
            self.produce_count = value
        # 保存设置
        self.save_settings(self.settings)

    # 测试，截图函数调用
    def capture(self):
        image = self.get_image()
        # 这里可以添加保存或显示图像的代码
        image.save("test.png")

    # 更新显示窗口句柄和窗口名的标签
    def update_handle_display(self, handle):
        self.handle = handle
        if self.handle is not None:
            window_text = win32gui.GetWindowText(self.handle)
            self.handle_label.setText(f"窗口句柄: {self.handle}")
            self.window_label.setText(f"窗口名: {window_text}")
            # 允许点击开始与仅强化
            self.startbtn.setEnabled(True)
            self.enhanceronlybtn.setEnabled(True)

    # 截图函数
    def get_image(self, x, y, width, height):

        handle = self.handle
        # 获取窗口客户区大小
        rect = win32gui.GetClientRect(self.handle)
        client_width, client_height = rect[2], rect[3]

        # 获取窗口的设备上下文(DC)
        hwndDC = win32gui.GetWindowDC(handle)
        # 创建设备上下文对象
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        # 创建内存设备上下文，用于复制位图
        saveDC = mfcDC.CreateCompatibleDC()
        # 创建位图对象准备保存截图
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, client_width, client_height)
        # 将截图保存到saveBitMap中
        saveDC.SelectObject(saveBitMap)
        # 从窗口的设备上下文中拷贝新的位图，这里是整个窗口的客户区
        result = windll.user32.PrintWindow(handle, saveDC.GetSafeHdc(), 1)
        # 如果成功，则处理位图
        if result == 1:
            # 获取位图信息
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            # 根据位图信息创建NumPy数组
            im = np.frombuffer(bmpstr, dtype='uint8')
            im.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
            # 裁剪图像到指定区域
            im = im[y:y+height, x:x+width, :]
            # 删除最后一个alpha通道
            im = im[:, :, :3]
        else:
            print("截图失败")
            im = None
        # 清理设备上下文和位图资源
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(handle, hwndDC)

        # 返回图像对象
        return im

    # 点击函数

    # 左键单击
    def click(self, x, y):
        # 获取系统缩放比例（默认DPI是96）
        scale_factor = self.dpi / 96.0
        # 调整坐标
        scaled_x = int(x * scale_factor)
        scaled_y = int(y * scale_factor)
        # 将x和y转化成矩阵
        lParam = win32api.MAKELONG(scaled_x, scaled_y)
        #发送一次鼠标左键单击
        win32gui.PostMessage(self.handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        win32gui.PostMessage(self.handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam)
    
    # 拖曳,x1y1为需要拖曳的距离
    def drag(self, x, y, x1, y1):
        # 获取系统缩放比例（默认DPI是96）
        scale_factor = self.dpi / 96.0
        # 调整坐标
        scaled_x = int(x * scale_factor)
        scaled_y = int(y * scale_factor)
        scaled_x1 = int(x1 * scale_factor)
        scaled_y1 = int(y1 * scale_factor)
        # 将x和y转化成矩阵，此矩阵表示移动时，鼠标的初始位置
        lParam = win32api.MAKELONG(scaled_x, scaled_y)
        # 将x+x1和y+y1转化成矩阵，此矩阵表示鼠标要移动到的目标位置
        lParam1 = win32api.MAKELONG(scaled_x+scaled_x1, scaled_y+scaled_y1)
        #按下，移动，抬起
        win32gui.PostMessage(self.handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        win32gui.PostMessage(self.handle, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lParam1)
        win32gui.PostMessage(self.handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam1)


    # 识图函数，分割图片并识别，分成3种分割规则——0:配方分割，1:香料/四叶草分割, 2:卡片分割, 3:特殊卡片分割，识图空格
    def match_image(self, image, target_image, type, bind=None, card_name=None):
        # 初始化bind参数
        if type == 0: # 配方分割
            # 按照分割规则，把图片分割成38 * 29像素的块，间隔的x与y都是49
            rows = 4
            column = 7
            # 遍历每一块，然后依次识图
            for i in range(rows):
                for j in range(column):
                    block = image[i * 49:(i + 1) * 49, j * 49:(j + 1) * 49]
                    block = block[4: 33, 4: 42]
                    if np.array_equal(block, target_image):
                        return j, i
        elif type == 1: # 香料/四叶草分割
            # 因为就一行，所以分割成10个就行
            column = 10
            for j in range(column):
                block = image[0: 49, j * 49:(j + 1) * 49]
                # 先识别种类，再识别是否绑定
                # 格式与FAA标准格式不同，Y轴要往上5个像素
                kind = block[4: 28, 4: 42]
                if np.array_equal(kind, target_image):
                    # 识别到种类，开始识别是否绑定,根据设置判断是否需要绑定
                    bind_flag = block[38:45, 3:9]
                    if bind == True:
                        if np.array_equal(bind_flag, self.resources.spice_bind_img):
                        # 返回香料/四叶草位置
                            return j
                    else:
                        if not np.array_equal(bind_flag, self.resources.spice_bind_img):
                        # 返回香料/四叶草位置
                            return j
            return None
        elif type == 2: # 卡片分割
            # 初始化卡片字典
            temp_card_dict = {}
            # 按照分割规则，先把图片分割成49 * 57像素的块，然后再分割出3个区域：卡片本体，绑定标志，星级标志
            rows, columns = 7, 7
            for i in range(rows):
                for j in range(columns):
                    block = image[i * 57:(i + 1) * 57, j * 49:(j + 1) * 49]
                    card = block[22:37, 8:41]
                    if np.array_equal(card, target_image):
                        # 开始检测是否绑定
                        bind_flag = block[45:52, 5:11]
                        is_bind = np.array_equal(bind_flag, self.resources.card_bind_img)
                        level_img = block[8:15, 9:16]
                        # 初始化level
                        level = 0
                        # 用设置里的卡片上下限来只识别指定星级的卡片
                        for k in range(self.min_level, max(self.max_level+1, 13)):
                            if np.array_equal(level_img, self.resources.level_images[k]):
                                level = k
                                break
                        # 当最低星级为0时，此时识别出来的0星卡片才是0星卡
                        if level == 0 and self.min_level == 0:
                            level = 0
                        elif level == 0 and self.min_level!= 0:
                            # 保险，如果level等于0，而最低星级不为0时，则不返回卡片信息
                            continue
                        # 保存卡片信息，有绑定，星级，还有名称
                        card_info = {"绑定": is_bind, "星级": f"{level}", "卡片名称": card_name}
                        temp_card_dict[f"{j}-{i}"] = card_info
            # 返回字典，有位置，是否绑定，星级，还有名称
            return temp_card_dict
        elif type == 3: # 特殊的卡片分割，用来识图出空格
            rows, columns = 7, 7
            for i in range(rows):
                for j in range(columns):
                    block = image[i * 57:(i + 1) * 57, j * 49:(j + 1) * 49]
                    card = block[22:37, 8:41]
                    if np.array_equal(card, target_image):
                        return False # 如果识别到了空格，就返回False，表明可以不用继续拖了
        return None, None
    
    # 保存设置到JSON文件
    def save_settings(self, settings, filename='setting.json'):
        with open(filename, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

    # 从JSON文件读取设置
    def load_settings(self, filename='setting.json'):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            filename = resource_path('GUI/default/setting.json')
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f) # 返回默认字典，如果设置文件不存在

    
    # 保存统计数据到JSON文件
    def save_statistics(self, statistics, filename='statistics.json'):
        with open(filename, 'w', encoding='utf-8') as f:
                json.dump(statistics, f, ensure_ascii=False, indent=4)
    
    # 从JSON文件读取统计数据
    def load_statistics(self, filename='statistics.json'):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            filename = resource_path('GUI/default/statistics.json')
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f) # 返回默认字典，如果设置文件不存在
    
    # 编辑并保存统计数据字典 type——0: 四叶草 1:香料 2:使用卡片 3:强化出卡片
    def edit_statistics(self, type: int, name: list, value=1):
        if type == 0: # 四叶草
            # name是列表，包含四叶草名[0]与绑定信息[1]
            if name[1]:
                self.statistics["使用四叶草总和"]['绑定'] = self.update_dict(self.statistics["使用四叶草总和"]['绑定'], f"{name[0]}四叶草", value)
            else:
                self.statistics["使用四叶草总和"]['不绑'] = self.update_dict(self.statistics["使用四叶草总和"]['不绑'], f"{name[0]}四叶草", value)
        elif type == 1: # 香料
            # name也是列表，包含香料名[0]与绑定信息[1]
            if name[1]:
                self.statistics["使用香料总和"]['绑定'] = self.update_dict(self.statistics["使用香料总和"]['绑定'], name[0], value * 5)
            else:
                self.statistics["使用香料总和"]['不绑'] = self.update_dict(self.statistics["使用香料总和"]['不绑'], name[0], value * 5)
        elif type == 2: # 使用卡片
            # name还是一个包含主卡与副卡信息的列表，需要摘出列表信息后，再进行统计
            for i in range(len(name)):
                sub_card_info = name[i]
                level = sub_card_info["星级"]
                bind = sub_card_info["绑定"]
                if bind:
                    self.statistics["使用卡片总和"]['绑定'] = self.update_dict(self.statistics["使用卡片总和"]["绑定"], level, value)
                else:
                    self.statistics["使用卡片总和"]['不绑'] = self.update_dict(self.statistics["使用卡片总和"]["不绑"], level, value)
        elif type == 3: # 强化出卡片，强化次数，成功次数
            # 强化出卡片也是一个列表，有两个值，分别是强化卡片的星级和强化前的星级，以此统计对应星级的强化次数，还能搞出成功次数
            level = name[0]
            after_level = name[1]
            self.statistics["强化次数总和"] = self.update_dict(self.statistics["强化次数总和"], f'{level}-{level + 1}', value)
            self.statistics["强化出卡片总和"] = self.update_dict(self.statistics["强化出卡片总和"], after_level, value)
            if after_level > level:
                self.statistics["成功次数总和"] = self.update_dict(self.statistics["成功次数总和"], f'{level}-{level + 1}', value)
        # 最后保存统计次数
        self.save_statistics(self.statistics)

    # 字典编辑方法，传入字典，键，值，返回修改后的字典
    def update_dict(self, dict, key, value):
        # 哦哦哦，把key转化为str
        key = str(key)
        # 修改或初始化字典对应键和值
        dict[key] = int(dict.get(key, 0)) + int(value)
        return dict
    
    # 点击配方
    # 预计更新方法，模板匹配第一处卡片上框架的位置，然后裁剪图片，再进行识别，失败，因为最上方框架与下方的所有卡片都不同。
    # 尝试直接使用模板匹配，非常好使。
    def get_recipe(self, target_img):
        # 截图三次，每次拖曳三格
        for i in range(4):
            # 截图
            img = self.get_image(559, 90, 343, 196)
            # 直接模板匹配图像
            result = cv2.matchTemplate(img, target_img, cv2.TM_CCOEFF_NORMED)
            min_value, max_value, min_loc, max_loc = cv2.minMaxLoc(result)
            if max_value >= 0.95:
                # 匹配成功，点击配方位置
                x, y = max_loc
                self.click(580 + x, 110 + y)
                return
            # 匹配失败，鼠标滑动15个像素，再次截图，如果是第一次尝试，就只点击滑块最上方
            if i == 0:
                self.click(910, 110)
            else:
                self.drag(910, 105 + i * 15, 0, 15)
            QtCore.QThread.msleep(200)
        # 匹配失败，弹出弹窗
        self.show_dialog_signal.emit("危", "配方识别失败,请检查自己的配方")
        return
        
    # 点击香料/四叶草 type——0:香料,1:四叶草 level——字符串，对不同的type匹配不同的图片
    # 方法重写了，这样会非常快速
    def get_spice_and_clover(self, type: int, level: str, bind: bool):
        # 先获取需要匹配的图片
        if type == 0:
            if level == '不放香料':
                # 把香料点掉
                self.click(180, 397)
                # 等待100毫秒
                QtCore.QThread.msleep(100)
                return
            target_img = self.resources.spice_images[level]
        elif type == 1:
            target_img = self.resources.clover_images[level]
        # 截图，查找，点击/继续截图，重复五次
        for i in range(5):
            # 截图，查找是否有目标香料/四叶草
            img = self.get_image(33, 526, 490, 49)
            x = self.match_image(img, target_img, 1, bind)
            if x is not None:
                self.click(55 + 49 * x, 550)
                if type == 1:
                    clover_info = [level, bind]
                    self.edit_statistics(0, clover_info)
                    self.found_clover = True
                return
            # 没找到，点两下右滑键，重来
            for j in range(2):
                self.click(532, 562)
                QtCore.QThread.msleep(50)
        # 如果最后还是没有找到，就弹窗
        if type == 0:
            self.show_dialog_signal.emit("什么！", "没有找到目标香料!")
        elif type == 1:
            # 停止四叶草标识
            self.found_clover = False
        return

    # 强化卡片主函数
    def main_enhancer(self):
        # 尝试方案，拖曳7次，每次拖四格
        # 每次强化，卡片的顺序都会改变，只能强化一次截一次图，直到强卡器返回False，才停止循环
        while self.is_running:
            for i in range(7):
                # 每次强化之后合成屋栏位都会动，所以在调用前要先等待100毫秒
                QtCore.QThread.msleep(100)
                # 获取截图
                img = self.get_image(559, 91, 343, 456)
                # 处理并切割截图
                # 初始化偏移值,切割传入图像
                self.offset = 0
                # 方法更新，用模板匹配图片中的第一行，然后把色块以上的图片全部切掉，再识别。这样无论滑块在哪里，都能确保找到七行道具
                line_img = self.resources.line_img
                if line_img.shape[0] <= img.shape[0] and line_img.shape[1] <= img.shape[1]:
                    # 进行模板匹配
                    result = cv2.matchTemplate(img, line_img, cv2.TM_CCOEFF_NORMED)
                    # 遍历匹配结果
                    for y in range(result.shape[0]):
                        if result[y, 0] >= 0.30:
                            self.offset = y # 保存偏移值
                            # 裁剪图像，保留标记位置以下的七格像素
                            img = img[y + 1:400 + y]
                            break
                # 尝试获取强化卡片字典
                self.get_card_dict(img)
                if self.card_dict:
                    # 强化当前页面卡片
                    self.card_enhancer()
                    if self.cards_enough:
                        # 强化后打破拖曳，再循环一次
                        break
                # 没有可以强化的卡了，拖曳截图一次，顺便检查一下停止标识
                if not self.is_running:
                    return
                # 如果在非第一次拖曳中，当前页面没有获取到强化字典，同时识别出了空格，表面再往下拉也没卡了，那么就退出循环
                if i != 0 and not self.match_image(img, self.resources.empty_card, 3):
                    return
                # 合成屋卡片拖曳17个像素正好是一格,但是拖曳8次后会有2像素偏移，用新方法就无视偏移啦
                self.drag(908, 120 + i * 68, 0, 68)
                QtCore.QThread.msleep(200)
                # 七次拖曳截图都没有获取到卡片，退出循环
                if i == 6:
                    return


    # 获取强化卡片字典
    def get_card_dict(self, img):
        """
        遍历识图当前页面的卡片，然后返回对应格式的字典。迭代副卡卡片列表，然后对同一张图片多次识图，凑成一个完整字典。
        字典格式如下:{
            位置:{
        "level": 星级,
        "card_name":卡片名,
        "bind":是否绑定
        }
        }
        """
        # 初始化卡片字典
        self.card_dict = {}
        # 初始化所有卡片数组
        cards = []
        # 从选定星级上下限的强化方案中，迭代出所有副卡的名字，作为数组
        for i in range (self.min_level, self.max_level):
            for j in range(4):
                if j == 0:
                    card_name = self.settings["强化方案"][f"{i}-{i+1}"]["主卡"]["卡片名称"]
                else:
                    card_name = self.settings["强化方案"][f"{i}-{i+1}"][f"副卡{j}"]["卡片名称"]
                if card_name != "无" and card_name not in cards:
                    cards.append(card_name)
        # 遍历卡片数组，分别识图，凑成一个完整的字典
        for card_name in cards:
            # 初始化卡片信息
            card_info = {}
            # 遍历当前页面的卡片,识图出设置中目标卡片
            card_image = imread(resource_path(f"items/card/{card_name}.png"))
            card_info = self.match_image(img, card_image, 2, None, card_name)
            if card_info:
                self.card_dict.update(card_info)
    
    # 固定制卡，创建生产队列
    def create_produce_queue(self):
        # 遍历生产方案，创建生产队列
        produce_list = self.settings["生产方案"].keys()
        for card_name in produce_list:
            self.add_to_produce_queue(card_name)

    # 把内容添加到生产队列
    def add_to_produce_queue(self, card_name: str, spice_index: int = None):
        self.produce_queue.put((card_name, spice_index))
    
    # 执行生产队列 
    def execute_produce_queue(self):
        # 循环，直到队列为空
        while not self.produce_queue.empty():
            # 从队列中获取任务
            card_name, spice_index = self.produce_queue.get()
            # 执行任务
            self.card_producer(card_name, spice_index)
            # 标记任务已完成
            self.produce_queue.task_done()
            # 等待200毫秒，防止因卡顿而出错
            QtCore.QThread.msleep(200)
    
    # 生产卡片,2.0版本，由生产队列调用，可以获取卡片配方，并选择香料生产卡片
    # 预计更新3.0版本，通过识别金币变动图片，来判断制卡完成。
    def card_producer(self, card_name, spice_index=None):
        # 获取目标配方图片
        card_image = imread(resource_path(f"items/recipe/{card_name}配方.png"))
        # 点击目标配方
        self.get_recipe(card_image)

        # 提前计算并存储常用的设置值
        personal_settings = self.settings.get("个人设置", {})
        produce_limit = int(personal_settings.get("制卡次数上限", 0))
        spice_limit_settings = self.settings["香料使用上限"]

        # 把生产方案字典内无序的内容改成列表,配上有序的索引
        spice_list = list(self.spice_dict.keys())
        spice_count = len(spice_list)

        # 如果传入了香料索引，只处理该香料
        if spice_index is not None:
            spice_list = [spice_list[spice_index]]
            spice_count = 1

        for index in range(spice_count - 1, -1, -1):
            spice_name = spice_list[index]
            count = int(self.settings["生产方案"][card_name][spice_name]['数量'])
            bind = self.settings["生产方案"][card_name][spice_name]['绑定']
            spice_limit = int(spice_limit_settings[spice_name])

            # 如果本次制作次数超过了次数上限,就跳过该香料
            if self.spice_used[index] >= spice_limit and spice_limit != 0:
                continue
            
            if count != 0:
                # 点击对应香料
                self.get_spice_and_clover(0, spice_name, bind)
                for i in range(count):
                    # 如果检测到停止标识,就退出
                    if not self.is_running:
                        return
                    # 截图现有金币的后几位
                    gold_img = self.get_image(869, 555, 30, 15)
                    # 制作多少次~
                    self.click(285, 425)
                    # 制作间隔
                    QtCore.QThread.msleep(self.produce_interval)
                    # 截图判断金币是否发生变动，如果没有变动，说明制作还没有完成
                    for i in range(20):
                        current_gold_img = self.get_image(869, 555, 30, 15)
                        if not np.array_equal(gold_img, current_gold_img):
                            break
                        QtCore.QThread.msleep(self.produce_check_interval)

                # 输出统计信息
                spice_statistics = [spice_name, bind] # 将使用的香料名和是否绑定，作为统计信息
                self.edit_statistics(1, spice_statistics, count)
                # 统计本次运行中制卡次数
                self.produce_count += count
                # 增加该种香料制作计数
                self.spice_used[index] += count

                # 如果设置了制卡次数上限，并且达到上限，则显示对话框并返回
                if produce_limit != 0 and self.produce_count >= produce_limit:
                    self.show_dialog_signal.emit("登登!", "制卡达到上限啦~")
                    return

        
    # 动态生产卡片，方法1
    def dynamic_card_producer_1(self):
        # 初始化变量
        max_sub_card = 8
        level_list = []
        sub_card_list = []
        for level, number in self.temp_card_level_dict.items():
            # 寻找出目前所有低于8星级的卡片
            if int(level) < 8:
                level_list.append(level)
        # 查找出目前已有卡片的强化方案所用最高的副卡
        for level in level_list:
            for i in range(3):
                sub_card = self.settings["强化方案"][f"{level}-{level + 1}"].get(f"副卡{i + 1}", "无")
                if sub_card != "无":
                    sub_card_list.append(int(sub_card))
        # 选出最高星级的副卡
        max_sub_card = max(sub_card_list)
        # 遍历生产方案，查询对应的副卡是否在生产计划之内，如果不在，就往下一级的副卡做
        spice_list = list(self.spice_dict.keys())
        for j in range(len(spice_list), 0, -1):
            currect_spice = j - 1
            spice_name = spice_list[currect_spice]
            count = int(self.settings["生产方案"][spice_name])
            # 需要有对应生产方案，且生产卡片星级低于最高副卡要求，且不能和当前已有副卡重复，且需要是可用副卡
            if count != 0 and currect_spice <= max_sub_card and currect_spice not in level_list and currect_spice in sub_card_list:
                # 按照生产方案指定次数，制作一轮需求的副卡中，星级最高的卡片
                self.card_producer(currect_spice)
                return
    
    # 动态生产卡片，方法2
    def dynamic_card_producer(self):
        # 创建一个包含0-8星级的列表
        all_levels = list(range(9)) # [0, 1, 2, 3, 4, 5, 6, 7, 8]
        # 创建一个有所有香料名的列表
        spice_list = list(self.spice_dict.keys())
        # 获取生产方案中所有的卡片名
        card_list = list(self.settings["生产方案"].keys())
        # 每个卡片名都与临时字典比较，获取出它们各自的空星级列表
        for card_name in card_list:
            # 初始化存在星级列表
            existing_levels = []
            for key in self.temp_card_level_dict.keys():
                name, level = key.split("-")
                if name == card_name:
                    existing_levels.append(int(level))
            # 寻找出不存在的星级
            missing_levels = [level for level in all_levels if level not in existing_levels]
            # 排序不存在的星级
            missing_levels.sort(reverse=True)
            # 从高星级向低星级遍历，找到第一个在生产方案内的卡片,且兼顾香料使用上限
            for level in missing_levels:
                spice_name = spice_list[int(level)]
                count = int(self.settings["生产方案"][card_name][spice_name]['数量'])
                spice_limit = int(self.settings["香料使用上限"][spice_name])
                # 如果本种香料在该次运行时超过了次数上限,就跳过该香料
                if self.spice_used[level] >= spice_limit and spice_limit != 0:
                    continue
                if count > 0:
                    self.add_to_produce_queue(card_name, level)
                    break  # 生产完成后，动态生产另一种卡片

    # 强化卡片，由高到低，强化当前页所有符合条件的卡片
    def card_enhancer(self):
        """
        强化方案中，卡片信息统一为字典，字典内包含以下内容：
        星级：星级
        卡片名称：卡片名称
        绑定：是否绑定
        """
        # 按照最高强化卡片，从高到低，遍历设置里的强化方案，获取所需副卡，如果卡片总量大于等于方案所需卡片，就遍历card字典的位置，点击卡片，强化一次
        for enhance_level in range(self.max_level, self.min_level, -1):
            # 获取当前星级强化方案
            enhance_plan = self.settings["强化方案"][f"{enhance_level-1}-{enhance_level}"]
            # 获取主卡信息，信息要重复使用，所以要深拷贝
            main_card_info = enhance_plan["主卡"].copy()
            # 给主卡信息加上星级
            main_card_info['星级'] = f'{enhance_level - 1}'
            # 获取副卡信息
            sub_card_infos = []
            for i in range(1, 4):
                sub_card_info = enhance_plan[f"副卡{i}"].copy()
                # 如果副卡存在星级，则将其添加到数组内
                if sub_card_info.get("星级", "无") != "无":
                    sub_card_infos.append(sub_card_info)
            # 解耦合，检查是否可以强化
            can_enhance, positions = self.can_enhance(main_card_info, sub_card_infos)
            if can_enhance: # 如果可以强化，就点击所有传过来的位置
                for position in positions:
                    x, y = int(position.split("-")[0]), int(position.split("-")[1])
                    # 点击目标卡片，千万记得要加上偏移值
                    self.click(580 + x * 49, 115 + y * 57 + self.offset)
                # 根据设置，点击四叶草
                if enhance_plan["四叶草"]['种类'] != "无":
                    self.get_spice_and_clover(1, enhance_plan["四叶草"]['种类'], enhance_plan["四叶草"]['绑定'])
                # 如果没找到四叶草，就会关闭查找四叶草标识
                if not self.found_clover:
                    # 没有就停止，同时发出弹窗
                    self.cards_enough = False
                    self.show_dialog_signal.emit("什么！", "没有找到目标四叶草!")
                    return
                # 点击强化！强化有延迟，最终解决方案是重复识图副卡栏位，如果副卡还在，就一直点强化，直到副卡不在，再点击主卡
                self.click(285, 436)
                # 初始等待时间，这个等待没法规避
                QtCore.QThread.msleep(self.enhance_interval)
                for i in range(20):
                    # 获得副卡槽图片
                    sub_card_image = self.get_image(267, 253, 40, 50)
                    # 判定副卡槽图片是否和副卡空卡槽图片一样
                    if np.array_equal(sub_card_image, self.resources.sub_card_icon):
                        break # 卡槽空了就点掉主卡，进行下一次强化
                    # 检测等待时间
                    QtCore.QThread.msleep(self.enhance_check_interval)
                    # 没空，就重复点击强化
                    self.click(285, 436)
                # 统计强化所使用卡片，把主卡也加入卡片使用
                card_infos = sub_card_infos + [main_card_info]
                self.edit_statistics(2, card_infos)
                # 强化之后截图强化区域，判定成功/失败，输出日志
                self.enhance_log(main_card_info, sub_card_infos, enhance_plan["四叶草"]['种类'])
                # 点掉强化区域的卡片后，才能再次进行强化
                self.click(287, 343)
                # 强化次数+1
                self.enhance_times += 1
                self.enhance_count += 1
                # 是否循环标识符
                self.cards_enough = True
                return
        # 如果遍历了强化方案后，发现已经没有卡可以强化了，就把此时的强化字典保存起来，作为临时卡片字典（该方法不完美，可能导致可用卡片重复添加）
        for card_info in self.card_dict.values():
            # 创建一个包含卡片名称与星级的键
            card_info_key = f"{card_info['卡片名称']}-{card_info['星级']}"
            # 如果该键不存在于临时卡片字典中，向临时卡片字典中添加它,值为1就行
            if card_info_key not in self.temp_card_level_dict:
                self.temp_card_level_dict[card_info_key] = 1
        self.cards_enough = False
        return

    # 是否可强化检查,还能修改临时强化字典，保证低级方案不会使用高级方案主卡存在时的副卡，以及返回位置列表
    def can_enhance(self, main_card_info: dict, sub_card_infos: list) -> tuple[bool, list]:
        # 初始化点击位置列表
        positions = []
        # 检查是否存在主卡
        for position, card_info in list(self.card_dict.items()):
            if card_info == main_card_info:
                # 向列表添加主卡位置
                positions.append(position)
                # 从字典中删除找到的主卡
                del self.card_dict[position]
                break
        if not positions:
            return False, None
        # 遍历副卡信息列表
        for sub_card_info in sub_card_infos:
            # 查找副卡信息是否在self.card_dict中
            found = False
            for position, card_info in list(self.card_dict.items()):  # 使用list来避免在遍历时修改字典
                if card_info == sub_card_info:
                    found = True
                    # 向列表添加副卡位置
                    positions.append(position)
                    # 从字典中删除找到的副卡
                    del self.card_dict[position]
                    break
            # 如果有任何一张副卡不在self.card_dict中，返回False
            if not found:
                return False, None
        # 如果所有副卡信息都在self.card_dict中，返回True，还有它们的位置信息
        return True, positions

    # 强化日志输出
    def enhance_log(self, main_card_info: dict, sub_card_infos: list, clover: str):
        # 先分离出各种信息
        main_card_name = main_card_info["卡片名称"]
        main_card_level = main_card_info["星级"]
        success = self.check_enhance_result(int(main_card_level))
        text = f"{main_card_level}星{main_card_name}强化"
        if success:
            text += "成功！"
        else:
            text += "失败！"
        text += "使用卡片："
        for sub_card_info in sub_card_infos:
            sub_card_name = sub_card_info["卡片名称"]
            sub_card_level = sub_card_info["星级"]
            text += f"[{sub_card_level}星{sub_card_name}]"
        # 添加上四叶草种类
        if clover != "无":
            text += f"，使用[{clover}四叶草]"
        # 给不同星级的强化成功日志加上不同颜色
        if success:
            if int(main_card_level) <= 4:
                text = f"<font color='gray'>{text}</font>"
            elif int(main_card_level) <= 6:
                text = f"<font color='green'>{text}</font>"
            elif int(main_card_level) <= 8:
                text = f"<font color='blue'>{text}</font>"
            elif int(main_card_level) <= 10:
                text = f"<font color='purple'>{text}</font>"
            else:
                text = f"<font color='orange'>{text}</font>"
        else:
            text = f"<font color='red'>{text}</font>"
        self.log_signal.emit(text)

    # 强化结果判定
    def check_enhance_result(self, level):
        # 截图强化区域
        result_img = self.get_image(267, 323, 40, 50)
        level_img = result_img[5:12, 5:12]
        success_img = self.resources.level_images[level + 1]
        level_list = [] # 初始化数组。 数组内数分别为卡片星级，卡片强化后星级
        # 判定强化结果
        if np.array_equal(level_img, success_img):
            level_list = [level, level + 1]
            self.edit_statistics(3, level_list)
            return True
        else:
            if level <= 5:
                level_list = [level, level]
            else:
                level_list = [level, level - 1]
            self.edit_statistics(3, level_list)
            return False 
    
    # 当前位置判定 position——0:可以看到合成屋图标的位置 1:可以看到制作说明图标的位置 2:可以看到强化说明图标的位置
    def check_position(self):
        position = None
        # 第一次判断，合成屋图标
        img = self.get_image(672, 550, 15, 15)
        if np.array_equal(img, self.resources.compose_icon):
            position = 0
            return position
        # 第二次判断，根据XX说明判断目前所处位置
        img = self.get_image(816, 28, 69, 22)
        if np.array_equal(img, self.resources.produce_help_icon):
            position = 1
            return position
        elif np.array_equal(img, self.resources.enhance_help_icon):
            position = 2
            return position
        return None
    
    # 防呆检测，避免一些奇怪的问题
    def dull_detection(self):
        # 能使用的强卡方案里，有没有副卡全是无的？
        for j in range(self.max_level, self.min_level, -1):
            # 初始化无计数
            None_count = 0
            # 遍历可用的强卡方案
            for k in range(1, 4):
                subcard_level = self.settings["强化方案"][f"{j-1}-{j}"][f'副卡{k}'].get('星级', '无')
                if subcard_level == "无":
                    # 将无计数加一
                    None_count += 1
                # 如果有三个无，就直接弹窗，并停止运行
                if None_count == 3:
                    self.show_dialog_signal.emit("这……", f"{j-1}-{j}方案的副卡全是无，回去再设置设置吧……")
                    self.onStop()
                    return
        # 通过防呆检测，就没事，正常开始
        return

    # 劲 爆 弹 窗
    @QtCore.pyqtSlot(str, str)
    def show_dialog(self, title, message):
        # 停止运行
        self.is_running = False
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        # 同时显示系统通知 打包后有BUG，找不到获取平台的方法，原因不明 这BUG起码四年了
        # 解决方法：打包时添加--hidden-import plyer.platforms.win.notification
        plyer.notification.notify(
            title=title,
            message=message,
            app_name='天知强卡器',
            timeout=5  # 通知显示的时间
        )
        msg.exec()
        

    # 输出日志
    def send_log_message(self, message):
        self.output_log.append(f"{message}")
        # 输出完成后，自动滚动到最新消息
        self.output_log.verticalScrollBar().setValue(
            self.output_log.verticalScrollBar().maximum()
        )

        
class EnhancerThread(QtCore.QThread):
    showDialogSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.enhancer = tenchi_cards_enhancer

    # 强卡器循环,分为3种模式，分别是：1.固定制卡 2.混合制卡 3.动态制卡
    def run(self):        
        # 读取制卡模式
        produce_mode = int(self.enhancer.settings["个人设置"]["制卡模式"])
        # 初始化位置，保证位置在合成屋或强化页面
        if not self.init_position():
            return
        while self.enhancer.is_running:
            # 如果强化到了一定次数，就退出重进一下合成屋，防止卡顿
            if self.enhancer.enhance_times >= self.enhancer.reload_count:
                self.reload()
            position = self.enhancer.check_position() # 获取位置标识
            if position == 1 and produce_mode != 2: # 如果是动态制卡模式，会跳过这个制作
                # 遍历制卡方案，添加到队列
                self.enhancer.create_produce_queue()
            if position == 1 and produce_mode != 0: # 如果是固定制卡模式，会跳过这个制作
                # 调用动态队列添加方法
                self.enhancer.dynamic_card_producer()
                # 重置临时字典
                self.enhancer.temp_card_level_dict = {}
            # 执行队列
            self.enhancer.execute_produce_queue()
            # 如果停止标识，则停止
            if not self.enhancer.is_running:
                break
            # 遍历完所有制作后，点击卡片强化
            QtCore.QThread.msleep(500)
            self.enhancer.click(108, 320)
            QtCore.QThread.msleep(500)
            # 先判定是否在卡片强化页面，如果在，开始强化
            position = self.enhancer.check_position()
            if position == 2:
                # 强化主函数
                self.enhancer.main_enhancer()
            # 数组卡片全部强化完成后，点击卡片制作，再次循环
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(800)

    # 初始化位置,使用截图与识图函数判断当前位置，一共有三次判断：1.判断窗口上是否有合成屋图标，如果有就点击 2.根据右上角的“XX说明”判断目前所处位置，分别执行不同操作 
    def init_position(self) -> bool:
        position = self.enhancer.check_position() # 获取位置标识
        if position == 0:
            # 先点击进入合成屋
            self.enhancer.click(685, 558)
            # 停顿久一些，加载图片
            QtCore.QThread.msleep(1500)
            # 打开运行标志，进入主循环
            self.enhancer.is_running = True
            return True
        elif position == 1:
            # 打开运行标志 直接进入主循环
            self.enhancer.is_running = True
            return True
        elif position == 2:
            # 打开运行标志
            self.enhancer.is_running = True
            # 强化主函数
            self.enhancer.main_enhancer()
            # 点击卡片制作，进入主循环
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(1500)
            return True
        else:
            # 未知位置，弹窗提示
            self.showDialogSignal.emit("哇哦", "未知位置，你好像被卡住了")
            # 停止运行
            self.enhancer.is_running = False
            return False

    def reload(self):
        # 点击右上角的红叉
                self.enhancer.click(914, 38)
                QtCore.QThread.msleep(1500)
                # 重新点击合成屋
                self.enhancer.click(685, 558)
                QtCore.QThread.msleep(1000)
                # 归零强化次数
                self.enhancer.enhance_times = 0

    def start_loop(self):
        if self.enhancer.handle is not None:
            self.start()
        else:
            self.showDialogSignal.emit("喂！", "你还没获取句柄呢！")

# 仅强卡线程
class enhanceonlyThread(QtCore.QThread):
    showDialogSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.enhancer = tenchi_cards_enhancer
    
    def run(self):
        # 判断当前位置，如果不在强化页面，就直接弹窗
        position = self.enhancer.check_position()
        if position!= 2:
            self.showDialogSignal.emit("等等", "先把页面调到卡片强化后再点我啊！")
            return
        # 截图后强化
        self.enhancer.main_enhancer()
        # 强化完成后弹窗
        self.showDialogSignal.emit("哇哦", "强化完成！没有可强化的卡片了")
        return
    
    def start_enhance(self):
        # 存在句柄时，打开运行状态，启动线程
        if self.enhancer.handle is not None:
            self.enhancer.is_running = True
            self.start()
        else:
            self.showDialogSignal.emit("喂！", "你还没获取句柄呢！")

# 主函数    
def main():
    app = QtWidgets.QApplication(sys.argv)
    # 设置默认字体
    font_id = QtGui.QFontDatabase.addApplicationFont(resource_path("items/font/font.ttf"))
    if font_id != -1:
            font_family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
            font = QtGui.QFont(font_family, 10)
            app.setFont(font)
    enhancer = tenchi_cards_enhancer()
    enhancer.show()
    sys.exit(app.exec())

# 设置进程为每个显示器DPI感知V2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = c_void_p(-4)
windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)

if __name__ == '__main__':
    main()