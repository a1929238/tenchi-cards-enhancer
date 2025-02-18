from __future__ import annotations
import threading
import time
from typing import TYPE_CHECKING

import pywintypes
import win32pipe
import win32file
import queue

from module.globals.EventManager import event_manager
from module.log.TenchiLogger import logger

if TYPE_CHECKING:
    from TenchiCardEnhancer import TenchiCardsEnhancer


class PipeCommunicationThread(threading.Thread):
    def __init__(self, pipe_name, enhancer: TenchiCardsEnhancer):
        super().__init__()
        self.pipe_name = r'\\.\pipe\\' + pipe_name
        self.enhancer = enhancer
        self.is_running = True
        self.pipe = None
        self.connected = False
        self.send_queue = queue.Queue()  # 发送队列

    def run(self):
        logger.debug("尝试连接FAA……")
        if not self.connect_to_pipe():
            logger.debug("无法连接到管道，线程退出。")
            return
        self.connected = True
        event_manager.log_signal.emit(f"应FAA召唤而来，你就是我的主人吗？")

        while self.is_running:
            try:
                # 优先处理发送队列中的消息
                while not self.send_queue.empty():
                    message = self.send_queue.get_nowait()
                    try:
                        win32file.WriteFile(self.pipe, message)
                        logger.debug(f"发送消息成功: {message}")
                    except pywintypes.error as e:
                        logger.debug(f"发送消息出错: {e}")
                        self.stop()  # 出错时停止
                        break  # 退出内层循环

                # 非阻塞读取
                _, _, messages_left = win32pipe.PeekNamedPipe(self.pipe, 0)
                if messages_left > 0:
                    try:
                        hr, data = win32file.ReadFile(self.pipe, 65536)
                        if hr == 0 and data:
                            message = data.decode('utf-8')
                            logger.debug(f"Received message: {message}")
                            if message == "exit":  # 接收到退出消息
                                self.stop()
                                break
                            # 处理消息...
                            if message.split(",")[0] == 'enhance_card':
                                self.enhancer.task_signal.emit(message)
                            elif message.split(",")[0] == 'decompose_gem':
                                self.enhancer.task_signal.emit(message)
                    except pywintypes.error as e:
                        if e.args[0] == 2:
                            logger.debug("管道另一端没有进程。")
                            self.stop()
                        elif e.args[0] == 109:
                            logger.debug("管道已结束")
                            self.stop()
                        elif e.args[0] == 234:
                            continue
                        else:
                            logger.debug(f"Pipe read error: {e}")
                            self.stop()
                            break

            except Exception as e:
                logger.debug(f"Error in pipe thread: {e}")
                self.stop()
                break
            time.sleep(1)

    def connect_to_pipe(self):
        """尝试连接到命名管道，最多尝试10次，每次间隔1秒"""
        for attempt in range(10):
            try:
                logger.debug(f"尝试连接到管道（第 {attempt + 1} 次）...")
                self.pipe = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,  # No sharing
                    None,  # Default security attributes
                    win32file.OPEN_EXISTING,  # Opens existing pipe
                    0,  # Default attributes
                    None  # No template file
                )
                # 设置管道的读取模式为消息模式
                win32pipe.SetNamedPipeHandleState(self.pipe, win32pipe.PIPE_READMODE_MESSAGE, None, None)
                self.connected = True
                return True  # 连接成功
            except pywintypes.error as e:
                if e.args[0] == 2:  # ERROR_FILE_NOT_FOUND
                    logger.debug("管道不存在")
                    return
                elif e.args[0] == 231:  # ERROR_PIPE_BUSY
                    logger.debug("管道繁忙，等待1秒...")
                    time.sleep(1)
                else:
                    logger.debug(f"连接管道时发生错误: {e}")
                    return False  # 其他错误，直接返回

        return False  # 尝试10次后仍未连接成功

    def send_message(self, message):
        """将消息放入发送队列"""
        # 编码信息
        message = message.encode('utf-8')
        if self.connected:
            self.send_queue.put(message)
        else:
            logger.debug("管道未连接，无法发送消息。")

    def send_complete(self):
        self.send_message("complete")

    def stop(self):
        if self.is_running:  # 避免重复调用
            self.is_running = False
            self.close_pipe()

    def close_pipe(self):
        if self.pipe is not None:
            try:
                win32file.CloseHandle(self.pipe)
                logger.debug(f"管道已关闭: {self.pipe_name}")
            except pywintypes.error as e:
                logger.debug(f"关闭管道出错: {e}")
            finally:
                self.pipe = None
