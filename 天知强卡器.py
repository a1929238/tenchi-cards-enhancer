# 天知强卡器，打算用pyqt5做GUI
# setting字典的结构为:setting[type][name][count]
# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import sys
import win32gui
import win32api
import win32con
import win32ui
import json
from ctypes import windll
import numpy as np
import os
import cv2

class tenchi_cards_enhancer(QtWidgets.QMainWindow):
    # GUI界面
    def __init__(self):
        super(tenchi_cards_enhancer, self).__init__()
        # 加载UI文件
        uic.loadUi('天知强卡器.ui', self)
        # 设置窗口图标
        self.setWindowIcon(QtGui.QIcon("items/icon/furina.ico"))

        # 变量初始化
        self.version = "0.0.1"
        self.handle = None
        self.card_dict = {}
        self.is_running = False
        self.offset = 0
        self.cards_enough = False
        self.enhance_times = 0
        self.settings = self.load_settings()  # 读取设置作为全局变量
        self.min_level = int(self.settings["个人设置"]["最小星级"])
        self.max_level = int(self.settings["个人设置"]["最大星级"])

        # 将GUI控件与脚本连接
        # 给日志输出第一条信息！
        self.send_log_message("天知强卡器启动成功！目前版本号为{self.version}".format(self=self))
        self.send_log_message("使用前请关闭二级密码，目前版本号较低，请使用小号做实验后再使用")
        self.send_log_message("统计及替换等功能尚未完工，请等待后续版本")
        self.send_log_message("[github] https://github.com/a1929238/tenchi-cards-enhancer")
        # 召唤动态芙芙！
        self.furina_movie = QtGui.QMovie("items/icon/芙芙摇（小尺寸）.gif")
        self.furina.setMovie(self.furina_movie)
        self.furina_movie.start()
        self.furina.__class__ = DraggableLabel
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

        # 连接测试按钮
        self.test_btn.clicked.connect(self.test)

    # 开始按钮
    def onStart(self):
        self.startbtn.setEnabled(False)
        self.stopbtn.setEnabled(True)
        self.EnhancerThread.start_loop()

    # 停止按钮
    def onStop(self):
        self.EnhancerThread.stop()
        self.startbtn.setEnabled(True)
        self.stopbtn.setEnabled(False)
    
    # 仅强卡按钮
    def enhanceronly(self):
        # 初始化按钮
        self.is_running = True
        self.stopbtn.setEnabled(True)
        self.enhanceonlyThread.start_enhance()
        
    
    # 测试功能
    def test(self):
        # 测试主循环
        # self.main_loop()

        # 测试卡片分割
        # image = Image.open("test3.png")
        # target_image = Image.open("target.png")
        # self.match_image(image, target_image, 2)

        # 测试香料获取
        # self.get_spice_and_clover(0, 7)

        # 测试卡片截图与拖曳
        """
        img = self.get_image(559, 91, 343, 456)
        cv2.imwrite("test1.png", img)
        # 合成屋卡片拖曳17个像素正好是一格,但是拖曳8次后会有2像素偏移，使用切片操作偏移
        for i in range(8):
            self.drag(908, 120 + i * 17, 0, 17)
            QtCore.QThread.msleep(200)
        img = self.get_image(559, 91, 343, 456)
        img = self.edit_img(img, 2)
        cv2.imwrite("test2.png", img)
        for j in range(8):
            self.drag(908, 256 + j * 17, 0, 17)
            QtCore.QThread.msleep(200)
        img = self.get_image(559, 91, 343, 456)
        img = self.edit_img(img, 4)
        cv2.imwrite("test3.png", img)
        """

        # 测试强化结果截图
        # self.check_enhance_result(0)

        # 测试位置检测
        # self.check_position()

        # 测试合成屋卡片切割

        # 测试合成屋字典获取
        img = self.get_image(559, 91, 343, 456)
        cv2.imwrite(f'test.png', img)
        self.get_card_dict(img)
        print(self.card_dict)
        return

    # 保存当前设置
    def save_current_settings(self):
        # 调用保存设置函数
        self.save_settings(self.settings)
    
    # 初始化选卡菜单
    def init_recipe(self):
        recipe_dir = "items/recipe"
        if os.path.exists(recipe_dir):
            for filename in os.listdir(recipe_dir): 
                recipe_name = filename.replace("配方.png", "")
                self.recipe_box.addItem(recipe_name)
            # 读取设置中的所选卡片，如果有的话，就自动选择这个卡片
            selected_card_name = self.settings.get("所选卡片", {}).get("卡片名称", None)
            # 在 QComboBox 中查找这个卡片名称对应的索引
            index = self.recipe_box.findText(selected_card_name)
            if index >= 0:
                # 如果找到了，设置 QComboBox 当前选中的索引
                self.recipe_box.setCurrentIndex(index)
            # 每次更改选项时，都要保存字典
            self.recipe_box.currentIndexChanged.connect(self.on_recipe_selected)
    
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
        max_level = int(self.settings.get("个人设置", {}).get("最大星级", 8))
        min_level = int(self.settings.get("个人设置", {}).get("最小星级", 0))
        bind_only = self.settings.get("个人设置", {}).get("只用绑定卡", False)
        unbind_clover_replace = self.settings.get("个人设置", {}).get("不绑草替代", False)
        self.max_level_input.setValue(max_level)
        self.min_level_input.setValue(min_level)
        self.bind_btn.setChecked(bind_only)
        self.bind_btn1.setChecked(unbind_clover_replace)
        # 把控件都连接上字典
        self.max_level_input.valueChanged.connect(self.on_setting_changed)
        self.min_level_input.valueChanged.connect(self.on_setting_changed)
        self.bind_btn.clicked.connect(self.on_setting_changed)
        self.bind_btn1.clicked.connect(self.on_setting_changed)

            



    
    # 正在选择的卡片，以及实时保存
    def on_recipe_selected(self, index):
        selected_recipe = self.recipe_box.itemText(index)
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
        elif sender_name == "min_level_input":
            self.settings["个人设置"]["最小星级"] = f"{value}"
        elif sender_name == "bind_btn":
            self.settings["个人设置"]["只用绑定卡"] = sender.isChecked()
        elif sender_name == "bind_btn1":
            self.settings["个人设置"]["不绑草替代"] = sender.isChecked()
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
        # 将x和y转化成矩阵
        lParam = win32api.MAKELONG(x, y)
        #发送一次鼠标左键单击
        win32gui.SendMessage(self.handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        win32gui.SendMessage(self.handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam)
    
    # 拖曳,x1y1为需要拖曳的距离
    def drag(self, x, y, x1, y1):
        # 将x和y转化成矩阵，此矩阵表示移动时，鼠标的初始位置
        lParam = win32api.MAKELONG(x, y)
        # 将x+x1和y+y1转化成矩阵，此矩阵表示鼠标要移动到的目标位置
        lParam1 = win32api.MAKELONG(x+x1, y+y1)
        #按下，移动，抬起
        win32gui.SendMessage(self.handle, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        win32gui.SendMessage(self.handle, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lParam1)
        win32gui.SendMessage(self.handle, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam1)


    # 识图函数，分割图片并识别，分成3种分割规则——0:配方分割，1:香料/四叶草分割, 2:卡片分割
    def match_image(self, image, target_image, type):
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
                    if self.settings["个人设置"]["只用绑定卡"] == True:
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
                        cv2.imwrite("temp.png", image)
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
                        cv2.imwrite(f"temp/level{i}-{j}.png", level_img)
                        # 用设置里的卡片上下限来只识别指定星级的卡片
                        for k in range(self.min_level, self.max_level+1):
                            level_image = self.imread(f"items/level/{k}.png")
                            if np.array_equal(level_img, level_image):
                                level = k
                                break
                        if self.min_level == 0 and level == 0:
                            level = 0
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
            return {}  # 返回空字典，如果设置文件不存在
    
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
            QtCore.QThread.msleep(200)
        # 匹配配方，如果还不成功，就再下滑一次
        img = self.get_image(559, 92, 343, 196)
        x, y = self.match_image(img, target_img, 0)
        if x is not None:
            # 匹配成功，点击配方位置
            print("匹配成功")
            # 获取目标配方位置后，点击配方
            self.click(580+(x*49), 110+(y+49))
            return
        # 匹配失败，弹出弹窗
        self.show_dialog("危", "配方识别失败,请检查自己的配方")
        return
        
    # 点击香料/四叶草 type——0:香料,1:四叶草 level——字符串，对不同的type匹配不同的图片
    def get_spice_and_clover(self, type, level):
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
            # 没找到，就点击三下右滑键，再截一次图
            for j in range(3):
                self.click(532, 562)
                QtCore.QThread.msleep(300)
            img = self.get_image(33, 526, 490, 49)
            # 重复前面的读图操作
            x = self.match_image(img, spice_img, 1)
            if x is not None:
                self.click(55 + 49 * x, 550)
                return
        elif type == 1:
            # 查找对应四叶草,level是字符串
            clover_img = self.imread(f"items/clover/{level}四叶草.png")
            # 点击对应四叶草
            x = self.match_image(img, clover_img, 1)
            if x is not None:
                self.click(55 + 49 * x, 550)
                return        
            # 没找到，就点击三下右滑键，再截一次图
            for j in range(3):
                self.click(532, 562)
                QtCore.QThread.msleep(300)
            img = self.get_image(33, 526, 490, 49)
            # 重复前面的读图操作
            x = self.match_image(img, clover_img, 1)
            if x is not None:
                self.click(55 + 49 * x, 550)
                return 
        # 如果还是没有找到，就弹出dialog，提示没有找到目标香料/四叶草
        self.show_dialog("什么！", "没有找到目标香料/四叶草")
        return
    
    # 强化卡片主函数
    def main_enhancer(self):
        # 还没有想好拖曳几次，悲
        # 每次强化，卡片的顺序都会改变，只能强化一次截一次图，直到强卡器返回False，才停止循环
        while self.is_running:
            for i in range(4):
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
                # 没有可以强化的卡了，拖曳截图一次
                # 合成屋卡片拖曳17个像素正好是一格,但是拖曳8次后会有2像素偏移，用新方法就无视偏移啦
                for j in range(6):
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
                    QtCore.QThread.msleep(500)
                # 占位，输出日志或统计信息
    

    # 强化卡片，强化当前页所有符合条件的卡片
    def card_enhancer(self):
        # 获取card字典
        card_dict = self.card_dict
        # 初始化当前页面卡片星级总量字典
        card_level_dict = {}
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
            # 死循环，直到所有卡片都被强化完毕，废案，卡片自己会跑！
            # 用数组来比较，目前是否可以执行这个强化方案
            can_enhance = all(card_level_dict.get(int(subcard), 0) >= subcards.count(subcard) for subcard in subcards)
            if can_enhance: # 如果可以强化，就索引card_dict，寻找目标星级卡片的位置
                for subcard in subcards: # 遍历所有强化需要的卡, 顺序为主卡，副卡1，副卡2，副卡3
                    for position, card_info in card_dict.items():
                        if card_info["level"] == subcard and card_info["bind"] == self.settings["个人设置"]["只用绑定卡"]:
                            x, y = int(position.split("-")[0]), int(position.split("-")[1])
                            # 点击目标卡片，千万记得要加上偏移值
                            self.click(580 + x * 49, 115 + y * 57 + self.offset)
                            # 去除当前卡片的计数，去除字典内存储的对应卡片
                            card_level_dict[subcard] -= 1
                            card_dict.pop(position)
                            QtCore.QThread.msleep(200)
                            break
                # 根据设置，点击四叶草
                if self.settings["强化方案"][f"{j-1}-{j}"].get("四叶草", "无") != "无":
                    self.get_spice_and_clover(1, self.settings["强化方案"][f"{j-1}-{j}"]["四叶草"])
                    QtCore.QThread.msleep(200)
                # 点击强化！强化有延迟，没啥解决方案
                self.click(285, 436)
                QtCore.QThread.msleep(500)
                # 强化之后截图强化区域，判定成功/失败，输出日志
                if self.check_enhance_result(j):
                    # 向日志输出强化信息
                    self.send_log_message(f"{j-1}星上{j}星强化成功")
                else:
                    # 向日志输出强化信息
                    self.send_log_message(f"{j-1}星上{j}星强化失败")
                # 点掉强化区域的卡片，返回，再截图一次
                self.click(287, 343)
                QtCore.QThread.msleep(200)
                # 强化次数+1
                self.enhance_times += 1
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
        # 判定强化结果
        if np.array_equal(level_img, success_img):
            return True
        else:
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

    # 劲 爆 弹 窗
    def show_dialog(self, title, message):
        self.msg = QtWidgets.QMessageBox()
        self.msg.setIcon(QtWidgets.QMessageBox.Warning)
        self.msg.setWindowTitle(title)
        self.msg.setText(message)
        self.msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        # 停止运行
        self.is_running = False
        self.msg.show() # 显示弹窗

    # 输出日志
    def send_log_message(self, message):
        self.output_log.append(f"{message}")

        
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
            # 初始化强卡位置，强卡一遍后再进入循环
            for i in range(5):
                self.enhancer.click(910, 100)
                QtCore.QThread.msleep(300)
            # 强化主函数
            self.enhancer.main_enhancer()
            # 打开运行标志, 点击卡片制作，进入主循环
            self.enhancer.is_running = True
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(300)
        else:
            # 未知位置，弹窗提示
            self.showDialogSignal.emit("哇哦", "未知位置，你好像被卡住了")
            # 停止运行
            self.enhancer.is_running = False
            return
        while self.enhancer.is_running:
            # 如果强化到了一定次数，就退出重进一下合成屋，防止卡顿
            if self.enhancer.enhance_times >= 50:
                # 点击右上角的红叉
                self.enhancer.click(914, 38)
                QtCore.QThread.msleep(1000)
                # 重新点击合成屋
                self.enhancer.click(685, 558)
                # 归零强化次数
                self.enhance_times = 0
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
                # 强化主函数
                self.enhancer.main_enhancer()
            # 数组卡片全部强化完成后，点击卡片制作，再次循环
            self.enhancer.click(108, 258)
            QtCore.QThread.msleep(200)

    def stop(self):
        self.enhancer.is_running = False

    def start_loop(self):
        if self.enhancer.handle is not None:
            self.start()
        else:
            self.showDialogSignal.emit("喂！", "你还没获取句柄呢！")

class enhanceonlyThread(QtCore.QThread):
    showDialogSignal = QtCore.pyqtSignal(str, str)

    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.enhancer = tenchi_cards_enhancer
    
    def run(self):
        # 不作判断，截图一次后强化
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

class DraggableLabel(QtWidgets.QLabel):
    handleChanged = QtCore.pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # 开启鼠标跟踪

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 获取鼠标释放时的全局位置
            cursor_pos = event.globalPos()
            # 获取当前位置的窗口句柄
            handle = win32gui.WindowFromPoint((cursor_pos.x(), cursor_pos.y()))
            self.handleChanged.emit(handle)
    
# 主函数    
def main():
    app = QtWidgets.QApplication(sys.argv)
    enhancer = tenchi_cards_enhancer()
    enhancer.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()