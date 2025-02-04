from PyQt6.QtCore import QObject, pyqtSignal


class EventManager(QObject):
    """
    管理全局事件信号
    """
    show_dialog_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


# 全局访问点
event_manager = EventManager()
