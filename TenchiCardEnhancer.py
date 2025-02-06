# 天知强卡器，以pyqt6为GUI
# setting字典的结构为:setting[type][name][count]
# 统计数据字典的结构为:statistics[type][name][count]
# 更新目标： 完善ui；增加校验，强化方案里有卡包就不进入单卡强卡模式
# -*- coding: utf-8 -*-
import time
from ctypes.wintypes import MSG

from PyQt6 import uic
import win32gui
import win32con
from ctypes import windll, c_void_p
import plyer
import queue
import copy

from PyQt6.QtCore import pyqtSignal, Qt, QElapsedTimer, QTimer, QTime, QThread, pyqtSlot, QEvent, \
    QAbstractNativeEventFilter, QByteArray
from PyQt6.QtGui import QIcon, QPalette, QMovie, QPixmap, QColor, QFontDatabase, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLabel, QApplication, QGraphicsBlurEffect, QWidget

from module.UI.GemUI import GemUI
from module.bg_img_match import match_p_in_w, loop_match_ps_in_w, loop_match_p_in_w
from module.core.CardEnhancer import enhance_log
from module.core.CardProducer import dynamic_card_producer
from module.core.CardTab import exist_empty_block, get_card_names, get_card_list, make_card_count_dict
from module.core.DynamicWait import dynamic_wait_card_slot_state
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match, template_img_match
from module.core.ItemTab import get_target_item
from module.core.LevelCheck import check_card_enhance_result
from module.core.MouseEvent import click, drag
from module.core.PositionCheck import check_position, change_position
from module.gem.GemEnhancer import GemEnhancerThread
from module.globals.DataClass import Card
from module.globals.ResourceInit import resource
from module.globals.EventManager import event_manager
from module.ocr.SuccessRateOcr import get_success_rate
from module.statistic.AsyncStatistic import recorder
from module.test.test_page import TestPage
from module.utils import *
from GUI.editwindow import EditWindow
from GUI.priceeditor import PriceEditor
from GUI.webstatistics import WebStatistics
from module.CardPackEditor import CardPackEditor
from module.EnhanceSimulator import EnhanceSimulator
from module.AutoCushion import AutoCushion
from module.log.TenchiLogger import logger
import module.globals.GLOBALS as GLOBALS


