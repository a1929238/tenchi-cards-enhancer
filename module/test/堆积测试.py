import json
import random
import time
from collections import Counter
from dataclasses import dataclass

from module.globals.DataClass import Card
from module.utils import merge_card_counts


def success_check(success_rate: float) -> bool:
    """
    成功率检查
    :param success_rate: 成功率
    :return: 是否成功
    """
    return success_rate > random.random()

class TestCardProducer:
    """
    测试卡片制作-强化是否会造成堆积的单元测试
    """

    def __init__(self):
        self.card_count_dict = None
        self.spice_stock = {
            0: 20000,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 0,
            7: 0,
            8: 0
        }
        self.temp_block_list = None
        self.is_running = False
        self.all_bonus = None
        self.max_level_count = 0
        self.spice_list = ["不放香料", "天然香料", "上等香料", "秘制香料", "极品香料", "皇室香料", "魔幻香料",
                           "精灵香料",
                           "天使香料"]
        self.card_list = []
        self.max_level, self.min_level = 9, 0
        with open("C://192//code//tenchi-cards-enhancer//module//test//setting.json", 'r', encoding='utf-8') as f:
            self.settings = json.load(f)
        # 初始化卡片质量映射
        self.card_quality_map = {
            "2": "好卡",
            "0": "中卡",
            "1": "差卡"
        }
        # 初始化四叶草等级映射
        self.clover_level_map = {
            "0": "无四叶草",
            "1": "1级四叶草",
            "2": "2级四叶草",
            "3": "3级四叶草",
            "4": "4级四叶草",
            "5": "5级四叶草",
            "6": "6级四叶草",
            "超能": "超能四叶草",
            "SS": "SS四叶草",
            "SSS": "SSS四叶草",
            "SSR": "SSR四叶草"
        }
        # 初始化VIP等级对强化成功率加成映射
        self.VIP_bonus = {
            "0": 0,
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0.03,
            "5": 0.04,
            "6": 0.05,
            "7": 0.07,
            "8": 0.08,
            "9": 0.09,
            "10": 0.11,
            "11": 0.13,
            "12": 0.15
        }
        # 初始化公会合成屋等级对强化成功率加成映射
        self.guild_bonus = {
            "0": 0,
            "1": 0.01,
            "2": 0.03,
            "3": 0.05,
            "4": 0.08,
            "5": 0.12
        }
        # 初始化总概率加成
        self.get_bonus()

        # 读取强化概率文件
        with open("C://192//code//tenchi-cards-enhancer//GUI//card_dict//compose.json", 'r', encoding='utf-8') as f:
            self.probability = json.load(f)

    def get_bonus(self):
        """
        获取总加成
        :return: 总加成
        """
        guild_compose_level = 5
        vip_level = 8
        self.all_bonus = self.guild_bonus[str(guild_compose_level)] + self.VIP_bonus[str(vip_level)]

    def success_rate_calculate(self, main_card: Card, sub_cards: list[Card], clover_level: str) -> tuple:
        """
        计算成功率
        """
        base_rates = []
        # 获取主卡等级
        main_card_level = main_card.level
        # 基于主卡，获得所有副卡概率
        for sub_card in sub_cards:
            quality = 2
            sub_card_level = sub_card.level
            if int(sub_card_level) - int(main_card_level) > 2:
                base_rates.append(1)
                break
            elif int(main_card_level) - int(sub_card_level) >= 3:
                base_rates.append(0)
            else:
                base_rates.append(
                    float(self.probability[f'{main_card_level}']["rate"][f'{quality}'][f'{sub_card_level}']))
        # 找到最高概率
        highest_rate = max(base_rates)
        base_rates.remove(highest_rate)
        if base_rates:  # 如果基础概率不是空列表,就把它们/3,并加到最高概率上
            for rate in base_rates:
                highest_rate += rate / 3
        # 四叶草加成
        if clover_level != "无":
            highest_rate = highest_rate * self.probability["clover"][clover_level.replace("级", "")]
        # 总概率加成
        bonus_rate = highest_rate * self.all_bonus
        success_rate = highest_rate + bonus_rate
        if highest_rate >= 1:
            success_rate = 1
            bonus_rate = 0.2
        return success_rate, bonus_rate

    def simulate_card_production(self, card_name, level, bind, count):
        for i in range(count):
            self.card_list.append(
                Card(card_name, level, bind)
            )

    def main_enhancer(self):
        # 每次强化，卡片的顺序都会改变，只能强化一次截一次图，直到强卡器返回False，才停止循环
        while self.is_running:
            if not self.card_enhancer():
                # 删掉列表里等于最高等级的卡
                self.card_list = [card for card in self.card_list if card.level != self.max_level]
                self.make_card_level_dict()
                break

    def card_enhancer(self):
        """
        强化方案中，卡片信息统一为字典，字典内包含以下内容：
        星级：星级
        卡片名称：卡片名称
        绑定：是否绑定
        """
        # 拷贝卡片列表，避免修改原列表
        card_list = self.card_list.copy()
        # 按照最高强化卡片，从高到低，遍历设置里的强化方案，获取所需副卡，如果卡片总量大于等于方案所需卡片，就遍历card字典的位置，点击卡片，强化一次
        for enhance_level in range(self.max_level, self.min_level, -1):
            # 如果该等级位于临时屏蔽列表中，则跳过
            if self.temp_block_list and enhance_level - 1 in self.temp_block_list:
                continue
            else:
                # 获取当前星级强化方案
                enhance_plan = self.settings["强化方案"][f"{enhance_level - 1}-{enhance_level}"]
            # 获取主卡信息
            main_card = Card()
            main_card.load_from_dict(enhance_plan["主卡"])
            # 获取副卡信息
            sub_cards = []
            for i in range(1, 4):
                if enhance_plan[f"副卡{i}"]["星级"] != "无":
                    # 如果副卡存在星级，则将其添加到数组内
                    sub_card = Card()
                    sub_card.load_from_dict(enhance_plan[f"副卡{i}"])
                    sub_cards.append(sub_card)
            # 解耦合，检查是否可以强化
            can_enhance = self.can_enhance(main_card, sub_cards, card_list)
            if not can_enhance:
                continue
            # 删除掉列表中的主卡和副卡
            main_idx = self.card_list.index(main_card)
            del self.card_list[main_idx]
            # 删除副卡（按逆序删除以避免索引错位）
            sub_indices = []
            for sub in sub_cards:
                sub_idx = self.card_list.index(sub)
                sub_indices.append(sub_idx)
            # 按逆序删除副卡
            for idx in sorted(sub_indices, reverse=True):
                del self.card_list[idx]
            # 开始强化
            success_rate = self.success_rate_calculate(main_card, sub_cards, enhance_plan["四叶草"]["种类"])
            success = success_check(success_rate[0])
            if success:
                main_card.level += 1
                if main_card.level == self.max_level:
                    self.max_level_count += 1
            else:
                if main_card.level > 5:
                    main_card.level -= 1
            self.card_list.append(main_card)
            # 强化完成，返回True
            return True

        # 无法强化，返回False
        return False

    def can_enhance(self, main_card: Card, sub_cards: list[Card], card_list: list[Card]):
        """
        是否可强化检查,还能修改临时强化列表，保证低级方案不会使用高级方案主卡存在时的副卡
        """
        # 检查是否存在主卡
        for index, card in enumerate(card_list):
            if card == main_card:
                # 删除找到的主卡
                del card_list[index]
                break
        else:
            return False
        # 遍历副卡信息列表
        for sub_card_info in sub_cards:
            # 查找副卡信息是否在self.card_list中
            for index, card in enumerate(card_list):
                if card == sub_card_info:
                    # 删除找到的副卡
                    del card_list[index]
                    break
            # 如果有任何一张副卡不存在，返回False
            else:
                return False
        # 如果所有副卡信息都在self.card_dict中，返回True，还有它们的位置信息
        return True

    def dynamic_card_producer(self):
        """
        根据卡片需求动态制卡。将现存的所有卡片看作主卡，计算副卡需求。再用所有主卡需求填充制卡列表
        """
        card_demand: list[Card] = []
        # 计算卡片需求
        if self.card_count_dict:
            # 如果存在卡片等级字典，则根据卡片等级字典计算卡片需求
            card_demand = self.get_card_demand(self.card_count_dict)
        # 用主卡需求进行填充
        card_demand = self.fill_demand_with_main_card(card_demand)
        # 截取前 14 项
        limited_cards = card_demand[:14]

        # 将结果转为元组列表
        produce_list = [(card, count) for card, count in Counter(limited_cards).items()]

        # 将元组列表送到解析器里，然后送给制卡器
        produce_list = self.parse_produce_list(produce_list)
        # 如果解析器返回的produce_list为空，则表明没有香料了，返回False
        if not produce_list:
            return False
        # 进行制卡
        for card, count in produce_list:
            card_state = card.get_state()
            count = min(count, self.spice_stock[card.level])
            self.simulate_card_production(*card_state, count)
            # 删掉对应的香料
            self.spice_stock[card.level] -= count

    def get_card_demand(self, card_count_dict) -> list[Card]:
        """
        根据目前的卡片存量，计算副卡与部分主卡的总需求
        """
        card_demand = []
        enhance_plan = self.settings["强化方案"]
        sub_cards = ["副卡1", "副卡2", "副卡3"]
        sub_cards_name = []
        max_count = 14
        # 列出可用香料列表
        usable_spice = [spice_id for spice_id, stock in self.spice_stock.items() if stock > 0]
        max_spice_level = max(usable_spice)
        for card, count in card_count_dict.items():
            # 为主卡需求副卡，0星副卡需求主卡。0星卡的需求可以是21张
            plan = enhance_plan[f"{card.level}-{card.level + 1}"]
            for i in range(3):
                if plan[sub_cards[i]]["星级"] == "无" or plan["主卡"]["卡片名称"] != card.name:
                    continue
                # 如果副卡存在星级，则将其添加到数组内
                sub_card = Card()
                sub_card.load_from_dict(plan[sub_cards[i]])
                if sub_card.name != card.name:
                    sub_cards_name.append(sub_card.name)
                # 副卡的需求高于最高可用香料，则跳过
                if sub_card.level > max_spice_level:
                    continue
                # 副卡已经存在且存在五张以上，则跳过
                if sub_card in self.card_count_dict and self.card_count_dict[sub_card] >= 5:
                    continue
                if sub_card.level == 0:
                    max_count = 21
                for _ in range(min(count, max_count)):
                    card_demand.append(sub_card)
            # 为0星且不等于主卡的副卡额外添加对主卡的需求
            if card.level == 0 and card in sub_cards_name:
                for i in range(3):
                    plan = enhance_plan[f"{card.level + i}-{card.level + (1 + i)}"]
                    for j in range(3):
                        if plan[sub_cards[j]]["星级"] == "无" or plan[sub_cards[j]]["卡片名称"] != card.name:
                            continue
                        main_card = Card()
                        # 获取该副卡的主卡信息
                        main_card.load_from_dict(plan["主卡"])
                        for _ in range(min(count, max_count)):
                            card_demand.append(main_card)
        # 将卡片需求用卡片的星级进行反向排序，方便后续操作
        card_demand.sort(key=lambda x: x.level, reverse=True)
        return card_demand

    def fill_demand_with_main_card(self, card_demand: list[Card]):
        """用主卡填满卡片需求，每个主卡7张"""
        spice_list = list(range(9))
        spice_list.sort(reverse=True)
        enhance_plan = self.settings["强化方案"]
        # 列出可用香料列表
        usable_spice = [spice_id for spice_id, stock in self.spice_stock.items() if stock > 0]
        # 逆向排序可用香料
        usable_spice.sort(reverse=True)
        for level in usable_spice:
            # 如果香料的余量不足，则仅用这些香料
            if self.spice_stock[level] < 7:
                count = self.spice_stock[level]
            else:
                # 两种香料时用7填充
                if len(usable_spice) > 1:
                    count = 7
                else:
                    count = 14
            card = Card()
            card.load_from_dict(enhance_plan[f"{level}-{level + 1}"]["主卡"])
            for _ in range(count):
                card_demand.append(card)
        return card_demand

    def make_card_level_dict(self):
        self.card_count_dict = {card: count for card, count in Counter(self.card_list).items()}

    def parse_produce_list(self, produce_list):
        """
        根据强化方案，解析生产列表
        注意，添加的主卡一定是和使用香料对应的，但是副卡会出现没有可用香料的情况
        这种情况就要解析副卡来源，用可用香料与等级屏蔽进行填充
        """
        # 列出可用香料列表
        usable_spice = [spice_id for spice_id, stock in self.spice_stock.items() if stock > 0]
        # 对可用列表反向排序
        usable_spice.sort(reverse=True)
        # 初始化来源列表，用于记录需要单独制卡的卡片
        needed_list = []
        for card, count in produce_list:
            if card.level not in usable_spice and count > 5:
                # 分解该卡片来源
                need_cards = self.calculate_total_base_cards(card.level, usable_spice)
                needed_list += need_cards * count
        # 元组列表化需求列表
        needed_list = [(card, count) for card, count in Counter(needed_list).items()]
        # 再度过滤列表，过滤掉没有对应星级香料的卡片
        filtered_list = [
            (card, count)
            for (card, count) in produce_list
            if card.level in usable_spice
        ]
        # 将来源列表和过滤后列表合并
        filtered_list = merge_card_counts(filtered_list, needed_list)
        # 寻找最多的卡片数量，若超过21，则找到超过的比例，按比例对所有数量进行缩放
        max_count = max(count for card, count in filtered_list)
        if max_count > 21:
            delete_rate = 21 / max_count
            # 按比例对所有数量进行缩放
            filtered_list = [(card, int(count * delete_rate)) for card, count in filtered_list]

        # 返回最终列表
        return filtered_list

    def calculate_total_base_cards(self, target_level, usable_spice):
        """
        递归计算强化到目标星级所需的基础0星卡总数
        Args:
            target_level(int):需要分解的目标星级
            usable_spice(list):可用香料列表
        Returns:
             total_list:具体的所需卡片列表
        """
        total_list = []

        # 0星卡还要分解？报错！
        if target_level == 0:
            print("没有0星卡了！")
            raise ValueError("没有0星卡了！")

        # 获取对应的强化方案（格式：当前星级-目标星级）
        plan_key = f"{target_level - 1}-{target_level}"
        current_plan = self.settings["强化方案"][plan_key]

        # 递归计算主卡消耗
        main_card = Card()
        current_plan["主卡"]["星级"] = target_level - 1
        main_card.load_from_dict(current_plan["主卡"])
        # 香料可用，直接加入列表
        if main_card.level in usable_spice:
            total_list.append(main_card)
        else:
            total_list.extend(self.calculate_total_base_cards(target_level - 1, usable_spice))

        # 计算所有副卡消耗
        for key in current_plan:
            if key.startswith("副卡") and current_plan[key]["星级"] != "无":
                sub_card = Card()
                sub_card.load_from_dict(current_plan[key])
                if sub_card.level in usable_spice:
                    # 如果香料可用，直接加入列表
                    total_list.append(sub_card)
                else:
                    total_list.extend(self.calculate_total_base_cards(sub_card.level, usable_spice))

        return total_list


if __name__ == '__main__':
    test_card_producer = TestCardProducer()
    test_card_producer.is_running = True
    start_time = time.time()
    print(f'开始强卡，目前的香料为:{test_card_producer.spice_stock}')
    for _ in range(1000):
        if not test_card_producer.is_running:
            break
        # 制卡
        test_card_producer.dynamic_card_producer()

        # 强卡
        test_card_producer.main_enhancer()
        if not test_card_producer.spice_stock:
            break
    print(f'结束强卡，目前的香料为:{test_card_producer.spice_stock}')
    print(f'共耗时{time.time() - start_time}秒')
