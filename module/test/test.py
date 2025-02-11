import win32file
import pywintypes
import threading
import queue


class NamedPipeClient:
    def __init__(self, pipe_name):
        self.pipe_name = pipe_name
        self.handle = None
        self.read_thread = None
        self.write_thread = None

    def connect(self):
        try:
            self.handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None,
                win32file.OPEN_EXISTING,
                0, None
            )
            print("成功连接服务器")

            # 创建读写线程
            self.read_thread = PipeReadThread(self.handle)
            self.write_thread = PipeWriteThread(self.handle)

            self.read_thread.start()
            self.write_thread.start()
            return True
        except pywintypes.error as e:
            print(f"连接失败: {e.strerror}")
            return False

    def send_message(self, message):
        """提供给外部的消息发送接口"""
        self.write_thread.send(message)

    def stop(self):
        self.read_thread.stop()
        self.write_thread.stop()
        self.read_thread.join()
        self.write_thread.join()
        win32file.CloseHandle(self.handle)
        print("客户端已关闭")


# 复用与服务器端相同的读写线程类
class PipeReadThread(threading.Thread):
    # 实现与服务器端相同...
    def __init__(self, handle):
        super().__init__(daemon=True)
        self.handle = handle
        self._running = True

    def run(self):
        while self._running:
            try:
                result, data = win32file.ReadFile(self.handle, 4096)
                if data:
                    print(f"[服务器] {data.decode('utf-8')}")
            except pywintypes.error as e:
                if e.winerror == 232:  # 服务器断开
                    print("服务器已断开连接")
                    self.stop()
                else:
                    raise

    def stop(self):
        self._running = False


class PipeWriteThread(threading.Thread):
    # 实现与服务器端相同...
    def __init__(self, handle):
        super().__init__(daemon=True)
        self.handle = handle
        self._running = True
        self.message_queue = queue.Queue()

    def send(self, message):
        self.message_queue.put(message)

    def run(self):
        while self._running:
            try:
                message = self.message_queue.get(timeout=0.1)
                try:
                    win32file.WriteFile(self.handle, message.encode('utf-8'))
                except pywintypes.error as e:
                    if e.winerror == 232:
                        print("服务器已断开连接")
                        self.stop()
                    else:
                        raise
            except queue.Empty:
                continue

    def stop(self):
        self._running = False


if __name__ == '__main__':
    client = NamedPipeClient(r'\\.\pipe\MyTestPipe')
    if client.connect():
        try:
            while True:
                message = input("[客户端] 请输入消息: ")
                if message.lower() == 'exit':
                    break
                client.send_message(message)
        finally:
            client.stop()