class TenchiCardsEnhancer(QMainWindow):

    # GUI界面初始化
    def __init__(self):
        super(TenchiCardsEnhancer, self).__init__()
        # 创建异常日志处理器
        sys.excepthook = logger.tenchi_exception_handler

        logger.info("少女祈祷中...")
        # 加载UI文件
        ui_path = resource_path('GUI/天知强卡器.ui')
        uic.loadUi(ui_path, self)
        # 移除系统边框和标题栏
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 初始化拖动变量
        self.drag_start_position = None
        self.drag_window_position = None
        # 初始化标题栏
        self.init_title_bar()
        # 设置窗口图标
        self.setWindowIcon(QIcon(resource_path("items/icon/furina.ico")))
        # 设置窗口背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 固定大小
        self.setFixedSize(self.size())
        # 设置窗口背景图
        background_image_path = resource_path('items/icon/furina_background.jpg')

        # 设置样式表
        self.setStyleSheet(f"""
                QMainWindow {{
                    background: rgba(240, 248, 255, 1);
                    border: 1px solid #3A3A3A;
                    border-radius: 12px;
                }}
                /* 工具提示样式 */
                QToolTip {{
                    background-color: rgb(170, 255, 255);
                    color: black;
                    border: 3px dotted rgb(170, 255, 255);
                    border-radius: 4px;
                }}
            """)

        # 背景遮盖层初始化
        self.frosted_layer.lower()  # 将半透明层放到底层
        # 设置模糊效果
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(18)
        self.frosted_layer.setGraphicsEffect(blur)

        # 检测GUI的主题，如果是深色模式，就把蒙版变成黑色
        palette = self.palette()
        if palette.color(QPalette.ColorRole.Window).lightness() < 128:
            self.frosted_layer.setStyleSheet(f"""
                background-color: rgba(0, 0, 0, 180);
                background-image: url("{background_image_path}");
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                """)
        else:
            self.frosted_layer.setStyleSheet(f"""
                background-color: rgba(255, 255, 255, 150);
                background-image: url("{background_image_path}");
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                """)

        # 初始化窗口dpi
        GLOBALS.DPI = get_system_dpi()

        # 变量初始化
        self.version = "0.4.0"
        self.handle = None
        self.handle_browser = None
        self.handle_360 = None
        self.window_name_360 = None
        self.is_running = False
        self.card_list = None
        self.card_count_dict = {}
        self.offset = 0
        self.cards_enough = False
        self.enhance_times = 0
        self.enhance_count = 0
        self.produce_count = 0
        self.card_info_dict = {}
        self.gold_cost_map = {}
        self.enhance_type = '无'
        self.time_last_reload_game = time.time()
        self.single_max_card_position = 0
        self.card_names = set()

        # 初始化强化滚动条的各种参数
        self.single_scroll_time = None
        self.single_line_length = None

        # 弹窗后刷新区
        self.failed_refresh = False
        self.failed_refresh_count = 0

        # 初始化香料列表
        # 从default_constants中获取香料列表
        filename = resource_path('GUI/default/default_constants.json')
        with open(filename, 'r', encoding='utf-8') as f:
            default_constants = json.load(f)
        self.spice_dict = default_constants['默认香料字典']
        self.best_enhance_plan = default_constants['强化最优路径']

        self.settings = load_settings()  # 读取设置作为全局变量
        self.statistics = load_statistics()  # 读取统计数据作为全局变量
        self.pack_names = list(self.settings["卡包配置"].keys())  # 提取所有卡包名
        self.min_level = int(self.settings["个人设置"]["最小星级"])
        self.max_level = int(self.settings["个人设置"]["最大星级"])
        self.reload_count = int(self.settings["个人设置"]["刷新次数"])
        self.is_reload_game = bool(self.settings["个人设置"]["是否刷新游戏"])
        self.reload_time = int(self.settings["个人设置"]["刷新游戏时间"])  # 该变量单位为分钟
        self.is_secondary_password = bool(self.settings["个人设置"]["是否输入二级密码"])
        self.failed_refresh = bool(self.settings["个人设置"]["弹窗后是否刷新游戏"])
        self.secondary_password = self.settings["个人设置"]["二级密码"]
        self.produce_check_interval = int(self.settings["个人设置"]["制卡检测间隔"])
        self.enhance_interval = int(self.settings["个人设置"]["强卡间隔"])
        self.enhance_check_interval = int(self.settings["个人设置"]["强卡检测间隔"])
        self.bag_size = int(self.settings["个人设置"]["背包格数"])

        # 获取卡片属性字典
        with open(resource_path('GUI/card_dict/card_info_dict.json'), 'r', encoding='utf-8') as f:
            self.card_info_dict = json.load(f)

        # 获取金币消耗映射
        with open(resource_path('GUI/card_dict/gold_cost.json'), 'r', encoding='utf-8') as f:
            self.gold_cost_map = json.load(f)

        # 将GUI控件与脚本连接
        # 初始化日志信息
        self.output_log.setOpenExternalLinks(True)
        # 设置日志最大行数
        self.output_log.document().setMaximumBlockCount(2000)
        self.init_log_message()

        # 召唤动态芙芙！
        self.furina_movie = QMovie(resource_path("items/icon/furina_shake.gif"))
        self.furina.setMovie(self.furina_movie)
        self.furina_movie.start()
        self.furina.handleChanged.connect(self.update_handle_display)

        # 初始化芙宁娜助手
        self.init_furina_helper()

        # 配置开始和停止按钮，将开始与停止连接上槽
        self.startbtn.setEnabled(False)  # 没有句柄时，开始与仅强化与宝石分解,宝石强化都不可用
        self.enhanceronlybtn.setEnabled(False)
        self.gem_decompose_btn.setEnabled(False)
        self.gem_enhance_btn.setEnabled(False)
        self.stopbtn.setEnabled(False)  # 初始时停止按钮不可用
        self.startbtn.clicked.connect(self.onStart)
        self.stopbtn.clicked.connect(self.onStop)
        self.enhanceronlybtn.clicked.connect(self.enhanceronly)

        # 连接宝石按钮
        self.gem_decompose_btn.clicked.connect(self.start_gem_decomposition)
        self.gem_enhance_btn.clicked.connect(self.start_gem_enhance)

        # 连上工作线程
        self.EnhancerThread = EnhancerThread(self)
        self.EnhanceOnlyThread = EnhanceOnlyThread(self)
        self.gemEnhancerThread = GemEnhancerThread(self)

        # 连接上工作线程的信号
        event_manager.show_dialog_signal.connect(self.show_dialog)
        event_manager.log_signal.connect(self.send_log_message)

        # 配置，初始化四叶草选择菜单
        self.init_clover()
        # 配置，初始化副卡选择菜单
        self.init_subcard()
        # 初始化香料菜单
        self.init_spice()
        # 初始化个人设置页
        self.init_setting()
        # 初始化状态栏
        self.init_statusbar()

        # 创建生产队列实例
        self.produce_queue = queue.Queue()

        # 创建卡包编辑器实例
        self.card_pack_editor = CardPackEditor(self.settings["卡包配置"])
        # 把卡包编辑器加入到self.tabWidget
        self.tabWidget.insertTab(3, self.card_pack_editor, '卡包配置')
        # 加入提示
        self.tabWidget.setTabToolTip(3,
                                     '在这里编辑你的卡包！默认开包能开出来的卡片都已经设置好啦，卡包被同时视为多张卡片哦')
        # 初始化卡包编辑器选卡菜单
        self.init_recipe_box(self.card_pack_editor.card_select_box)
        # 连接卡包编辑器保存卡包信号
        self.card_pack_editor.save_signal.connect(self.save_card_pack)

        # 创建强化模拟器实例
        self.enhance_simulator = EnhanceSimulator(resource_path('GUI/card_dict/compose.json'), self)
        # 初始化强化模拟器
        self.init_simulator()
        # 初始化物价编辑器
        self.price_editor = None
        # 将物价编辑器连接上按钮
        self.price_editor_btn.clicked.connect(self.show_price_editor)

        # 创建自动垫卡实例
        self.auto_cushion = AutoCushion(self)
        # 初始化自动垫卡
        self.init_cushion()

        # 创建统计数据页实例
        self.web_statistics = WebStatistics(self)

        # 在主窗口中创建一个编辑窗口的属性
        self.edit_window = None
        # 追踪目前窗口的对象名
        self.current_label_object_name = None

        # 创建宝石强化实例
        # self.gem_enhancer = GemEnhancer(self)
        self.gem_ui = GemUI(self)

        # 测试模式
        if TEST_MODE:
            test_page = TestPage(self)
            self.tabWidget.addTab(test_page, "测试")

    # 开始按钮
    def onStart(self):
        # 确保不会重复点击开始
        self.enhanceronlybtn.setEnabled(False)
        self.startbtn.setEnabled(False)
        self.stopbtn.setEnabled(True)
        # 打开运行标识
        self.is_running = True
        GLOBALS.IS_RUNNING = True
        # 正式开始前先防呆
        self.dull_detection()
        # 如果没通过防呆检测，就直接返回
        if not self.is_running:
            return
        # 统计用户目前强化方案与生产方案用卡
        enhance_plan = self.settings["强化方案"]
        produce_plan = self.settings["生产方案"]
        use_cards = ["主卡", "副卡1", "副卡2", "副卡3"]
        enhance_list = []
        for i in range(self.min_level, self.max_level):  # 强化方案
            for card_type in use_cards:
                card = enhance_plan[f"{i}-{i + 1}"][card_type]
                card_name = card["卡片名称"]
                if card["绑定"] == 0:
                    card_bind = "不绑"
                elif card["绑定"] == 1:
                    card_bind = "绑定"
                else:
                    card_bind = "绑定 + 不绑"
                full_name = f"{card_bind}-{card_name} \n"
                if full_name not in enhance_list:
                    enhance_list.append(full_name)
        produce_text = ""
        # 生产方案
        produce_text += f"香料使用情况：\n"
        for spice_name, spice_info in produce_plan.items():
            if not spice_info:
                continue
            produce_text += f"{spice_name}\n"
        produce_text += f'放心，香料要用完了或没了会自动不使用哒'
        # 给出弹窗，提醒用户自己目前强化方案用卡与生产方案用卡。用户点击确定才能开始，否则就停止
        enhance_text = "当前强化用卡：\n" + "\n".join(enhance_list)
        enhance_range_text = f"当前强化范围：{self.min_level}星-{self.max_level}星"
        message = f"{enhance_range_text}\n\n{enhance_text}\n\n{produce_text}\n\n确认开始强化吗？"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('开始前检查！')
        msg_box.setText(message)

        # 自定义按钮
        yes_button = msg_box.addButton('确认开始！', QMessageBox.ButtonRole.AcceptRole)
        no_button = msg_box.addButton('好像不太对', QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            self.EnhancerThread.start_loop()
        else:
            self.onStop()
            return

    # 停止按钮
    def onStop(self):
        # 点击停止后可以重新点击开始
        self.is_running = False
        GLOBALS.IS_RUNNING = False
        self.startbtn.setEnabled(True)
        self.enhanceronlybtn.setEnabled(True)
        self.gem_decompose_btn.setEnabled(True)
        self.gem_enhance_btn.setEnabled(True)
        self.stopbtn.setEnabled(False)
        # 重置弹窗计数
        self.failed_refresh_count = 0

    # 仅强卡按钮
    def enhanceronly(self):
        # 初始化按钮
        self.stopbtn.setEnabled(True)
        self.startbtn.setEnabled(False)
        self.enhanceronlybtn.setEnabled(False)
        # 打开运行标识
        self.is_running = True
        # 正式开始前先防呆
        self.dull_detection("仅强卡")
        # 如果没通过防呆检测，就直接返回
        if not self.is_running:
            return
        self.EnhanceOnlyThread.start_enhance()

    # 芙芙助手，功能强大
    def init_furina_helper(self):
        # 乌瑟勋爵，一键统一所有强化方案用卡
        # 初始化配方选择框
        self.init_recipe_box(self.GentilhommeUsher_box, include_pack=True)
        # 将按钮连接上一键统一功能
        self.GentilhommeUsher_btn.clicked.connect(self.gentilhomme_usher)
        # 海薇玛夫人，一键将副卡星级设置为最优路径
        self.SurintendanteChevalmarin_btn.clicked.connect(self.surintendante_chevalmarin)
        # 蟹贝蕾妲小姐，一键设置所有强化方案用料为绑定/不绑/绑定+不绑
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
                    enhance_plan[f'{i}-{i + 1}']['主卡']['卡片名称'] = card_name
                elif j in [1, 2, 3]:
                    enhance_plan[f'{i}-{i + 1}'][f'副卡{j}']['卡片名称'] = card_name
        self.settings["强化方案"] = enhance_plan
        # 保存强化方案！
        save_settings(self.settings)

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
        save_settings(self.settings)

    # 蟹贝蕾妲小姐！
    def mademoiselle_crabaletta(self):
        # 获取绑定/不绑按钮的选择状态
        bind_state = self.bind_check_box.get_state()
        enhance_plan = self.settings["强化方案"]
        # 迭代所有主副卡，将其绑定设置为选择的状态
        for i in range(16):
            for j in range(5):
                if j == 0:
                    enhance_plan[f'{i}-{i + 1}']['主卡']['绑定'] = bind_state
                elif j in [1, 2, 3]:
                    enhance_plan[f'{i}-{i + 1}'][f'副卡{j}']['绑定'] = bind_state
                elif j == 4:
                    enhance_plan[f'{i}-{i + 1}']['四叶草']['绑定'] = bind_state
        self.settings["强化方案"] = enhance_plan
        # 保存强化方案！
        save_settings(self.settings)

    # 保存并刷新卡包配置
    def save_card_pack(self, card_pack):
        # 保存卡包配置
        self.settings["卡包配置"] = card_pack
        # 保存设置
        save_settings(self.settings)
        # 刷新卡包名
        self.pack_names = list(self.settings["卡包配置"].keys())
        # 刷新卡包配置，乌瑟勋爵和类属性需要在这里刷新
        self.GentilhommeUsher_box.clear()
        self.init_recipe_box(self.GentilhommeUsher_box, include_pack=True)

    # 保存当前设置
    def save_current_settings(self):
        # 调用保存设置函数
        save_settings(self.settings)

    def init_title_bar(self):
        # 设置标题栏图标
        self.title_icon.setScaledContents(True)
        self.title_icon.setPixmap(QPixmap(resource_path("items/icon/furina.ico")))
        self.title_icon.setFixedSize(30, 30)
        # 设置标题栏名称
        self.title_name.setText("天知强卡器！！！！！")
        # 让标题栏名称的字体大一些
        self.title_name.setStyleSheet("""
            QLabel {
                color: black;  /* 文字颜色 */
                font: 20px;
            }
        """)
        # 创建背景层
        self.titleBarBackground = QWidget(self.titleBar)
        self.titleBarBackground.setGeometry(self.titleBar.rect())
        self.titleBarBackground.lower()  # 置于底层

        self.titleBar.setStyleSheet("""
                QWidget #titleBar {
                    background: transparent;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    border: none;
                }
            """)

        # 设置背景层样式
        self.titleBarBackground.setStyleSheet("""
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                background: rgba(240, 248, 255, 1);
            """)

        # 确保背景层不拦截鼠标事件
        self.titleBarBackground.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # 使用FontAwesome图标
        font_id = QFontDatabase.addApplicationFont(resource_path("items/font/fa-solid-900.ttf"))

        if font_id == -1:
            raise Exception("Failed to load Font Awesome font")

        # 获取字体族名称
        fa_families = QFontDatabase.applicationFontFamilies(font_id)

        fa_font = QFont()
        fa_font.setFamily(fa_families[0])

        # 修改按钮文本设置部分
        self.minimizeButton.setFont(fa_font)
        self.minimizeButton.setText("\uf068")  # fa-window-minimize
        self.closeButton.setFont(fa_font)
        self.closeButton.setText("\uf00d")  # fa-times

        # self.minimizeButton.setText("−")  # Unicode减号
        # self.closeButton.setText("✕")  # 使用更粗的乘号（U+2715）

        # 设置按钮样式
        button_style = """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 22px;
                    font-weight: 900;
                    padding: 0;
                    margin: 0;
                    qproperty-alignment: AlignCenter;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.1);
                }
                QPushButton:pressed {
                    background: rgba(0, 0, 0, 0.15);
                }
            """

        # 单独设置关闭按钮颜色
        self.closeButton.setStyleSheet(button_style + """
                QPushButton {
                    color: #666666;
                }
                QPushButton:hover {
                    color: #444444;
                }
            """)

        # 设置最小化按钮颜色
        self.minimizeButton.setStyleSheet(button_style + """
                QPushButton {
                    color: #666666;
                }
                QPushButton:hover {
                    color: #444444;
                }
            """)

        # 设置按钮固定尺寸
        self.minimizeButton.setFixedSize(30, 30)
        self.closeButton.setFixedSize(30, 30)
        # 连接标题栏按钮信号
        self.minimizeButton.clicked.connect(self.window().showMinimized)
        self.closeButton.clicked.connect(self.window().close)

        # 设置标题栏鼠标事件处理
        self.titleBar.mousePressEvent = self._title_bar_mouse_press
        self.titleBar.mouseMoveEvent = self._title_bar_mouse_move
        self.titleBar.mouseReleaseEvent = self._title_bar_mouse_release

    def _title_bar_mouse_press(self, event):
        """处理标题栏鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint()
            self.drag_window_position = self.pos()

    def _title_bar_mouse_move(self, event):
        """处理标题栏鼠标移动事件"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.drag_start_position:
                delta = event.globalPosition().toPoint() - self.drag_start_position
                self.move(self.drag_window_position + delta)

    def _title_bar_mouse_release(self, event):
        """处理标题栏鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = None
            self.drag_window_position = None

    # 初始化日志信息
    def init_log_message(self):
        self.send_log_message(f"当当！天知强卡器启动成功！目前版本号为{self.version} 测试版")
        self.send_log_message(f"该版本为测试版，功能还不完善，遇到不稳定的情况，请反馈给我！")
        self.send_log_message("使用前请关闭二级密码，遇到问题请查看网站里的教程！！（目前还不存在的链接）")
        self.send_log_message("目前仅支持360游戏大厅,但支持任何系统缩放，所以说我是高性能的呦")
        self.send_log_message(
            "最新版本 [github] <a href=https://github.com/a1929238/tenchi-cards-enhancer>https://github.com/a1929238"
            "/tenchi-cards-enhancer</a>")
        self.send_log_message("[QQ群 交流·反馈·催更] 1群：786921130 2群：142272678")
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
        self.edit_window.setWindowIcon(QIcon(resource_path("items/icon/hutao.ico")))
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
            self.init_recipe_box(recipe_box, include_pack=True)
            # 将配方选择框更改的信号连接上字典的编辑和保存
            recipe_box.currentIndexChanged.connect(self.on_recipe_box_changed)

        # 根据设置文件，初始化选择框的索引，并在星级不存在时，隐藏对应的配方选择框
        for i in range(4):
            recipe_box = getattr(self.edit_window, f'card_box{i}')
            if i == 0:
                card_name = self.settings["强化方案"][self.enhance_type]["主卡"].get("卡片名称", "无")
            else:
                # 只会隐藏部分副卡的选择框
                card_name = self.settings["强化方案"][self.enhance_type][f"副卡{i}"].get("卡片名称", "无")
                card_level = self.settings["强化方案"][self.enhance_type][f"副卡{i}"].get("星级", "无")
                if card_level == "无":
                    # 不用这张副卡，就隐藏这张副卡相关的所有控件
                    hide_row_widgets(self.edit_window.gridLayout, i)
            index = 0
            for index in range(recipe_box.count()):
                if recipe_box.itemText(index).split("-")[0] == card_name:
                    break
            recipe_box.setCurrentIndex(index)

        # 初始化绑定按钮，绑定按钮有五个,0是主卡，1-3是副卡，4是四叶草
        for i in range(5):
            bind_btn = getattr(self.edit_window, f'bind_btn{i}')
            self.init_bind_btn(bind_btn, i)

    # 初始化编辑窗口的绑定编辑
    def init_bind_btn(self, check_box, index):
        # 根据设置，初始化勾选框当前选项
        if index == 0:
            # 主卡绑定
            bind_flag = self.settings["强化方案"][self.enhance_type]["主卡"].get("绑定", 0)
        elif index in [1, 2, 3]:
            # 副卡绑定
            bind_flag = self.settings["强化方案"][self.enhance_type][f"副卡{index}"].get("绑定", 0)
        elif index == 4:
            # 四叶草绑定
            bind_flag = self.settings["强化方案"][self.enhance_type]["四叶草"].get("绑定", 0)
        else:
            return
        # 设置是否被勾选
        check_box.set_state(bind_flag)
        # 将绑定勾选框点击的信号连接上字典的编辑和保存
        check_box.stateChanged.connect(self.on_bind_btn_clicked)

    # 初始化选卡菜单
    def init_recipe_box(self, comboBox, include_pack=False, filter_word=None, need_suffix=True):
        recipe_dir = resource_path("items/recipe")
        # 在开头加入卡包名
        if include_pack:
            for pack_name in self.pack_names:
                comboBox.addItem(pack_name)
        if os.path.exists(recipe_dir):
            # 获取卡片名列表
            filenames = os.listdir(recipe_dir)
            # 根据评级对文件名进行排序
            sorted_filenames = sorted(filenames, key=self.sort_key)
            for filename in sorted_filenames:
                # 获取卡片名
                recipe_name = filename.replace("配方.png", "")
                recipe_quality = self.card_info_dict.get(recipe_name, '未知')
                # 如果有筛选词，则只显示包含筛选词的卡片
                if filter_word and filter_word != recipe_quality:
                    continue
                card_text = recipe_name
                # 如果需要后缀，则在卡片名后面加上卡片的属性
                if need_suffix:
                    card_text += f"-{recipe_quality}"
                comboBox.addItem(card_text)

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
                subcard_box_name = f"subcard{i + 1}_{j}"
                subcard_box = getattr(self, subcard_box_name)
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
                selected_subcard = self.settings.get("强化方案", {}).get(f"{j}-{j + 1}", {}).get(f"副卡{i + 1}",
                                                                                                 "无").get("星级", "无")
                # 在 QComboBox 中查找这个卡片名称对应的索引
                index = subcard_box.findText(selected_subcard)
                if index >= 0:
                    # 如果找到了，设置 QComboBox 当前选中的索引
                    subcard_box.setCurrentIndex(index)
                # 允许信号发射
                subcard_box.blockSignals(False)
                # 尝试断开旧的信号
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
            selected_clover = self.settings.get("强化方案", {}).get(f"{i}-{i + 1}", {}).get("四叶草", "无").get("种类",
                                                                                                                "无")
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

    def init_spice(self):
        """根据设置，初始化控件的选择情况，并绑定信号"""
        # 初始化香料菜单
        production_plan = self.settings["生产方案"]
        # 将字典的键（香料名）提取到一个列表中
        spices = list(production_plan.keys())
        for i in range(len(spices)):
            spice_name = spices[i]
            # 获取对应的香料控件
            spice_use_name = f"spice_use{i}"
            spice_use_check = getattr(self, spice_use_name)
            # 设置是否使用该香料
            spice_use_check.setChecked(production_plan[spice_name])
            # 每次更改是否使用时，都要保存字典
            spice_use_check.stateChanged.connect(self.on_spice_use_changed)

    # 初始化个人设置菜单
    def init_setting(self):
        # 从个人设置字典中读取数据，初始化控件
        self.max_level_input.setValue(self.max_level)
        self.min_level_input.setValue(self.min_level)
        self.reload_count_input.setValue(self.reload_count)

        self.is_reload_game_input.setChecked(self.is_reload_game)
        self.reload_time_input.setValue(self.reload_time)
        self.is_secondary_password_input.setChecked(self.is_secondary_password)
        self.secondary_password_input.setText(self.secondary_password)
        self.failed_refresh_check.setChecked(self.failed_refresh)


        self.produce_check_interval_input.setValue(self.produce_check_interval)
        self.enhance_interval_input.setValue(self.enhance_interval)
        self.enhance_check_interval_input.setValue(self.enhance_check_interval)
        self.bag_size_input.setValue(self.bag_size)

        # 把控件都连接上字典
        self.max_level_input.valueChanged.connect(self.on_setting_changed)
        self.min_level_input.valueChanged.connect(self.on_setting_changed)
        self.reload_count_input.valueChanged.connect(self.on_setting_changed)

        self.is_reload_game_input.stateChanged.connect(self.on_setting_changed)
        self.reload_time_input.valueChanged.connect(self.on_setting_changed)
        self.is_secondary_password_input.stateChanged.connect(self.on_setting_changed)
        self.secondary_password_input.textChanged.connect(self.on_setting_changed)
        self.failed_refresh_check.stateChanged.connect(self.on_setting_changed)

        self.produce_check_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_interval_input.valueChanged.connect(self.on_setting_changed)
        self.enhance_check_interval_input.valueChanged.connect(self.on_setting_changed)
        self.bag_size_input.valueChanged.connect(self.on_setting_changed)

    # 初始化状态栏
    def init_statusbar(self):
        # 设置颜色蒙版
        self.statusBar.setStyleSheet(f"""
                /* 状态栏样式 */
                QStatusBar {{
                    background: transparent;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                    padding: 4px;
                    background-color: rgba(240, 248, 255, 0.8);
                }}
                """)
        # 获取打开程序的时间
        self.start_time = QElapsedTimer()
        self.start_time.start()  # 开始计时

        # 创建一个控件让当前时间标签往右偏移一些
        self.offset_label = QLabel()
        self.statusBar.addWidget(self.offset_label)
        self.offset_label.setFixedWidth(10)

        # 创建并添加当前时间标签
        self.current_time_label = QLabel()
        self.statusBar.addWidget(self.current_time_label)
        self.current_time_label.setFixedWidth(115)

        # 创建并添加程序运行时间标签
        self.run_time_label = QLabel()
        self.statusBar.addWidget(self.run_time_label)
        self.run_time_label.setFixedWidth(115)

        # 创建并添加强化次数标签
        self.enhance_count_label = QLabel()
        self.statusBar.addWidget(self.enhance_count_label)

        # 创建并添加版本号标签
        self.version_label = QLabel(f'版本号:{self.version}')
        self.statusBar.addPermanentWidget(self.version_label)
        # 让样式表偏移一些
        self.version_label.setStyleSheet("QLabel { margin-right: 5px; }")

        # 设置定时器更新当前时间和程序运行时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status_bar)
        self.timer.start(1000)  # 每秒更新一次

        self.update_status_bar()  # 初始化状态栏显示

    def update_status_bar(self):
        # 更新当前时间
        current_time = QTime.currentTime().toString()
        self.current_time_label.setText(f'当前时间: {current_time}')

        # 更新程序运行时间
        elapsed_time = self.start_time.elapsed()
        hours, remainder = divmod(elapsed_time, 3600000)
        minutes, seconds = divmod(remainder, 60000)
        run_time = f'{hours:02d}:{minutes:02d}:{seconds // 1000:02d}'
        self.run_time_label.setText(f'运行时间: {run_time}')

        # 更新运行期间强化次数
        self.enhance_count_label.setText(f'本次运行期间共强化: {self.enhance_count}次')

    # 初始化强化模拟器
    def init_simulator(self):
        # 绑定添加主卡/副卡按钮
        self.add_main_card_btn.clicked.connect(self.add_virtual_card)
        self.add_sub_card_btn_1.clicked.connect(self.add_virtual_card)
        self.add_sub_card_btn_2.clicked.connect(self.add_virtual_card)
        self.add_sub_card_btn_3.clicked.connect(self.add_virtual_card)
        # 绑定四叶草按钮
        self.clover_select_box.currentIndexChanged.connect(self.enhance_simulator.clover_changed)
        # 绑定强化按钮
        self.enhance_btn.clicked.connect(self.enhance_simulator.cyber_enhance)
        # 绑定获得方案期望按钮
        self.get_expectation_btn.clicked.connect(self.enhance_simulator.get_enhancement_expectation)
        # 初始化选择框数值
        self.guild_compose_level_input.setValue(self.settings["强化模拟器"]["公会合成屋等级"])
        self.VIP_level_input.setValue(self.settings["强化模拟器"]["VIP等级"])
        # 绑定VIP等级和合成屋等级选择框，将它们的数据修改后保存
        self.guild_compose_level_input.valueChanged.connect(self.save_bonus_rate)
        self.VIP_level_input.valueChanged.connect(self.save_bonus_rate)

    # 等级保存和强化成功率修改
    def save_bonus_rate(self):
        sender = self.sender()
        sender_name = sender.objectName()
        if sender_name == "guild_compose_level_input":
            self.settings["强化模拟器"]["公会合成屋等级"] = sender.value()
        elif sender_name == "VIP_level_input":
            self.settings["强化模拟器"]["VIP等级"] = sender.value()
        # 保存设置
        save_settings(self.settings)
        # 刷新显示
        self.enhance_simulator.get_bonus()

    # 强化模拟器卡片添加
    def add_virtual_card(self):
        # 获取对象名
        sender = self.sender()
        # 分离出对象数字
        oid = sender.objectName().split('_')[1]
        # 创建质量映射
        quality_map = {
            "好卡": "2",
            "中卡": "0",
            "差卡": "1",
        }
        if oid == "main":
            # 主卡
            level = self.main_card_level_box.currentText()
            quality = self.main_card_quality_box.currentText()
            self.enhance_simulator.simulator_cards["0"] = {
                "星级": level,
                "质量": quality_map[quality],
            }
        elif oid == "sub":
            oid = sender.objectName().split('_')[4]
            sub_card_level_box = getattr(self, f"sub_card_level_box_{oid}")
            sub_card_quality_box = getattr(self, f"sub_card_quality_box_{oid}")
            level = sub_card_level_box.currentText()
            quality = sub_card_quality_box.currentText()
            if not level or not quality:
                return
            self.enhance_simulator.simulator_cards[oid] = {
                "星级": level,
                "质量": quality_map[quality],
            }
        # 刷新强化模拟器UI
        self.enhance_simulator.refresh_ui()

    # 打开物价编辑器
    def show_price_editor(self):
        # 创建物价编辑器实例
        price_editor = PriceEditor(self.settings["物价"])
        if price_editor.exec():  # 如果用户点击了保存
            data = price_editor.get_data()
            self.settings["物价"] = data  # 保存到设置中
            save_settings(self.settings)

    # 初始化自动垫卡
    def init_cushion(self):
        # 将按钮连接上添加规律
        self.add_rule_btn.clicked.connect(self.auto_cushion.add_rules)
        # 连接上删除规律
        self.delete_rule_btn.clicked.connect(self.auto_cushion.delete_rule)
        # 连接上开始寻找方案
        self.find_combination_btn.clicked.connect(self.auto_cushion.find_combination)
        # 连接上开始垫卡
        self.start_cushion_btn.clicked.connect(self.auto_cushion.auto_cushion)
        # 连接清空现有规律结果按钮
        self.clear_cushion_btn.clicked.connect(self.auto_cushion.clear_result)

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
        save_settings(self.settings)

    # 实时保存编辑窗口的绑定编辑
    def on_bind_btn_clicked(self, state):
        sender = self.sender()
        # 获取绑定按钮的对象名,0是主卡,1-3是副卡,4是四叶草
        index = int((sender.objectName()).replace('bind_btn', ''))
        # 保存到字典
        if index == 0:
            self.settings["强化方案"][self.enhance_type]['主卡']['绑定'] = state
        elif index in [1, 2, 3]:
            self.settings["强化方案"][self.enhance_type][f'副卡{index}']['绑定'] = state
        elif index == 4:
            self.settings["强化方案"][self.enhance_type]['四叶草']['绑定'] = state
        # 保存设置
        save_settings(self.settings)

    def on_spice_use_changed(self, state):
        """动态保存是否使用该香料"""
        sender = self.sender()
        spice_level = int(sender.objectName().replace('spice_use', ''))
        # 更新字典中的香料使用配置
        production_plan = self.settings["生产方案"]
        spice_name = list(production_plan)[spice_level]
        production_plan[spice_name] = bool(state)
        self.settings["生产方案"] = production_plan
        save_settings(self.settings)

    # 实时保存四叶草配置
    def on_clover_selected(self, index):
        # 从信号发出名分离出数字
        sender = self.sender()
        clover_level = int(sender.objectName().replace('clover', ''))
        selected_clover = sender.itemText(index)
        # 更新字典中的四叶草配置
        scheme_key = f"{clover_level}-{clover_level + 1}"
        if scheme_key not in self.settings["强化方案"]:
            self.settings["强化方案"][scheme_key] = {}
        self.settings["强化方案"][scheme_key]["四叶草"]["种类"] = selected_clover
        # 保存设置
        save_settings(self.settings)

    # 实时保存副卡配置
    def on_subcard_selected(self, index):
        # 从信号发出名分离出数字
        sender = self.sender()
        subcard_type, subcard_level = sender.objectName().split("_")[0].replace('subcard', ''), int(
            sender.objectName().split("_")[1])
        selected_subcard_level = sender.itemText(index)
        # 更新字典中的副卡配置
        scheme_key = f"{subcard_level}-{subcard_level + 1}"
        self.settings["强化方案"][scheme_key][f"副卡{subcard_type}"]['星级'] = selected_subcard_level
        # 保存设置
        save_settings(self.settings)

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
        elif sender_name == "is_reload_game_input":
            self.settings["个人设置"]["是否刷新游戏"] = sender.isChecked()
            self.is_reload_game = sender.isChecked()
        elif sender_name == "reload_time_input":
            self.settings["个人设置"]["刷新游戏时间"] = f"{value}"
            self.reload_time = value
        elif sender_name == "failed_refresh_check":
            self.settings["个人设置"]["弹窗后是否刷新游戏"] = sender.isChecked()
            self.failed_refresh = sender.isChecked()
        elif sender_name == "is_secondary_password_input":
            self.settings["个人设置"]["是否输入二级密码"] = sender.isChecked()
            self.is_secondary_password = sender.isChecked()
        elif sender_name == "secondary_password_input":
            self.settings["个人设置"]["二级密码"] = value
            self.secondary_password = value
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
        elif sender_name == "bag_size_input":
            self.settings["个人设置"]["背包格数"] = f"{value}"
            self.bag_size = value
        # 保存设置
        save_settings(self.settings)

    def handle_check(self, handle):
        """
        根据窗口类名，窗口大小，校验该窗口是否为flash游戏窗口
        """
        # 窗口名
        window_name = win32gui.GetWindowText(handle)
        # 窗口类名
        window_class_name = win32gui.GetClassName(handle)
        # 窗口大小
        window_rect = win32gui.GetWindowRect(handle)
        left, top, right, bottom = window_rect
        width = right - left
        height = bottom - top

        scale = GLOBALS.DPI / 96
        # 计算期望的窗口尺寸
        expected_width = int(950 * scale)
        expected_height = int(596 * scale)

        logger.info(handle, window_name, window_class_name, width, height)

        # 允许1个像素内的误差
        if abs(width - expected_width) <= 1 and abs(height - expected_height) <= 1:
            return True

    # 更新显示窗口句柄和窗口名的标签
    def update_handle_display(self, handle):
        """
        360窗口结构
        Type:DUIWindow Name: channel-name # 360层级
            |- Type: TabContentWnd
                |- Type: CefBrowserWindow
                    |- Type: Chrome_WidgetWin_0 # 窗口浏览器层级
                        |- Type: WrapperNativeWindowClass
                            |- Type: NativeWindowClass # Flash游戏层级 需要玩家指定
        """
        # 句柄校验
        if not self.handle_check(handle):
            event_manager.show_dialog_signal.emit("这不是游戏窗口！",
                                                  "哼，给我拖到游戏里去啊！\n （悄悄告诉你呦，目前我只支持360游戏大厅）")
            return
        self.handle = handle
        GLOBALS.HWND = handle
        if self.handle is not None:
            window_text = win32gui.GetWindowText(self.handle)
            self.handle_label.setText(f"窗口句柄: {self.handle}")
            self.window_label.setText(f"窗口名: {window_text}")
            # 允许点击开始与仅强化与宝石分解强化与垫卡按钮
            self.startbtn.setEnabled(True)
            self.enhanceronlybtn.setEnabled(True)
            self.gem_decompose_btn.setEnabled(True)
            self.gem_enhance_btn.setEnabled(True)
            self.start_cushion_btn.setEnabled(True)
            # 句柄改变时，重置单卡位置
            self.single_max_card_position = 0
            if win32gui.GetClassName(handle) == "NativeWindowClass":
                logger.info("360游戏大厅模式, 允许刷新, 可用 window_name_360 是否 None 判断")
                # 获取上级句柄
                for i in range(2):
                    handle = win32gui.GetParent(handle)
                self.handle_browser = handle
                for i in range(3):
                    handle = win32gui.GetParent(handle)
                self.handle_360 = handle
                self.window_name_360 = win32gui.GetWindowText(self.handle_360)
                # 获取供刷新用的网页句柄
                self.handle_web = self.find_sibling_window_by_class(win32gui.GetParent(self.handle),
                                                                    "Chrome_RenderWidgetHostHWND")
                logger.info(self.handle_web)

            else:
                self.window_name_360 = None
            logger.info(self.window_name_360)

    """
    窗口结构
    Type:DUIWindow Name: channel-name # 360层级
        |- Type: TabContentWnd
            |- Type: CefBrowserWindow
                |- Type: Chrome_WidgetWin_0 # 窗口浏览器层级
                    |- Type: WrapperNativeWindowClass
                        |- Type: NativeWindowClass # Flash游戏层级
    """

    def find_sibling_window_by_class(self, hwnd, sibling_class_name):
        parent = win32gui.GetParent(hwnd)
        if not parent:
            return None

        hwnd_sibling = None

        def enum_sibling_windows(hwnd, param):
            nonlocal hwnd_sibling
            if win32gui.GetClassName(hwnd) == sibling_class_name:
                hwnd_sibling = hwnd
                return False  # 停止枚举
            return True  # 继续枚举

        win32gui.EnumChildWindows(parent, enum_sibling_windows, None)
        return hwnd_sibling

    def get_handle_cus(self, mode="flash"):
        """
        解析频道名称 获取句柄, 仅支持360游戏大厅,
        :param mode: "360" -> "browser" -> "flash"
        :return: handel
        """
        handle = win32gui.FindWindow("DUIWindow", self.window_name_360)  # 360窗口 该层级有刷新框
        if mode in ["browser", "flash"]:
            handle = win32gui.FindWindowEx(handle, None, "TabContentWnd", "")
            handle = win32gui.FindWindowEx(handle, None, "CefBrowserWindow", "")
            handle = win32gui.FindWindowEx(handle, None, "Chrome_WidgetWin_0", "")  # 该层级 有 服务器序号输入框
        if mode == "flash":
            handle = win32gui.FindWindowEx(handle, None, "WrapperNativeWindowClass", "")
            handle = win32gui.FindWindowEx(handle, None, "NativeWindowClass", "")  # game窗口

        return handle

    # 字典编辑方法，传入字典，键，值，返回修改后的字典
    def update_dict(self, my_dict, key, value):
        # 哦哦哦，把key转化为str
        key = str(key)
        # 修改或初始化字典对应键和值
        my_dict[key] = int(my_dict.get(key, 0)) + int(value)
        return my_dict

    # 点击配方
    # 预计更新方法，模板匹配第一处卡片上框架的位置，然后裁剪图片，再进行识别，失败，因为最上方框架与下方的所有卡片都不同。
    # 尝试直接使用模板匹配，非常好使。
    def get_recipe(self, target_img):
        # 截图四次，每次拖曳三格(第一次为点击滑块最上方)
        for i in range(5):
            # 等待150毫秒
            QThread.msleep(150)
            # 截图
            img = get_image(559, 90, 343, 196)
            # 直接模板匹配图像
            result = cv2.matchTemplate(img, target_img, cv2.TM_CCOEFF_NORMED)
            min_value, max_value, min_loc, max_loc = cv2.minMaxLoc(result)
            if max_value >= 0.99:
                # 匹配成功，点击配方位置
                x, y = max_loc
                # 计算模板图像的中心偏上位置
                center_x = x + target_img.shape[1] // 2
                center_y = y + 5

                # 然后点击中心偏上位置
                click(580 + center_x, 110 + center_y)
                return
            # 匹配失败，鼠标滑动15个像素，再次截图，如果是第一次尝试，就只点击滑块最上方
            if i == 0:
                click(910, 110)
            else:
                drag(910, 95 + i * 15, 0, 15)
            QThread.msleep(200)
        # 匹配失败，弹出弹窗
        event_manager.show_dialog_signal.emit("危", "配方识别失败,请检查自己的配方")
        return

    def check_spice_slot(self, slot_img, target_img):
        """
        用模板匹配判断香料是否被正确放置
        """
        result = cv2.matchTemplate(slot_img, target_img, cv2.TM_CCOEFF_NORMED)
        min_value, max_value, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_value >= 0.98:
            return True
        else:
            return False

    def get_scroller_parameter(self):
        """
        根据背包大小，计算出滚动条的各种参数
        滚动条长度 = −1.772 × 物品行数 + 160.082
        """
        bag_lines = (self.bag_size // 7) + 1
        scroller_length = (-1.772 * bag_lines) + 160.082
        draggable_length = 420 - scroller_length
        self.single_line_length = int(draggable_length // bag_lines)  # 确保拖动距离小于准确的一行
        self.single_scroll_time = int(((draggable_length / bag_lines) / self.single_line_length) * bag_lines) + 1

    # 强化卡片主函数
    def main_enhancer(self):
        if not self.is_running:
            return
        # 初始化当前位置
        current_position = 0
        # 最终最终方案，根据用户背包大小计算卡片行数，然后算出滚动条总长，以此完全确定拖动距离
        self.get_scroller_parameter()
        # 确认当前强化方案中卡片数量
        card_num = len(self.card_names)
        # 单卡强卡特殊方案，寻找比强化最高星级低一级的卡片位置
        if card_num == 1 and self.single_max_card_position == 0:
            self.find_max_card_position()
        # 每次强化，卡片的顺序都会改变，只能强化一次截一次图，直到强卡器返回False，才停止循环
        while self.is_running:
            # 每次强化之后合成屋栏位都会动，所以在截图前要先等待200毫秒
            QThread.msleep(200)
            # 初始化偏移值,切割传入图像
            self.offset = 0
            # 截图并切割图片，方法更新，用模板匹配图片中的第一行，然后把色块以上的图片全部切掉，再识别。这样无论滑块在哪里，都能确保找到七行卡片
            img = self.get_cut_cards_img(need_offset=True)
            # 尝试获取强化卡片字典
            card_list = get_card_list(img, self.card_names, rows=7, columns=7, min_level=self.min_level,
                                      max_level=self.max_level)
            if card_list:
                # 如果是单卡强卡且最高等级小于10，则检测一遍最上面一排，第七张卡(0-6)是否等于等级上限，如果等于，就往下拉一行
                if card_num == 1 and self.max_level < 10:
                    self.check_first_row_card(card_list)
                self.card_list = card_list
                # 强化当前页面卡片，传输进去的是拷贝后的卡片列表，可在强化函数中修改
                self.enhance_card_once(card_list=card_list.copy(), enhance_plan=self.settings["强化方案"])
                # 检查停止标识
                if not self.is_running:
                    break
                if self.cards_enough:
                    # 强化后打破拖曳，在循环一次
                    continue
            # 如果卡片数量大于1，则启用第一种拖曳方式
            if card_num > 1:
                # 如果在非第一次拖曳中，同时识别出了空格，表明再往下拉也没卡了，那么就退出循环
                if current_position != 0 and exist_empty_block(img):
                    break
                # 拖曳长度取决于拖曳次数，每次拖曳长度为420/滚动次数，当前位置为0时，点击一次滑块最顶端
                if current_position == 0:
                    current_position += 5
                    click(908, 120)
                else:
                    drag(908, 120 + current_position, 0, self.single_line_length * 7)
                    current_position += self.single_line_length * 7
                QThread.msleep(100)
                # 当前位置超过370，退出循环
                if current_position >= 370:
                    break
            else:
                # 单卡拖曳方式，固定在等级最高卡片位置
                click(908, 120 + self.single_max_card_position)
                break

    # 寻找等级最高卡片位置
    def find_max_card_position(self):
        # 初始化目标等级
        target_level = min(self.max_level - 1, 9)
        current_max_level = 0
        full_card_set = set()
        # 分用户设置次数获取卡片字典，获得目前最高卡片等级
        scroll_length = self.single_line_length * 7
        # 点击一下滑块的最上方
        click(908, 120)
        for i in range((420 // scroll_length) + 1):
            QThread.msleep(150)
            img = self.get_cut_cards_img()
            card_list = get_card_list(img, self.card_names)
            full_card_set.update(card_list)
            drag(908, 120 + i * scroll_length, 0, scroll_length)
        if not full_card_set:
            return
        for card in full_card_set:
            if card.level <= target_level:
                current_max_level = max(current_max_level, card.level)
        # 点击一下滑块的最上方
        click(908, 120)
        # 寻找到目标等级后，从开始慢慢拖曳滑块，直到等级最高的卡片出现在第一行
        for i in range(self.single_scroll_time):
            if not self.is_running:
                return
            QThread.msleep(150)
            img = self.get_cut_cards_img(rows=1)
            card_list = get_card_list(img, self.card_names, rows=1, min_level=self.min_level,
                                      max_level=self.max_level)
            # 如果列表里存在目标等级的卡，就停止拖曳，并修改位置设置
            for card in card_list:
                if card.level == current_max_level:
                    self.single_max_card_position = i * self.single_line_length
                    return
            drag(908, 120 + i * self.single_line_length, 0, self.single_line_length)

    def check_first_row_card(self, card_list):
        """检测第一行最后的卡片是否为最高等级，是的话就往下拉一行"""
        for card in card_list:
            if card.position == (0, 6) and card.level == self.max_level:
                break
        else:
            return True, card_list
        # 往下拉一行
        while True:
            drag(908, 120 + self.single_max_card_position, 0, self.single_line_length)
            self.single_max_card_position += self.single_line_length
            QThread.msleep(200)
            img = self.get_cut_cards_img(need_offset=True)
            card_list = get_card_list(img, self.card_names, rows=7, columns=7, min_level=self.min_level,
                                      max_level=self.max_level)
            for card in card_list:
                if card.position == (0, 6) and card.level == self.max_level:
                    # 还在，就再拉一次
                    break
            else:
                # 使用本次获得的卡片列表
                return True, card_list

    # 获取裁剪过的合成屋卡片图像
    def get_cut_cards_img(self, rows=7, need_offset=False):
        height = 57 * rows
        img = get_image(559, 91, 343, 456)
        line_img = resource.line_img
        # 进行模板匹配
        result = cv2.matchTemplate(img, line_img, cv2.TM_CCOEFF_NORMED)
        # 遍历匹配结果
        for y in range(result.shape[0]):
            if result[y, 0] >= 0.25:
                # 裁剪图像，保留标记位置以下的七格像素
                img = img[y + 1:400 + y]
                # 剪裁出符合行数的图像
                img = img[:height]
                if need_offset:
                    self.offset = y
                break
        return img

    # 强化卡片，由高到低，强化当前页所有符合条件的卡片
    def enhance_card_once(self, card_list, enhance_plan):
        """
        强化方案中，卡片信息统一为字典，字典内包含以下内容：
        星级：星级
        卡片名称：卡片名称
        绑定：是否绑定
        """
        # 按照最高强化卡片，从高到低，遍历设置里的强化方案，获取所需副卡，如果卡片总量大于等于方案所需卡片，就遍历card字典的位置，点击卡片，强化一次
        for enhance_level in range(self.max_level, self.min_level, -1):
            # 获取当前星级强化方案
            current_enhance_plan = enhance_plan[f"{enhance_level - 1}-{enhance_level}"]
            # 初始化需求卡片列表
            need_card_list = []
            # 获取主卡对象
            main_card = Card()
            main_card_info = current_enhance_plan["主卡"].copy()
            # 给主卡信息加上星级
            main_card_info['星级'] = f'{enhance_level - 1}'
            main_card.load_from_dict(main_card_info)
            need_card_list.append(main_card)
            # 获取副卡信息
            for i in range(1, 4):
                sub_card_info = current_enhance_plan[f"副卡{i}"].copy()
                # 如果副卡存在星级，则将其添加到数组内
                if sub_card_info.get("星级", "无") != "无":
                    sub_card = Card()
                    sub_card.load_from_dict(sub_card_info)
                    need_card_list.append(sub_card)
            # 解耦合，检查是否可以强化
            can_enhance, used_card_list = self.can_enhance(card_list, need_card_list)
            if can_enhance:  # 如果可以强化，就点击所有传过来的位置
                # 初始化检查用的槽位
                check_slot = len(used_card_list)
                # 先点击主卡槽，确保上一张卡不会留存
                click(284, 347)
                for card in used_card_list:
                    y, x = card.position
                    # 点击目标卡片，千万记得要加上偏移值
                    click(580 + x * 49, 115 + y * 57 + self.offset)
                # 根据设置，获取四叶草
                clover_name = current_enhance_plan["四叶草"]['种类']
                clover_bind_need = current_enhance_plan["四叶草"]['绑定']
                # 初始化获取到的四叶草绑定状态
                clover_bind = 0
                if current_enhance_plan["四叶草"]['种类'] != "无":
                    # 尝试获取四叶草，以及获取到的四叶草的绑定状态
                    find, clover_bind = get_target_item(resource.clover_images[clover_name], clover_bind_need)
                    # 如果没找到四叶草，弹窗并返回
                    if not find:
                        bind_status_map = {0: "不绑", 1: "绑定", 2: "绑定或不绑"}
                        event_manager.show_dialog_signal.emit(
                            "强化停下了！",
                            f"没有找到{bind_status_map[clover_bind_need]}{clover_name}四叶草，请检查一下！"
                        )
                        return
                    else:
                        # 检查槽位设置为5，即检查四叶草槽位
                        check_slot = 5
                # 按照强化用的卡片数量，循环等待卡片是否均被成功点上
                if not dynamic_wait_card_slot_state(check_slot, True, interval=self.enhance_check_interval):
                    text = ""
                    for card in used_card_list:
                        text += f'[{card.get_text()}]'
                    event_manager.show_dialog_signal.emit(
                        "卡片点不上去！",
                        f"{text}未被成功点击，是点到永久卡了吗？"
                    )
                    return
                # 初始等待时间，等待所有道具被完全放上卡槽，这个等待可以通过给游戏加速来规避，调低会导致强化没有进行就开始下一次强化
                QThread.msleep(self.enhance_interval)
                # 记录本次强化的成功率与成功率加成
                original_success_rate, extra_success_rate = get_success_rate()
                # 点击强化！点好卡后到可以强化有延迟，故该点击常常无效
                click(285, 436)
                # 主卡为不绑时，使用绑定材料强卡会导致弹窗，此为弹窗检测和点击
                if not used_card_list[0].bind:
                    for index in range(1, len(used_card_list)):
                        if used_card_list[index].bind or clover_bind:
                            # 检测绑定弹窗，并点掉
                            self.click_warning_dialog()
                            break
                # 等待强化结束后卡槽空出
                if not dynamic_wait_card_slot_state(2, False, interval=self.enhance_check_interval):
                    self.is_running = False
                    # 强化失败，弹窗
                    event_manager.show_dialog_signal.emit("哎呦", "强化检测超过80轮，看看发生什么了吧")
                    return
                # for i in range(80):
                #     # 获得副卡槽图片
                #     sub_card_image = get_image(267, 253, 40, 50)
                #     # 判定副卡槽图片是否和副卡空卡槽图片一样
                #     if direct_img_match(sub_card_image, resource.sub_card_icon):
                #         break  # 卡槽空了就点掉主卡，进行下一次强化
                #     # 没空，就重复点击强化
                #     click(285, 436)
                #     # 检测等待时间
                #     QThread.msleep(self.enhance_check_interval)
                # else:
                #     return
                # 检查运行标识
                if not self.is_running:
                    return
                # 强化之后截图强化区域，判定成功/失败，输出日志
                success = check_card_enhance_result(used_card_list[0].level)
                enhance_log(used_card_list, clover_name, clover_bind, success)
                # 点掉强化区域的卡片后，才能再次进行强化
                click(287, 343)
                # 强化次数+1
                self.enhance_times += 1
                self.enhance_count += 1
                # 发送统计信息
                recorder.make_stat_and_record(used_card_list, clover_name, clover_bind,
                                              original_success_rate, extra_success_rate, success)
                # 是否循环标识符
                self.cards_enough = True
                return
        # 不可强化，统计目前卡片星级与数量(无视卡片名与0星卡)
        self.cards_enough = False

    def can_enhance(self, card_list: list[Card], need_card_list: list[Card]) -> tuple:
        """
        是否可强化检查
        还能修改临时强化列表，保证下次调用循环时，低等级方案不会使用高等级方案主卡存在时的副卡，以及返回强化所需的卡片
        Args:
            card_list: 当前卡片列表，已经被浅拷贝过
            need_card_list: 需要的卡片列表
        Returns:
            bool: 是否可强化
            list: 需要的位置列表
        """
        used_card_list = []
        for need_card in need_card_list:
            for card in card_list:
                # 根据需求卡的类型判断匹配条件
                if need_card.name in self.pack_names:
                    # 卡包类卡片处理
                    card_in_pack = card.name in self.settings["卡包配置"].get(need_card.name, [])
                    level_match = card.level == need_card.level
                    bind_check = (need_card.bind != 2) and (card.bind == need_card.bind)

                    if card_in_pack and level_match and (need_card.bind == 2 or bind_check):
                        used_card_list.append(card)
                        card_list.remove(card)
                        break
                elif need_card.bind == 2:
                    # 不绑绑定混用类卡片处理
                    if card.name == need_card.name and card.level == need_card.level:
                        used_card_list.append(card)
                        card_list.remove(card)
                        break
                else:
                    # 普通卡片处理
                    if card == need_card:
                        used_card_list.append(card)
                        card_list.remove(card)
                        break
            else:
                # 找不到对应需求卡，立即返回失败
                return False, []
        # 顺利全部找到，返回可强化标识符与找到的卡片列表
        return True, used_card_list

    # 点掉绑定弹窗
    def click_warning_dialog(self):
        # 弹窗出现有延迟，需要循环检测
        for i in range(10):
            img = get_image(440, 260, 40, 40)
            # 还没出现就等一等
            if not direct_img_match(img, resource.bind_dialog):
                # 点击强化按钮
                click(285, 436)
                QThread.msleep(100)
            else:
                break
        # 反复检测弹窗有没有被点掉，跟检测卡槽是一样的
        for i in range(30):
            img = get_image(440, 260, 40, 40)
            if direct_img_match(img, resource.bind_dialog):
                click(425, 353)  # 弹窗还在就继续点确定
                QThread.msleep(100)
            else:
                return
        else:
            event_manager.emit("怎么这样", "你这绑定弹窗怎么点不掉呀")
            return

    def start_gem_decomposition(self):
        self.gem_enhance_btn.setEnabled(False)
        self.gem_decompose_btn.setEnabled(False)
        self.stopbtn.setEnabled(True)
        self.gemEnhancerThread.start_decompose()

    def start_gem_enhance(self):
        self.gem_decompose_btn.setEnabled(False)
        self.gem_enhance_btn.setEnabled(False)
        self.stopbtn.setEnabled(True)
        self.gemEnhancerThread.start_enhance()

    def dull_detection(self, mode: str = None):
        """
        防呆检测
        防呆不防傻，大力出奇迹
        """
        # 能使用的强卡方案里，有没有副卡全是无的？
        for j in range(self.max_level, self.min_level, -1):
            # 初始化无计数
            none_count = 0
            name_None_count = 0
            # 遍历可用的强卡方案
            for k in range(1, 4):
                subcard = self.settings["强化方案"][f"{j - 1}-{j}"][f'副卡{k}']
                subcard_level = subcard.get('星级', '无')
                if subcard_level == "无":
                    # 将无计数加一
                    none_count += 1
                # 如果有三个无，就直接弹窗，并停止运行
                if none_count == 3:
                    event_manager.show_dialog_signal.emit("这……", f"{j - 1}-{j}方案的副卡全是无，回去再设置设置吧……")
                    self.onStop()
                    return
                # 确认这些副卡是不是都存在卡片名称
                subcard_name = subcard.get('卡片名称', '无')
                if subcard_name == "无":
                    name_None_count += 1
                if name_None_count == 3:
                    event_manager.show_dialog_signal.emit("嗯嗯？",
                                                          "你还没有设置要强化的卡片呢！请到强卡方案——强化类型按钮里去进行设置，或使用乌瑟勋爵一键设置")
                    self.onStop()
                    return
        if mode == "仅强卡":
            return
        # 生产方案中，有没有选择要使用的香料？
        if not any(list(self.settings["生产方案"].values())):
            event_manager.show_dialog_signal.emit("┗|｀O′|┛ 嗷~~",
                                                  "你还没有设置要使用的香料呢！请到生产方案——使用香料按钮里去进行设置")
            self.onStop()
            return

        # 通过防呆检测，就可以正常开始~
        return

    # 劲 爆 弹 窗
    @pyqtSlot(str, str)
    def show_dialog(self, title, message):
        # 停止运行
        self.is_running = False
        GLOBALS.IS_RUNNING = False

        # 如果打开了弹窗后刷新游戏
        if self.failed_refresh and self.failed_refresh_count < 5:
            # 弹窗计数+1
            self.failed_refresh_count += 1
            return
        elif self.failed_refresh_count == 5:
            title = "已达到弹窗后刷新上限"
            message = "呼……好累……老是弹窗……刷新不动了……"
            self.failed_refresh_count += 1

        # 将弹窗内容记录到日志中
        logger.info(f"[芙芙弹窗] {title}：{message}")
        msg = QMessageBox()
        # 设置愤怒的芙芙作为图标
        angry_furina = QPixmap(resource_path("items/icon/angry_furina.png"))
        normal_furina = resource_path("items/icon/furina.ico")
        msg.setIconPixmap(angry_furina)
        msg.setWindowIcon(QIcon(normal_furina))
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        # 同时显示系统通知 打包后有BUG，找不到获取平台的方法，原因不明 这BUG起码四年了
        # 解决方法：打包时添加--hidden-import plyer.platforms.win.notification
        plyer.notification.notify(
            title=title,
            message=message,
            app_name='天知强卡器',
            timeout=5,  # 通知显示的时间
            app_icon=normal_furina,
        )
        msg.exec()

    # 输出日志
    def send_log_message(self, message):
        """
        将信息输出到强卡日志，顺便也输出到Log里
        """
        self.output_log.append(f"{message}")
        logger.info(message)

        # 输出完成后，自动滚动到最新消息
        self.output_log.verticalScrollBar().setValue(
            self.output_log.verticalScrollBar().maximum()
        )

    # 输入二级密码
    def check_second_password(self) -> None:
        # 先检查二级密码设置
        if self.settings["个人设置"]["二级密码"] == "":
            # 弹窗提示
            event_manager.show_dialog_signal.emit("啊哇哇哇哇", "你没有填二级密码开什么二级密码输入功能呀")
            return
        # 确保当前位置处于主菜单
        if check_position() != "主菜单":
            self.send_log_message("找不到跳转按钮，不输入二级密码")
            return
        # 跳转到暗晶商店，尝试兑换星座卡随机礼包
        click(870, 556)
        QThread.msleep(500)
        click(880, 225)
        QThread.msleep(500)
        click(795, 488)
        QThread.msleep(500)
        click(177, 65)
        QThread.msleep(500)
        click(407, 449)
        QThread.msleep(500)
        # 检查停止标识
        if not self.is_running:
            return
        # 循环输入二级密码
        for char in self.settings["个人设置"]["二级密码"]:
            win32gui.PostMessage(self.handle, win32con.WM_CHAR, ord(char), 0)
            QThread.msleep(100)
        # 输入完成后点击完成
        click(438, 386)
        QThread.msleep(500)
        # 退出暗晶商店和公会副本，归位到主界面
        click(917, 38)
        QThread.msleep(500)
        click(912, 78)
        QThread.msleep(500)

    def reload_game(self):

        def click_refresh_btn():

            # 点击刷新按钮 该按钮在360窗口上
            find = loop_match_p_in_w(
                source_handle=self.handle_360,
                source_root_handle=self.handle_360,
                source_range=[0, 0, 400, 100],
                template=resource_path("items/login/0_刷新.png"),
                match_tolerance=0.9,
                after_sleep=3,
                click=True,
                click_function=click)

            if not find:
                find = loop_match_p_in_w(
                    source_handle=self.handle_360,
                    source_root_handle=self.handle_360,
                    source_range=[0, 0, 400, 100],
                    template=resource_path("items/login/0_刷新_被选中.png"),
                    match_tolerance=0.98,
                    after_sleep=3,
                    click=True,
                    click_function=click)

                if not find:

                    find = loop_match_p_in_w(
                        source_handle=self.handle_360,
                        source_root_handle=self.handle_360,
                        source_range=[0, 0, 400, 100],
                        template=resource_path("items/login/0_刷新_被点击.png"),
                        match_tolerance=0.98,
                        after_sleep=3,
                        click=True,
                        click_function=click)

                    if not find:
                        logger.info("未找到360大厅刷新游戏按钮, 可能导致一系列问题...")

        def try_enter_server_4399():
            # 4399 进入服务器
            my_result = match_p_in_w(
                source_handle=self.handle_browser,
                source_root_handle=self.handle_360,
                source_range=[0, 0, 2000, 2000],
                template=resource_path("items/login/1_我最近玩过的服务器_4399.png"),
                match_tolerance=0.9
            )
            if my_result:
                # 点击进入服务器
                click(x=my_result[0], y=my_result[1] + 30, handle=self.handle_browser)
                return True
            return False

        def try_enter_server_qq_space():
            # QQ空间 进入服务器
            my_result = match_p_in_w(
                source_handle=self.handle_browser,
                source_root_handle=self.handle_360,
                source_range=[0, 0, 2000, 2000],
                template=resource_path("items/login/1_我最近玩过的服务器_QQ空间.png"),
                match_tolerance=0.9
            )
            if my_result:
                # 点击进入服务器
                click(x=my_result[0] + 20, y=my_result[1] + 30, handle=self.handle_browser)
                return True
            return False

        def try_enter_server_qq_game_hall():
            # QQ游戏大厅 进入服务器
            my_result = match_p_in_w(
                source_handle=self.handle_browser,
                source_root_handle=self.handle_360,
                source_range=[0, 0, 2000, 2000],
                template=resource_path("items/login/1_我最近玩过的服务器_QQ游戏大厅.png"),
                match_tolerance=0.9
            )
            if my_result:
                # 点击进入服务器
                click(x=my_result[0], y=my_result[1] + 30, handle=self.handle_browser)
                return True
            return False

        def main():
            while True:

                # 点击刷新按钮 该按钮在360窗口上
                logger.info("[刷新游戏] 点击刷新按钮...")
                click_refresh_btn()

                # 是否在 选择服务器界面 - 判断是否存在 最近玩过的服务器ui(4399 or qq空间) 或 开始游戏(qq游戏大厅) 并进入
                result = False

                logger.info("[刷新游戏] 判定4399平台...")
                result = result or try_enter_server_4399()

                logger.info("[刷新游戏] 判定QQ空间平台...")
                result = result or try_enter_server_qq_space()

                logger.info("[刷新游戏] 判定QQ游戏大厅平台...")
                result = result or try_enter_server_qq_game_hall()

                # 如果未找到进入服务器，从头再来
                if not result:
                    logger.info("[刷新游戏] 未找到进入服务器, 可能 1.QQ空间需重新登录 2.360X4399微端 3.意外情况")

                    result = loop_match_p_in_w(
                        source_handle=self.handle_browser,
                        source_root_handle=self.handle_360,
                        source_range=[0, 0, 2000, 2000],
                        template=resource_path("items/login/空间服登录界面.png"),
                        match_tolerance=0.95,
                        match_interval=0.5,
                        match_failed_check=5,
                        after_sleep=5,
                        click=True,
                        click_function=click)
                    if result:
                        logger.info("[刷新游戏] 找到QQ空间服一键登录, 正在登录")
                    else:
                        logger.info("[刷新游戏] 未找到QQ空间服一键登录, 可能 1.360X4399微端 2.意外情况, 继续")

                """查找大地图确认进入游戏"""
                logger.info("[刷新游戏] 循环识图中, 以确认进入游戏...")
                # 更严格的匹配 防止登录界面有相似图案组合
                result = loop_match_ps_in_w(
                    source_handle=self.handle_browser,
                    source_root_handle=self.handle_360,
                    template_opts=[
                        {
                            "source_range": [840, 525, 2000, 2000],
                            "template": resource_path("items/login/跳转.png"),
                            "match_tolerance": 0.98,
                        }, {
                            "source_range": [610, 525, 2000, 2000],
                            "template": resource_path("items/login/任务.png"),
                            "match_tolerance": 0.98,
                        }, {
                            "source_range": [890, 525, 2000, 2000],
                            "template": resource_path("items/login/后退.png"),
                            "match_tolerance": 0.98,
                        }
                    ],
                    return_mode="and",
                    match_failed_check=30,
                    match_interval=1
                )

                if result:
                    logger.info("[刷新游戏] 循环识图成功, 确认进入游戏! 即将刷新Flash句柄")

                    # 重新获取句柄, 此时游戏界面的句柄已经改变
                    self.handle = self.get_handle_cus(mode="flash")
                    GLOBALS.HWND = self.handle

                    # [4399] [QQ空间]关闭健康游戏公告
                    logger.info("[刷新游戏] [4399] [QQ空间] 尝试关闭健康游戏公告")
                    loop_match_p_in_w(
                        source_handle=self.handle,
                        source_root_handle=self.handle_360,
                        source_range=[0, 0, 950, 600],
                        template=resource_path("items/login/3_健康游戏公告_确定.png"),
                        match_tolerance=0.97,
                        match_failed_check=5,
                        after_sleep=1,
                        click=True,
                        click_function=click)

                    logger.info("[刷新游戏] 尝试关闭每日必充界面")
                    # [每天第一次登陆] 每日必充界面关闭
                    loop_match_p_in_w(
                        source_handle=self.handle,
                        source_root_handle=self.handle_360,
                        source_range=[0, 0, 950, 600],
                        template=resource_path("items/login/4_退出每日必充.png"),
                        match_tolerance=0.99,
                        match_failed_check=3,
                        after_sleep=1,
                        click=True,
                        click_function=click)

                    logger.info("[刷新游戏] 已完成")

                    return
                else:
                    logger.info("[刷新游戏] 查找大地图失败, 点击服务器后未能成功进入游戏, 刷新重来")

        main()


class EnhancerThread(QThread):

    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.enhancer = tenchi_cards_enhancer

    # 强卡器循环,分为3种模式，分别是：0.固定制卡 1.混合制卡 2.动态制卡
    def run(self):
        # 初始化最高等级卡片位置
        self.enhancer.single_max_card_position = 0
        # 如果打开了输入二级密码，且处于能看到合成屋的位置，则代替输入二级密码
        if self.enhancer.settings["个人设置"]["是否输入二级密码"]:
            self.enhancer.check_second_password()
        if not self.enhancer.is_running:
            return
        # 初始化卡片名称集合
        self.enhancer.card_names = get_card_names(
            self.enhancer.settings["强化方案"],
            self.enhancer.settings["卡包配置"],
            self.enhancer.min_level,
            self.enhancer.max_level
        )
        # 初始化位置，保证位置在合成屋或强化页面
        if not self.init_position():
            return
        while self.enhancer.is_running:
            # 如果强化到达一定时间，且打开刷新游戏设置，就刷新游戏重进一下游戏, 防止卡顿
            if self.enhancer.is_reload_game and time.time() - self.enhancer.time_last_reload_game >= self.enhancer.reload_time * 60:
                self.reload_game()
            # 检查停止标识
            if not self.enhancer.is_running:
                break
            # 如果强化到了一定次数，就退出重进一下合成屋，防止卡顿
            if self.enhancer.enhance_times >= self.enhancer.reload_count:
                self.reload_house()
            # 进行动态制卡
            dynamic_card_producer(self.enhancer.settings, self.enhancer.card_count_dict)
            # 清空卡片列表
            self.enhancer.card_list = []
            QThread.msleep(400)
            if not self.enhancer.is_running:
                break
            # 制作后，点击卡片强化标签
            change_position("卡片强化", "卡片制作")
            QThread.msleep(200)
            # 强化主函数
            self.enhancer.main_enhancer()
            # 获取卡片数量字典
            self.enhancer.card_count_dict = make_card_count_dict(self.enhancer.card_list)
            # 检查停止标识
            if not self.enhancer.is_running:
                break
            QThread.msleep(100)
            # 数组卡片全部强化完成后，点击卡片制作标签，再次循环
            change_position("卡片制作", "卡片强化")
            QThread.msleep(200)
        # 如果开启了弹窗后刷新功能，则刷新一次
        if (self.enhancer.failed_refresh and self.enhancer.failed_refresh_count != 0
                and self.enhancer.failed_refresh_count <= 5):
            logger.info("危险设置！ 弹窗后刷新游戏")
            self.enhancer.is_running = True
            self.reload_game()
            self.run()  # 递归调用

    # 初始化位置,使用截图与识图函数判断当前位置，一共有三次判断：1.判断窗口上是否有合成屋图标，如果有就点击 2.根据右上角的“XX说明”判断目前所处位置，分别执行不同操作
    def init_position(self) -> bool:
        position = check_position()  # 获取位置标识
        if position == "主菜单":
            # 进入合成屋的卡片制作页面
            change_position("卡片制作")
            # 停顿久一些，加载图片
            QThread.msleep(1000)
            return True
        elif position == "卡片制作":
            return True
        elif position == "卡片强化":
            # 强化主函数
            self.enhancer.main_enhancer()
            QThread.msleep(200)
            # 检查运行标识符
            if not self.enhancer.is_running:
                return False
            # 获取卡片数量字典
            self.enhancer.card_count_dict = make_card_count_dict(self.enhancer.card_list)
            # 切换到卡片制作页面，进入主循环
            change_position("卡片制作")
            QThread.msleep(500)
            return True
        else:
            # 未知位置，弹窗提示
            event_manager.show_dialog_signal.emit("哇哦",
                                                  "未知位置，你在哪里？异次元空间吗？\n仅支持360游戏大厅，请确保将芙芙拖到游戏窗口内")
            # 停止运行
            self.enhancer.is_running = False
            return False

    def reload_house(self):
        # 点击右上角的红叉
        click(914, 38)
        QThread.msleep(600)
        # 重新点击合成屋
        click(685, 558)
        QThread.msleep(600)
        # 归零强化次数
        self.enhancer.enhance_times = 0

    def reload_game(self) -> None:

        if self.enhancer.window_name_360:
            logger.info("时间差不多喽, 360游戏大厅刷新")
            self.enhancer.reload_game()
            # 刷新后检查二级密码
            if self.enhancer.settings["个人设置"]["是否输入二级密码"]:
                self.enhancer.check_second_password()
            # 重新点击合成屋
            click(685, 558)
            QThread.msleep(3000)
            # 归零强化次数
            self.enhancer.enhance_times = 0
            self.enhancer.single_max_card_position = 0  # 刷新后要初始化卡片位置
        else:
            logger.info("虽然到一小时了, 但非360游戏大厅 不刷新")

        # 重新获取当前时间戳 s
        self.enhancer.time_last_reload_game = time.time()

    def start_loop(self):
        if self.enhancer.handle is not None:
            self.start()
        else:
            event_manager.show_dialog_signal.emit("喂！", "你还没获取句柄呢！")


# 仅强卡线程
class EnhanceOnlyThread(QThread):

    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.enhancer = tenchi_cards_enhancer

    def run(self):
        # 判断当前位置，如果不在强化页面，就直接弹窗
        position = check_position()
        if position != "卡片强化":
            event_manager.show_dialog_signal.emit("等等", "先把页面调到卡片强化后再点我啊！")
            return
        # 初始化卡片名称集合
        self.enhancer.card_names = get_card_names(
            self.enhancer.settings["强化方案"],
            self.enhancer.settings["卡包配置"],
            self.enhancer.min_level,
            self.enhancer.max_level
        )
        # 截图后强化
        self.enhancer.main_enhancer()
        # 强化完成后弹窗
        event_manager.show_dialog_signal.emit("哇哦", "强化完成！没有可强化的卡片了")
        return

    def start_enhance(self):
        # 存在句柄时，启动线程
        if self.enhancer.handle is not None:
            self.start()
        else:
            event_manager.show_dialog_signal.emit("喂！", "你还没获取句柄呢！")


TEST_MODE = False
# 非打包环境下启动测试模式
if not getattr(sys, 'frozen', False):
    logger.debug("阿布拉卡达布拉！测试模式启动！")
    TEST_MODE = True


# 主函数
def main():
    app = QApplication(sys.argv)
    # 设置禁用状态下的按钮文本颜色
    palette = QPalette()
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#888888"))
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Button,
                     QColor(255, 255, 255, 190))
    app.setPalette(palette)
    # 设置默认字体
    font_id = QFontDatabase.addApplicationFont(resource_path("items/font/font.ttf"))
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        font = QFont(font_family, 10)
        app.setFont(font)
    enhancer = TenchiCardsEnhancer()
    enhancer.show()
    sys.exit(app.exec())


# 设置进程为每个显示器DPI感知V2,Qt6默认就是这个
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = c_void_p(-4)
windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)

if __name__ == '__main__':
    main()
