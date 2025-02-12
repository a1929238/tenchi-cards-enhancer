import json
import os
import threading
import time

from module.utils import resource_path


def load_produce_stats(filename='enhance_stats/produce_stats.json'):
    """读取生产数据，不存在就创建文件夹，读取默认设置"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        filename = resource_path('GUI/default/produce_stats.json')
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)


class AsyncProduceRecorder:
    def __init__(self, filename='enhance_stats/produce_stats.json', flush_interval=5.0):
        """
        异步生产数据记录器。

        Args:
            filename (str): 存储生产数据的文件名。
            flush_interval (float): 刷新间隔（秒）。
        """
        self.produce_stats_path = filename
        self.produce_statistics = load_produce_stats(self.produce_stats_path)
        self.flush_interval = flush_interval
        self.lock = threading.Lock()
        self.running = True
        self.data_updated = threading.Event()
        self.thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.thread.start()

    def save_produce_statistic(self, bind: bool, level: int, count: int):
        """
        记录生产数据。

        Args:
            bind (bool): 是否绑定。
            level (int): 装备等级。
            count (int): 生产数量。
        """
        with self.lock:
            level_key = str(level)  # 将等级转换为字符串，以便作为 JSON 的键
            if bind:
                self.produce_statistics["bind"][level_key] += count
            else:
                self.produce_statistics["unbind"][level_key] += count
            self.data_updated.set()

    def save_gold_cost(self, gold_cost: int):
        """记录金币消耗"""
        self.produce_statistics["gold_cost"] = gold_cost
        self.data_updated.set()

    def _flush_to_disk(self):
        """将统计数据保存到 JSON 文件"""
        with self.lock:  # 确保在写入时锁定，防止数据竞争
            try:
                # 自动创建目录
                os.makedirs(os.path.dirname(self.produce_stats_path), exist_ok=True)
                with open(self.produce_stats_path, "w", encoding="utf-8") as f:
                    json.dump(self.produce_statistics, f, indent=4, ensure_ascii=False)  # 美化输出
            except Exception as e:
                print(f"保存统计数据失败: {e}")

    def _flush_loop(self):
        """后台刷新线程"""
        while self.running:
            if self.data_updated.wait(self.flush_interval):  # 等待数据更新事件
                self._flush_to_disk()  # 直接调用 _flush_to_disk
                self.data_updated.clear()
            else:
                continue

    def close(self):
        """安全关闭"""
        self.running = False
        self.thread.join()  # 等待后台线程结束
        self._flush_to_disk()  # 最后再刷新一次，确保数据全部写入


produce_recorder = AsyncProduceRecorder()
