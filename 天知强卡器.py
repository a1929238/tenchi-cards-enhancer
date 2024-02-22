# 天知强卡器，打算用pyqt5做GUI
# setting字典的结构为:setting[type][name][count]
# 统计数据字典的结构为:statistics[type][name][count]
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


class tenchi_cards_enhancer(QtWidgets.QMainWindow):
    # 定义信号
    show_dialog_signal = QtCore.pyqtSignal(str, str)
    
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
        ui_path = self.resource_path('GUI/天知强卡器.ui')
        uic.loadUi(ui_path, self)
        # 设置窗口图标
        self.setWindowIcon(QtGui.QIcon("items/icon/furina.ico"))

        # 初始化窗口dpi
        self.dpi = self.get_system_dpi()
        
        # 变量初始化
        self.version = "0.1.0"
        self.handle = None
        self.card_dict = {}
        self.is_running = False
        self.offset = 0
        self.cards_enough = False
        self.enhance_times = 0
        self.enhance_count = 0
        self.produce_count = 0
        self.card_info_dict = {}
        self.settings = self.load_settings()  # 读取设置作为全局变量
        self.statistics = self.load_statistics()  # 读取统计数据作为全局变量
        self.min_level = int(self.settings["个人设置"]["最小星级"])
        self.max_level = int(self.settings["个人设置"]["最大星级"])
        self.reload_count = int(self.settings["个人设置"]["刷新次数"])
        self.produce_interval = int(self.settings["个人设置"]["制卡间隔"])
        self.enhance_interval = int(self.settings["个人设置"]["强卡间隔"])
        self.enhance_check_interval = int(self.settings["个人设置"]["强卡检测间隔"])

        # 背景遮盖层初始化
        self.frosted_layer.lower()  # 将半透明层放到底层

        # 将GUI控件与脚本连接
        # 初始化日志信息
        self.output_log.setOpenExternalLinks(True)
        self.init_log_message()
        
        # 召唤动态芙芙！
        self.furina_movie = QtGui.QMovie("items/icon/furina_shake.gif")
        self.furina.setMovie(self.furina_movie)
        self.furina_movie.start()
        self.furina.handleChanged.connect(self.update_handle_display)

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


        # 配置，初始化配方选择菜单
        self.init_recipe()
        # 配置，初始化四叶草选择菜单
        self.init_clover()
        # 配置，初始化副卡选择菜单
        self.init_subcard()
        # 初始化香料菜单
        self.init_spice()
        # 初始化个人设置页
        self.init_setting()
        # 初始化统计数据页
        self.init_statistics()
        # 初始化状态栏
        self.init_statusbar()

        # 连接测试按钮
        # self.test_btn.clicked.connect(self.test)

    # 打包后绝对路径函数
    def resource_path(self, relative_path):
        # 获取资源的绝对路径。它用于访问在 --onefile 模式下的资源。
        try:
            # PyInstaller 创建的临时文件夹
            base_path = sys._MEIPASS
        except AttributeError:
            # 如果应用程序没有被打包，则使用普通的绝对路径
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    
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
        
    
    # 测试功能
    def test(self):
        # 测试强化结果截图
        # self.check_enhance_result(0)

        # 测试位置检测
        # self.check_position()

        # 测试合成屋卡片切割

        # 测试合成屋字典获取
        #img = self.get_image(559, 91, 343, 456)
        #cv2.imwrite(f'test.png', img)
        #self.get_card_dict(img)
        #print(self.card_dict)
        #return

        # 测试主卡是否还在
        # self.check_main_card()
        # 获取副卡图片
        img = self.get_image(267, 253, 40, 50)
        cv2.imwrite(f'test.png', img)
        return

    # 保存当前设置
    def save_current_settings(self):
        # 调用保存设置函数
        self.save_settings(self.settings)

    # 初始化日志信息
    def init_log_message(self):
        self.send_log_message(f"当当！天知强卡器启动成功！目前版本号为{self.version}")
        self.send_log_message("使用前请关闭二级密码")
        self.send_log_message("目前仅支持360游戏大厅,但支持任何系统缩放")
        self.send_log_message("目前无法应对美食大赛任务，请注意自己的美食大赛完成进度")
        self.send_log_message("[github] <a href=https://github.com/a1929238/tenchi-cards-enhancer>https://github.com/a1929238/tenchi-cards-enhancer</a>")
        self.send_log_message("[QQ群 交流·反馈·催更] 786921130 ")
        self.send_log_message("如果觉得好用的话，把软件推荐给更多的人嘛，反正不要钱~")
    
    # 初始化选卡菜单
    def init_recipe(self):
        recipe_dir = "items/recipe"
        # 获取卡片属性字典
        with open(self.resource_path('GUI/card_dict/card_info_dict.json'), 'r', encoding='utf-8') as f:
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
                self.recipe_box.addItem(card_text)
            # 读取设置中的所选卡片，如果有的话，就自动选择这个卡片,这里要加上卡片的属性
            selected_card_name = self.settings.get("所选卡片", {}).get("卡片名称", "无")
            selected_card = f'{selected_card_name}-{self.card_info_dict.get(selected_card_name, "未知")}'
            # 在 QComboBox 中查找这个卡片名称对应的索引
            index = self.recipe_box.findText(selected_card)
            if index >= 0:
                # 如果找到了，设置 QComboBox 当前选中的索引
                self.recipe_box.setCurrentIndex(index)
            else:
                # 如果没找到，就默认选择第一个, 并修改设置文件，让它也是第一个
                self.recipe_box.setCurrentIndex(0)
                self.on_recipe_selected(0)
            # 连接信号，每次更改选项时，都发出信号，保存字典
            self.recipe_box.currentIndexChanged.connect(self.on_recipe_selected)
    
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
    
    # 初始化副卡菜单
    def init_subcard(self):
        for i in range(3):
            for j in range(16):
                subcard_box_name = f"subcard{i+1}_{j}"
                subcard_box = getattr(self, subcard_box_name)
                added_items = set() # 为了避免重复，加上集合
                # 给每个副卡菜单添加上对应等级的副卡选项
                for n in range(3):
                    value = j - n
                    if value >= 0 and value not in added_items:
                        subcard_box.addItem(str(value))
                        added_items.add(value)
                # 不要忘记加上无
                subcard_box.addItem("无")
                # 菜单选项添加完后，根据设置文件，设置菜单的当前选中项
                selected_subcard = self.settings.get("强化方案", {}).get(f"{j}-{j+1}", {}).get(f"副卡{i+1}", "无")
                # 在 QComboBox 中查找这个卡片名称对应的索引
                index = subcard_box.findText(selected_subcard)
                if index >= 0:
                    # 如果找到了，设置 QComboBox 当前选中的索引
                    subcard_box.setCurrentIndex(index)
                # 每次更改选项时，都要保存字典
                subcard_box.currentIndexChanged.connect(self.on_subcard_selected)
    
    # 初始化四叶草菜单
    def init_clover(self):
        for i in range(16):
            clover_box_name = f"clover{i}"
            clover_box = getattr(self, clover_box_name)
            # 给每个四叶草菜单加上所有四叶草
            clover_dir = "items/clover"
            if os.path.exists(clover_dir):
                for filename in os.listdir(clover_dir):
                    clover_name = filename.replace("四叶草.png", "")
                    clover_box.addItem(clover_name)
            # 加上无
            clover_box.addItem("无")
            # 菜单选项添加完后，根据设置文件，设置菜单的当前选中项
            selected_clover = self.settings.get("强化方案", {}).get(f"{i}-{i+1}", {}).get("四叶草", "无")
            # 在 QComboBox 中查找这个卡片名称对应的索引
            index = clover_box.findText(selected_clover)
            if index >= 0:
                # 如果找到了，设置 QComboBox 当前选中的索引
                clover_box.setCurrentIndex(index)
            # 每次更改选项时，都要保存字典
            clover_box.currentIndexChanged.connect(self.on_clover_selected)

    # 初始化香料菜单
    def init_spice(self):
        # 根据设置字典，初始化香料次数选择
        # 获取生产方案字典
        production_plan = self.settings.get("生产方案", {})
        # 将字典的键（香料名）提取到一个列表中
        spices = list(production_plan.keys())
        for i in range(len(spices)):
            spice_name = spices[i]
            spice_count = production_plan[spice_name]
            # 获取对应的香料控件
            spice_box_name = f"spice{i}"
            spice_box = getattr(self, spice_box_name)
            # 设置香料盒的数量
            spice_box.setValue(int(spice_count))
            # 每次更改次数时，都要保存字典
            spice_box.valueChanged.connect(self.on_spice_selected)
        
                

    # 初始化个人设置菜单
    def init_setting(self):
        # 从个人设置字典中读取数据，初始化控件
        bind_only = self.settings.get("个人设置", {}).get("只用绑定卡", False)
        unbind_clover_replace = self.settings.get("个人设置", {}).get("不绑草替代", False)
        self.max_level_input.setValue(self.max_level)
        self.min_level_input.setValue(self.min_level)
        self.bind_btn.setChecked(bind_only)
        self.bind_btn1.setChecked(unbind_clover_replace)
        self.reload_count_input.setValue(self.reload_count)
        self.produce_interval_input.setValue(self.produce_interval)
        self.enhance_interval_input.setValue(self.enhance_interval)
        self.enhance_check_interval_input.setValue(self.enhance_check_interval)
        self.produce_times_input.setValue(int(self.settings.get("个人设置", {}).get("制卡次数上限", 0)))

        # 把控件都连接上字典
        self.max_level_input.valueChanged.connect(self.on_setting_changed)
        self.min_level_input.valueChanged.connect(self.on_setting_changed)
        self.bind_btn.clicked.connect(self.on_setting_changed)
        self.bind_btn1.clicked.connect(self.on_setting_changed)
        self.reload_count_input.valueChanged.connect(self.on_setting_changed)
        self.produce_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_check_interval_input.valueChanged.connect(self.on_setting_changed)
        self.produce_times_input.valueChanged.connect(self.on_setting_changed)

    # 初始化状态栏
    def init_statusbar(self):
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



    
    # 正在选择的卡片，以及实时保存
    def on_recipe_selected(self, index):
        selected_recipe_name = self.recipe_box.itemText(index)
        # 把卡片属性的注释分离出来
        selected_recipe = selected_recipe_name.split("-")[0]
        # 更新设置字典中的所选卡片
        self.settings["所选卡片"]["卡片名称"] = selected_recipe
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存香料配置
    def on_spice_selected(self, value):
        # 从信号发出名分离出数字
        sender = self.sender()
        spice_level = int(sender.objectName().replace('spice', ''))
        # 更新字典中的香料配置
        production_plan = self.settings.get("生产方案", {})
        spices = list(production_plan.keys())
        for i in range(len(spices)):
            spice_name = spices[i]
            if i == spice_level:
                production_plan[spice_name] = f"{value}"
        self.settings["生产方案"] = production_plan
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
        self.settings["强化方案"][scheme_key]["四叶草"] = selected_clover
        # 保存设置
        self.save_settings(self.settings)
    
    # 实时保存副卡配置
    def on_subcard_selected(self, index):
        # 从信号发出名分离出数字
        sender = self.sender()
        subcard_type, subcard_level = sender.objectName().split("_")[0].replace('subcard', ''), int(sender.objectName().split("_")[1])
        selected_subcard = sender.itemText(index)
        # 更新字典中的副卡配置
        scheme_key = f"{subcard_level}-{subcard_level+1}"
        if scheme_key not in self.settings["强化方案"]:
            self.settings["强化方案"][scheme_key] = {}
        self.settings["强化方案"][scheme_key][f"副卡{subcard_type}"] = selected_subcard
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
        elif sender_name == "bind_btn":
            self.settings["个人设置"]["只用绑定卡"] = sender.isChecked()
        elif sender_name == "bind_btn1":
            self.settings["个人设置"]["不绑草替代"] = sender.isChecked()
        elif sender_name == "reload_count_input":
            self.settings["个人设置"]["刷新次数"] = f"{value}"
            self.reload_count = value
        elif sender_name == "produce_interval_input":
            self.settings["个人设置"]["制卡间隔"] = f"{value}"
            self.produce_interval = value
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


    # 识图函数，分割图片并识别，分成3种分割规则——0:配方分割，1:香料/四叶草分割, 2:卡片分割
    def match_image(self, image, target_image, type, bind=None):
        # 初始化bind参数
        if bind is None:
            bind = self.settings["个人设置"]["只用绑定卡"]
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
            bind_image = self.imread("items/bind_icon/spice_bind.png")
            for j in range(column):
                block = image[0: 49, j * 49:(j + 1) * 49]
                # 先识别种类，再识别是否绑定
                # 格式与FAA标准格式不同，Y轴要往上5个像素
                kind = block[4: 28, 4: 42]
                if np.array_equal(kind, target_image):
                    # 识别到种类，开始识别是否绑定,根据设置判断是否需要绑定
                    bind_flag = block[38:45, 3:9]
                    if bind == True:
                        if np.array_equal(bind_flag, bind_image):
                        # 返回香料/四叶草位置
                            return j
                    else:
                        if not np.array_equal(bind_flag, bind_image):
                        # 返回香料/四叶草位置
                            return j
            return None
        elif type == 2: # 卡片分割
            # 初始化卡片字典
            temp_card_dict = {}
            # 方法更新，用模板匹配图片中的第一行，然后把色块以上的图片全部切掉，再识别。这样无论滑块在哪里，都能确保找到七行道具
            line_img = self.imread("items/position/line.png")
            if line_img.shape[0] <= image.shape[0] and line_img.shape[1] <= image.shape[1]:
                # 进行模板匹配
                result = cv2.matchTemplate(image, line_img, cv2.TM_CCOEFF_NORMED)
                # 遍历匹配结果
                for y in range(result.shape[0]):
                    if result[y, 0] >= 0.30:
                        self.offset = y # 保存偏移值
                        # 裁剪图像，保留标记位置以下的七格像素
                        image = image[y+1:400+y]
                        break
            # 按照分割规则，先把图片分割成49 * 57像素的块，然后再分割出3个区域：卡片本体，绑定标志，星级标志
            rows = 7
            column = 7
            bind_image = self.imread("items/bind_icon/card_bind.png")
            for i in range(rows):
                for j in range(column):
                    block = image[i * 57:(i + 1) * 57, j * 49:(j + 1) * 49]
                    card = block[22:37, 8:41]
                    if np.array_equal(card, target_image):
                        # 寻找到目标图像，开始检测是否绑定
                        bind_flag = block[45:52, 5:11]
                        if np.array_equal(bind_flag, bind_image):
                            # 是绑定卡，就给卡片字典的对应位置的绑定调整为true
                            temp_card_dict.setdefault(f"{j}-{i}", {})["bind"] = True
                        else:
                            # 不是就False
                            temp_card_dict.setdefault(f"{j}-{i}", {})["bind"] = False
                        level_img = block[8:15, 9:16]
                        # 初始化level
                        level = 0
                        # 用设置里的卡片上下限来只识别指定星级的卡片
                        for k in range(self.min_level, self.max_level+1):
                            level_image = self.imread(f"items/level/{k}.png")
                            if np.array_equal(level_img, level_image):
                                level = k
                                break
                        if self.min_level == 0 and level == 0:
                            level = 0
                            # 0卡是否被视为绑定，取决于个人设置
                            temp_card_dict.setdefault(f"{j}-{i}", {})["bind"] = self.settings["个人设置"]["只用绑定卡"]
                        temp_card_dict.setdefault(f"{j}-{i}", {})["level"] = level        
            # 返回字典，有位置，是否绑定，星级
            return temp_card_dict

        return None, None
    
    # 读取图像函数，读取图像并返回矩阵
    def imread(self, filename):
        # 使用 np.fromfile 读取数据
        data = np.fromfile(filename, dtype=np.uint8)
        # 使用 cv2.imdecode() 解码图像数据
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return image
    
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
            filename = self.resource_path('GUI/default/setting.json')
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
            filename = self.resource_path('GUI/default/statistics.json')
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f) # 返回默认字典，如果设置文件不存在
    
    # 编辑并保存统计数据字典 type——0: 四叶草 1:香料 2:使用卡片 3:强化出卡片
    def edit_statistics(self, type, name, value=1):
        if type == 0: # 四叶草
            self.statistics["使用四叶草总和"] = self.update_dict(self.statistics["使用四叶草总和"], f"{name}四叶草", value)
        elif type == 1: # 香料
            self.statistics["使用香料总和"] = self.update_dict(self.statistics["使用香料总和"], name, value * 5)
        elif type == 2: # 使用卡片
            # 卡片总和不同，name是一个数组，所以要遍历数组后分次添加
            for i in range(len(name)):
                level = name[i]
                self.statistics["使用卡片总和"] = self.update_dict(self.statistics["使用卡片总和"], level, value)
        elif type == 3: # 强化出卡片，强化次数，成功次数
            # 强化出卡片也是一个数组，有两个值，分别是强化卡片的星级和强化前的星级，以此统计对应星级的强化次数，还能搞出成功次数
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
    def get_recipe(self, target_img):
        for i in range(5):
            #点击五下上滑键，初始化配方窗口位置
            self.click(910, 97)
            QtCore.QThread.msleep(200)
        # 第一次截图并识图
        img = self.get_image(559, 90, 343, 196)

        # 读取截图中的配方，并与目标配方匹配
        x, y = self.match_image(img, target_img, 0)
        if x is not None:
            # 匹配成功，点击配方位置
            self.click(580+(x*49), 110+(y*49))
            return
        # 匹配失败，鼠标滑动22个像素，再次截图
        for j in range(1):
            self.drag(910, 120 + j * 2, 0, 22)
            QtCore.QThread.msleep(500)
        # 匹配配方，如果还不成功，就再下滑一次
        img = self.get_image(559, 92, 343, 196)
        x, y = self.match_image(img, target_img, 0)
        if x is not None:
            # 获取目标配方位置后，点击配方
            self.click(580+(x*49), 110+(y*49))
            return
        # 匹配失败，弹出弹窗
        self.show_dialog_signal.emit("危", "配方识别失败,请检查自己的配方")
        return
        
    # 点击香料/四叶草 type——0:香料,1:四叶草 level——字符串，对不同的type匹配不同的图片
    def get_spice_and_clover(self, type, level, bind=None):
        if bind is None:
            bind = self.settings["个人设置"]["只用绑定卡"]
        # 直接第一次截图，查找是否有目标香料/四叶草
        img = self.get_image(33, 526, 490, 49)
        if type == 0:
            # 如果level == 不放香料,那就不放香料
            if level == "不放香料":
                return
            # 识图，点击对应香料
            spice_img = self.imread(f"items/spice/{level}.png")
            x = self.match_image(img, spice_img, 1)
            if x is not None:
                self.click(55 + 49 * x, 550)
                return
            # 没找到，就点击五下右滑键，再截一次图
            for j in range(5):
                self.click(532, 562)
                QtCore.QThread.msleep(250)
            img = self.get_image(33, 526, 490, 49)
            # 重复前面的读图操作
            x = self.match_image(img, spice_img, 1)
            if x is not None:
                self.click(55 + 49 * x, 550)
                return
            # 如果还是没有找到，就弹出dialog，提示没有找到目标香料
            self.show_dialog_signal.emit("什么！", "没有找到目标香料!")
        elif type == 1:
            # 查找对应四叶草,level是字符串
            clover_img = self.imread(f"items/clover/{level}四叶草.png")
            # 点击对应四叶草
            x = self.match_image(img, clover_img, 1, bind)
            if x is not None:
                self.click(55 + 49 * x, 550)
                self.edit_statistics(0, level)
                return        
            # 没找到，就点击五下右滑键，再截一次图
            for j in range(6):
                self.click(532, 562)
                QtCore.QThread.msleep(150)
            img = self.get_image(33, 526, 490, 49)
            # 重复前面的读图操作
            x = self.match_image(img, clover_img, 1, bind)
            if x is not None:
                self.click(55 + 49 * x, 550)
                self.edit_statistics(0, level)
                return
            # 还是没找到，就停止运行
            self.is_running = False
        return
    
    # 强化卡片主函数
    def main_enhancer(self):
        # 还没有想好拖曳几次，悲
        # 尝试方案，拖曳7次，每次拖四格
        # 每次强化，卡片的顺序都会改变，只能强化一次截一次图，直到强卡器返回False，才停止循环
        while self.is_running:
            for i in range(7):
                # 获取截图
                img = self.get_image(559, 91, 343, 456)
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
                # 合成屋卡片拖曳17个像素正好是一格,但是拖曳8次后会有2像素偏移，用新方法就无视偏移啦
                for j in range(4):
                    self.drag(908, 120 + i * 119 + j * 17, 0, 17)
                    QtCore.QThread.msleep(200)
                # 四次拖曳截图都没有获取到卡片，退出循环
                if i == 3:
                    return


    # 获取强化卡片字典
    def get_card_dict(self, img):
        """
        遍历识图当前页面的卡片，然后返回对应格式的字典
        字典格式如下:{
            位置:{
        "level": 星级,
        "card_rank":卡片质量,
        "bind":是否绑定
        }
        }
        """
        # 初始化卡片字典
        self.card_dict = {}
        # 遍历当前页面的卡片,识图出设置中目标卡片
        card_name = self.settings["所选卡片"]["卡片名称"]
        card_image = self.imread(f"items/card/{card_name}.png")
        card_dict = self.match_image(img, card_image, 2)
        if card_dict:
            self.card_dict = card_dict
        
    
    # 生产卡片
    def card_producer(self):
        # 根据设置文件，进行循环
        # 香料顺序由从低到高生产卡片
        for spice_name, count in self.settings["生产方案"].items():
            if int(count):
                # 点击对应香料
                self.get_spice_and_clover(0, spice_name)
                for i in range(int(count)):
                    # 如果检测到停止标识，就退出
                    if not self.is_running:
                        return
                    # 制作多少次~
                    self.click(285, 425)
                    # 使用系统信息标识来动态延迟，失败
                    # self.check_system_message()
                    QtCore.QThread.msleep(self.produce_interval)
                # 输出统计信息
                self.edit_statistics(1, spice_name, int(count))
                # 统计制卡次数
                self.produce_count += int(count)
                if int(self.settings.get("个人设置", {}).get("制卡次数上限", 0)) != 0 and self.produce_count >= int(self.settings.get("个人设置", {}).get("制卡次数上限", 0)):
                    self.show_dialog_signal.emit("登登！", "制卡达到上限啦~")
                    return
        
    

    # 强化卡片，强化当前页所有符合条件的卡片
    def card_enhancer(self):
        # 获取card字典
        card_dict = self.card_dict
        # 初始化当前页面卡片星级总量字典
        card_level_dict = {}
        # 读取主卡空卡槽图片
        main_card_target_img = self.imread("items/position/main_card.png")
        # 读取副卡空卡槽图片
        sub_card_target_img = self.imread("items/position/sub_card.png")
        # 遍历card字典，获得一共有多少星级的卡片
        for position, card_info in card_dict.items():
            # 获得当前卡片字典的星级
            level = card_dict[position]["level"]
            # 获得当前卡片的绑定状态
            bind = card_dict[position]["bind"]
            # 获得当前卡片的质量
            # card_rank = card_dict[i]["card_rank"]
            # 判定用绑定卡/不绑卡
            if bind == self.settings["个人设置"]["只用绑定卡"]:
                # 如果字典中存在level，则给level的计数加1，否则初始化为1
                card_level_dict[level] = card_level_dict.setdefault(level, 0) + 1
        # 按照最高强化卡片，从高到低，遍历设置里的强化方案，获取所需副卡，如果卡片总量大于等于方案所需卡片，就遍历card字典的位置，点击卡片，强化一次
        for j in range(self.max_level, self.min_level, -1):
            # 初始化一个数组来存储当前强化方案所需的所有卡
            subcards = []
            subcards.append(j-1) # 把主卡加进去
            # 获得当前强化方案所需的卡片总量
            for k in range(3):
                subcard_level = (self.settings["强化方案"][f"{j-1}-{j}"].get(f"副卡{k+1}", "无"))
                if subcard_level != "无":
                    subcards.append(int(subcard_level))
            # 保险，如果使用卡片全部低于最低星级，就跳过这次强卡
            if min(subcards) < self.min_level:
                continue
            # 死循环，直到所有卡片都被强化完毕，废案，卡片自己会跑！
            # 用数组来比较，目前是否可以执行这个强化方案
            can_enhance = all(card_level_dict.get(int(subcard), 0) >= subcards.count(subcard) for subcard in subcards)
            # 在比较之后，为了留存高级方案卡片，在等级字典内减去高级方案所需卡片
            for subcard in subcards:
                card_level_dict[subcard] = card_level_dict.get(subcard, 0) - subcards.count(subcard)
                # 如果减去之后对应键值小于零，则从字典中除去对应键
                if card_level_dict[subcard] < 0:
                    del card_level_dict[subcard]
            if can_enhance: # 如果可以强化，就索引card_dict，寻找目标星级卡片的位置
                for subcard in subcards: # 遍历所有强化需要的卡, 顺序为主卡，副卡1，副卡2，副卡3
                    for position, card_info in card_dict.items():
                        if card_info["level"] == subcard and card_info["bind"] == self.settings["个人设置"]["只用绑定卡"]:
                            x, y = int(position.split("-")[0]), int(position.split("-")[1])
                            # 点击目标卡片，千万记得要加上偏移值
                            self.click(580 + x * 49, 115 + y * 57 + self.offset)
                            # 把card_dict里对应位置的卡片删掉，免得重复点击
                            del card_dict[position]
                            break
                # 根据设置，点击四叶草
                if self.settings["强化方案"][f"{j-1}-{j}"].get("四叶草", "无") != "无":
                    self.get_spice_and_clover(1, self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"])
                # 如果没找到四叶草，就会关闭运行标识
                if not self.is_running:
                    # 如果在强化绑定卡时，开启了不绑1,2草替代，就在找不到绑定1,2草时，点击不绑1,2草替代
                    if self.settings["个人设置"]["不绑草替代"] == True and self.settings["个人设置"]["只用绑定卡"] == True and self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"] in ["1级", "2级"]:
                        self.get_spice_and_clover(1, self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"], False)
                        # 重新打开运行标识
                        self.is_running = True
                    else:
                        # 没有就停止，同时发出弹窗
                        self.cards_enough = False
                        self.show_dialog_signal.emit("什么！", "没有找到目标四叶草!")
                        return
                # 点击强化！强化有延迟，最终解决方案是重复识图副卡栏位，如果副卡还在，就一直点强化，直到副卡不在，再点击主卡
                self.click(285, 436)
                # 初始等待时间，这个等待没法规避
                QtCore.QThread.msleep(self.enhance_interval)
                for i in range(10):
                    # 获得副卡槽图片
                    sub_card_image = self.get_image(267, 253, 40, 50)
                    # 判定副卡槽图片是否和副卡空卡槽图片一样
                    if np.array_equal(sub_card_image, sub_card_target_img):
                        break # 卡槽空了就点掉主卡，进行下一次强化
                    # 检测等待时间
                    QtCore.QThread.msleep(self.enhance_check_interval)
                    # 没空，就重复点击强化
                    self.click(285, 436)
                # 统计强化所使用卡片
                self.edit_statistics(2, subcards)
                # 强化之后截图强化区域，判定成功/失败，输出日志
                if self.check_enhance_result(j):
                    # 向日志输出强化信息
                    self.send_log_message(f'{self.settings["所选卡片"]["卡片名称"]}，{self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"]}四叶草，{j-1}星上{j}星强化成功')
                else:
                    # 向日志输出强化信息
                    self.send_log_message(f'{self.settings["所选卡片"]["卡片名称"]}，{self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"]}四叶草，{j-1}星上{j}星强化失败')
                # 点掉强化区域的卡片后，才能再次进行强化
                self.click(287, 343)
                # 保险装置，检查主卡位是不是空的，只检查10次，每次间隔200毫秒
                for i in range(10):
                    # 获得主卡槽图片
                    main_card_img = self.get_image(267, 323, 40, 50)
                    if np.array_equal(main_card_img, main_card_target_img):
                        break # 上面没卡了就强化下一次
                    # 检测等待时间
                    QtCore.QThread.msleep(self.enhance_check_interval)
                    self.click(287, 343)
                # 强化次数+1
                self.enhance_times += 1
                self.enhance_count += 1
                # 是否循环标识符
                self.cards_enough = True
                break
            else:
                self.cards_enough = False
        return
    
    # 强化结果判定
    def check_enhance_result(self, level):
        # 截图强化区域
        result_img = self.get_image(267, 323, 40, 50)
        level_img = result_img[5:12, 5:12]
        success_img = self.imread(f"items/level/{level}.png")
        level_list = [] # 初始化数组。 数组内数分别为卡片星级，卡片强化后星级
        # 判定强化结果
        if np.array_equal(level_img, success_img):
            level_list = [level - 1, level]
            self.edit_statistics(3, level_list)
            return True
        else:
            if level <= 6:
                level_list = [level - 1, level - 1]
                self.edit_statistics(3, level_list)
            else:
                level_list = [level - 1, level - 2]
                self.edit_statistics(3, level_list)
            return False 
    
    # 当前位置判定 position——0:可以看到合成屋图标的位置 1:可以看到制作说明图标的位置 2:可以看到强化说明图标的位置
    def check_position(self):
        position = None
        # 第一次判断，合成屋图标
        img = self.get_image(672, 550, 15, 15)
        if np.array_equal(img, self.imread("items/position/合成屋.png")):
            position = 0
            return position
        # 第二次判断，根据XX说明判断目前所处位置
        img = self.get_image(816, 28, 69, 22)
        if np.array_equal(img, self.imread("items/position/制作说明.png")):
            position = 1
            return position
        elif np.array_equal(img, self.imread("items/position/强化说明.png")):
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
            for k in range(3):
                subcard_level = (self.settings["强化方案"][f"{j-1}-{j}"].get(f"副卡{k+1}", "无"))
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

    # 强卡器循环
    def run(self):        
        # 读取用户设置，根据设置进行下一步操作
        target_image_path = "items/recipe/" + self.enhancer.settings["所选卡片"]["卡片名称"] + "配方.png"
        target_image = self.enhancer.imread(target_image_path)
        # 使用截图与识图函数判断当前位置，一共有三次判断：1.判断窗口上是否有合成屋图标，如果有就点击 2.根据右上角的“XX说明”判断目前所处位置，分别执行不同操作 
        position = self.enhancer.check_position() # 获取位置标识
        if position == 0:
            # 先点击进入合成屋
            self.enhancer.click(685, 558)
            # 停顿久一些，加载图片
            QtCore.QThread.sleep(1)
            # 打开运行标志，进入主循环
            self.enhancer.is_running = True
        elif position == 1:
            # 打开运行标志 直接进入主循环
            self.enhancer.is_running = True
        elif position == 2:
            # 打开运行标志
            self.enhancer.is_running = True
            # 强化主函数
            self.enhancer.main_enhancer()
            # 点击卡片制作，进入主循环
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(500)
        else:
            # 未知位置，弹窗提示
            self.showDialogSignal.emit("哇哦", "未知位置，你好像被卡住了")
            # 停止运行
            self.enhancer.is_running = False
            return
        while self.enhancer.is_running:
            # 如果强化到了一定次数，就退出重进一下合成屋，防止卡顿
            if self.enhancer.enhance_times >= self.enhancer.reload_count:
                # 点击右上角的红叉
                self.enhancer.click(914, 38)
                QtCore.QThread.msleep(1000)
                # 重新点击合成屋
                self.enhancer.click(685, 558)
                QtCore.QThread.msleep(1000)
                # 归零强化次数
                self.enhancer.enhance_times = 0
            position = self.enhancer.check_position() # 获取位置标识
            if position == 1:
                # 如果目前所处界面为卡片制作，首先初始化配方窗口位置，再拖曳截图，遍历判断是否与匹配用户所选配方
                # 点击配方
                self.enhancer.get_recipe(target_image)
                # 遍历制作生产方案中的所有卡片
                self.enhancer.card_producer()
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
                # 点一下滑块的最上端
                self.enhancer.click(908, 120)
                # 强化主函数
                self.enhancer.main_enhancer()
            # 数组卡片全部强化完成后，点击卡片制作，再次循环
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(500)

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
    font_id = QtGui.QFontDatabase.addApplicationFont("items/font/font.ttf")
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