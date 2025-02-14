import csv
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import List, Any

from module.log.TenchiLogger import logger
from module.utils import resource_path


class AsyncStatsRecorder:
    def __init__(
            self,
            filename: str,
            max_buffer_size: int = 100,
            flush_interval: float = 5.0
    ):
        # 分解文件名基础路径和扩展名
        self.base, self.ext = os.path.splitext(filename)
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval

        # 双缓冲队列
        self.active_buffer: List[List[Any]] = []
        self.backup_buffer: List[List[Any]] = []
        self.lock = threading.Lock()

        # 文件头配置
        self.header = [
            "timestamp",  # float 时间戳
            "main_star", "main_name", "main_bind",  # int, str, bool
            "sub_star1", "sub_name1", "sub_bind1",
            "sub_star2", "sub_name2", "sub_bind2",
            "sub_star3", "sub_name3", "sub_bind3",
            "clover_name", "clover_bind",  # str, bool
            "original_success_rate", "extra_success_rate", "result"  # float, float, bool
        ]

        # 后台线程控制
        self.running = True
        self.thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.thread.start()

    def record(self, data: List[Any]):
        """添加单条合成记录到缓冲区

        记录装备合成过程中的各项数据，数据字段顺序必须与类头配置self.header严格对应。
        该方法线程安全，当缓冲区达到最大限制时会自动触发缓冲区切换。

        Args:
            data (List[Any]): 需要记录的合成数据列表，元素顺序及类型应为：
                [
                    float,  # timestamp 时间戳
                    int, str, bool,  # main_star, main_name, main_bind 主卡信息
                    int, str, bool,  # sub_star1, sub_name1, sub_bind1 副卡1信息
                    int, str, bool,  # sub_star2, sub_name2, sub_bind2 副卡2信息
                    int, str, bool,  # sub_star3, sub_name3, sub_bind3 副卡3信息
                    str, bool,       # clover_name, clover_bind 四叶草信息
                    float, float, bool  # original_success_rate, extra_success_rate, result 成功率及结果
                ]

        Notes:
            - 使用线程锁保证多线程安全
            - 当缓冲区达到max_buffer_size时会触发缓冲区交换
            - 实际写入操作由后台刷新线程完成
        """
        # 通过线程锁保证操作的原子性
        with self.lock:
            # 将新记录添加到当前激活缓冲区
            self.active_buffer.append(data)

            # 检查缓冲区是否达到容量上限
            if len(self.active_buffer) >= self.max_buffer_size:
                # 触发缓冲区切换（非阻塞，由后台线程处理持久化）
                self._swap_buffers()

    def make_stat_and_record(self, used_card_list, clover_name, clover_bind,
                             original_success_rate, extra_success_rate,
                             result):
        """
        制作统计数据并进行记录
        """
        # 获取当前时间戳
        timestamp = time.time()

        # 主卡信息
        main_card = used_card_list[0]
        main_info = [main_card.level, main_card.name, main_card.bind]

        # 副卡信息
        sub_cards = used_card_list[1:]
        sub_info = []
        for sub_card in sub_cards:
            sub_info.extend([sub_card.level, sub_card.name, sub_card.bind])
        # 如果不足 3 个副卡，则用None填充
        while len(sub_info) < 3 * 3:
            sub_info.extend([None, None, None])

        # 四叶草信息
        if clover_name != "无":
            clover_info = [clover_name, clover_bind]
        else:
            clover_info = [None, None]

        # 制作完整记录数据列表
        record_data = (
                [timestamp] +  # 时间戳
                main_info +  # 主卡信息
                sub_info +  # 三个副卡信息
                clover_info +  # 四叶草信息
                [original_success_rate, extra_success_rate, result]  # 成功率及结果
        )

        # 记录
        self.record(record_data)

    def _swap_buffers(self):
        """交换缓冲区（线程安全）"""
        with self.lock:
            self.active_buffer, self.backup_buffer = \
                self.backup_buffer, self.active_buffer

    def _flush_to_disk(self):
        """将备份缓冲区写入磁盘"""
        if not self.backup_buffer:
            return

        file = f"{self.base}{self.ext}"
        try:
            # 自动创建目录
            os.makedirs(os.path.dirname(file), exist_ok=True)

            # 判断是否需要表头
            need_header = not os.path.exists(file)

            # 使用支持全角字符的编码
            with open(file, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if need_header:
                    writer.writerow(self.header)
                writer.writerows(self.backup_buffer)
        except Exception as e:
            logger.error(f"文件写入失败 [{file}]: {e}")

        self.backup_buffer.clear()

    def _flush_loop(self):
        """后台刷新线程"""
        while self.running:
            start = time.time()
            self._swap_buffers()
            self._flush_to_disk()
            time.sleep(max(0, self.flush_interval - (time.time() - start)))

    def close(self):
        """安全关闭"""
        self.running = False
        self.thread.join()
        self._swap_buffers()
        self._flush_to_disk()


recorder = AsyncStatsRecorder("enhance_stats/card_stats.csv")
