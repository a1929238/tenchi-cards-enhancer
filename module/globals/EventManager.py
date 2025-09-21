from PyQt6.QtCore import QObject, pyqtSignal


class MidSignalPrint:
    """
    模仿信号的类, 但其实本身完全不是信号, 是为了可以接受缺省参数而模仿的中间类,
    该类的emit方法是 一个可以输入 缺省的颜色 或 时间参数 来生成文本的方法
    并调用信号发送真正的信息
    """

    def __init__(self):
        super().__init__()
        self.color_scheme = None

    def set_theme(self, theme):
        if theme == 'light':
            self.color_scheme = {
                1: "C80000",  # 深红色
                2: "E67800",  # 深橙色暗调
                3: "006400",  # 深绿色
                4: "009688",  # 深宝石绿
                5: "0056A6",  # 深海蓝
                6: "003153",  # 普鲁士蓝
                7: "5E2D79",  # 深兰花紫
                8: "4B0082",  # 靛蓝
                9: "999999",  # 我也不知道啥色
                }
        else:
            self.color_scheme = {
                1: "FF4C4C",  # 鲜红色
                2: "FFA500",  # 橙色
                3: "00FF00",  # 亮绿色
                4: "20B2AA",  # 浅海绿色
                5: "1E90FF",  # 道奇蓝
                6: "4682B4",  # 钢蓝色
                7: "9370DB",  # 中兰花紫
                8: "8A2BE2",  # 蓝紫色
                9: "CCCCCC",  # 浅灰色
            }

    def emit(self, text, color_level=9, color=None, time=True, is_line=False, line_type="normal"):
        """
        :param text: 正文文本
        :param color_level: int 1 to 9, 优先使用
        :param color: 支持直接使用颜色代码, 次要使用
        :param time: 是否显示打印时间
        :param is_line: 是否替换本行为横线
        :param line_type: str normal/top/bottom
        :return:
        """

        if color_level in self.color_scheme:
            color = self.color_scheme[color_level]
        elif not color:
            color = self.color_scheme[9]
        if is_line:
            text = "—" * 44
            time = False
            if line_type == "top":
                text = "‾" * 67
            if line_type == "bottom":
                text = "_" * 59

        event_manager.log_signal_true.emit(text, color, time)


class EventManager(QObject):
    """
    管理全局事件信号
    """
    show_dialog_signal = pyqtSignal(str, str)
    log_signal = MidSignalPrint()
    log_signal_true = pyqtSignal(str, str, bool)  # 文本, 颜色代码, 是否显示时间
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


# 全局访问点
event_manager = EventManager()
