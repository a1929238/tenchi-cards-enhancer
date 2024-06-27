# 强化模拟器，自动垫卡的前置科技
import random
import json
import itertools
import copy
from PyQt6.QtWidgets import QMessageBox

from GUI.qwidgetwebexpectation import QWidgetWebExpectation


class EnhanceSimulator:
    """
    强化的概率区间如下:
    ((基于主卡最高概率副卡) + (基于主卡次高概率副卡)/3 + (基于主卡次高概率副卡)/3) * 四叶草加成 + (前方所有概率 * 总概率加成)
    """

    def __init__(self, file_path, main_window):
        # 实例化主窗口
        self.widget = None
        self.main_window = main_window

        # 初始化模拟器卡片配置
        self.simulator_cards = {}
        self.simulator_clover_level = "0"

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
        # 初始化赛博成功率
        self.cyber_success_rate = 0

        # 读取强化概率配置文件
        with open(file_path, 'r', encoding='utf-8') as f:
            self.probability = json.load(f)

        self.all_bonus = 0
        # 初始化总概率加成
        self.get_bonus()

        # 刷新窗口
        self.refresh_ui()

    def success_rate_calculate(self, main_card: dict, sub_cards: list, clover_level: str) -> tuple:
        """
        计算成功率
        :param main_card: 主卡, 格式: {"星级": 1, "质量": "好2/中0/差1"}
        :param sub_cards: 副卡, 格式: [{"星级": 1, "质量": "好2/中0/差1"},{"星级": 1, "质量": "好2/中0/差1"}]
        :param clover_level: 四叶草等级
        :return: 总成功率, 无加成成功率
        """
        base_rates = []
        # 获取主卡等级
        main_card_level = main_card["星级"]
        # 基于主卡，获得所有副卡概率
        for sub_card in sub_cards:
            quality = sub_card["质量"]
            sub_card_level = sub_card["星级"]
            if int(sub_card_level) - int(main_card_level) > 2:
                base_rates.append(1)
                break
            elif int(main_card_level) - int(sub_card_level) >= 3:
                base_rates.append(0)
            else:
                base_rates.append(float(self.probability[main_card_level]["rate"][quality][sub_card_level]))
        # 找到最高概率
        highest_rate = max(base_rates)
        base_rates.remove(highest_rate)
        if base_rates:  # 如果基础概率不是空列表,就把它们/3,并加到最高概率上
            for rate in base_rates:
                highest_rate += rate / 3
        # 四叶草加成
        if clover_level != "0":
            highest_rate = highest_rate * self.probability["clover"][clover_level]
        # 总概率加成
        bonus_rate = highest_rate * self.all_bonus
        success_rate = highest_rate + bonus_rate
        if highest_rate >= 1:
            success_rate = 1
            bonus_rate = 0.2
        return success_rate, bonus_rate

    def success_check(self, success_rate: float) -> bool:
        """
        成功率检查
        :param success_rate: 成功率
        :return: 是否成功
        """
        return success_rate > random.random()

    def get_bonus(self):
        """
        获取总加成
        :return: 总加成
        """
        guild_compose_level = self.main_window.settings["强化模拟器"]["公会合成屋等级"]
        VIP_level = self.main_window.settings["强化模拟器"]["VIP等级"]
        self.all_bonus = self.guild_bonus[str(guild_compose_level)] + self.VIP_bonus[str(VIP_level)]
        # 修改文本
        self.main_window.all_bonus_label.setText(f"总强化成功率加成: {self.all_bonus * 100:.0f}%")

    def success_rate_finder(self, target_success_rate: float, max_cards: int = 1,
                            with_bonus_rate: bool = False) -> dict:
        """
        成功率查找器，给出成功率，返回最接近该成功率的主副卡配置/四叶草等级
        :param target_success_rate: 目标成功率
        :param mode: 模式,表示用几张副卡,1: 1张,2: 2张,3: 3张
        :return: 最接近该成功率的配置
        """
        closest_config = None
        closest_diff = float('inf')

        # 获取所有可能的主卡、副卡、四叶草等级组合
        main_card_levels = ["3", "4", "5", "6"]
        qualities = ['2', '0', '1']
        clover_levels = ['0', '1', '2', '3']

        # 遍历所有组合
        for main_level in main_card_levels:
            main_card = {"星级": main_level}
            sub_card_levels = list(self.probability[main_level]["rate"]["0"].keys())
            sub_card_levels.remove(str(int(main_level) + 1))
            sub_combinations = []
            # 生成1到3个副卡的组合
            for i in range(1, 1 + max_cards):
                sub_combinations.extend(itertools.product(sub_card_levels, qualities, repeat=i))
                for sub_combination in sub_combinations:
                    sub_cards = [{"星级": sub_combination[j], "质量": sub_combination[j + 1]} for j in
                                 range(0, len(sub_combination), 2)]
                    for clover_level in clover_levels:
                        success_rate, bonus_rate = self.success_rate_calculate(main_card, sub_cards, clover_level)
                        if success_rate >= 1:
                            break
                        if not with_bonus_rate:
                            success_rate -= bonus_rate
                        diff = abs(success_rate - target_success_rate)
                        if diff < closest_diff:
                            closest_diff = diff
                            closest_config = {
                                "main_card": main_card,
                                "sub_cards": sub_cards,
                                "clover_level": clover_level,
                                "success_rate": success_rate
                            }
        return closest_config

    def get_enhancement_expectation(self) -> dict:
        """
        调用强化模拟器，使用当前强化方案，实现大量卡片的强化模拟，最终获得强化结果，消耗金币，消耗四叶草数，强化总次数，强化耗时
        输入物品价格还能计算收益率
        """
        # 先获取当前强化方案，强化最高星，强化最低星。逐级将其保存成所需星级、成功率的字典
        plan = self.main_window.settings["强化方案"]
        min_level = self.main_window.min_level
        max_level = self.main_window.max_level
        # 初始化统计数据
        statistic = {
            "强化次数": 0,
            "消耗金币": 0,
            "消耗额外副卡": 0,
            "消耗四叶草": {
                "0": 0,
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "超能": 0,
                "SS": 0,
                "SSS": 0,
                "SSR": 0
            }
        }
        enhance_time = 0
        other_card = 0
        # 根据生产方案中的第一张卡，初始化卡片字典，生成包含卡片数量、卡片质量、卡片名称的字典(第二张卡自动添加，视为数量无限)
        card_names = list(self.main_window.settings["生产方案"].keys())
        card_name = card_names[0]
        card_dict = {}
        # card_dict要多一个键值对，表示最大星级的卡片
        card_dict[f"{max_level}"] = {
            "名称": card_name,
            "数量": 0
        }
        temp_dict = {}
        for i in range(max_level - 1, min_level - 1, -1):
            # 处理存储所需星级和成功率的临时字典时，也初始化卡片字典
            card_dict[f"{i}"] = {
                "名称": card_name,
                "数量": 0
            }
            need_cards = []
            cards = plan[f"{i}-{i + 1}"]
            sub_cards = []
            other_sub_card = 0
            main_card = {
                "星级": str(i)
            }
            need_cards.append(str(i))
            for j in range(3):
                sub_card_level = cards[f"副卡{j + 1}"]["星级"]
                if sub_card_level == "无":
                    continue
                sub_name = cards[f"副卡{j + 1}"]["卡片名称"]
                quality = self.main_window.card_info_dict[sub_name]
                for id, word in self.card_quality_map.items():
                    if word == quality:
                        quality = id
                        break
                sub_card = {
                    "星级": sub_card_level,
                    "质量": quality,
                }
                sub_cards.append(sub_card)
                # 如果副卡和主卡不是一种卡，对其特殊标记，在结算时单独计数
                if sub_name != card_name:
                    other_sub_card += 1
                need_cards.append((sub_card_level))
            # 处理所需卡牌，将同级的合并
            need_levels = {}
            for level in need_cards:
                if level in need_levels:
                    need_levels[level] += 1
                else:
                    need_levels[level] = 1
            clover_level = cards["四叶草"]["种类"].replace("级", "")
            if clover_level == "无":
                clover_level = "0"
            success_rate, bonus_rate = self.success_rate_calculate(main_card, sub_cards, clover_level)
            # 设置到新字典当中
            temp_dict[f"{i}-{i + 1}"] = {
                "所需星级": need_levels,
                "成功率": success_rate,
                "额外副卡": other_sub_card,
                "四叶草": clover_level
            }
        # 获取香料使用上限，初始化卡片字典里的卡片数量
        limit = self.main_window.settings["香料使用上限"]
        i = 0
        for spice, count in limit.items():
            if count == "0":
                i += 1
                continue
            card_dict[f"{i}"]["数量"] = int(count) // 5
            i += 1
        # 存储原始card_dict
        origin_card_dict = copy.deepcopy(card_dict)
        # 初始化临时等级，用来存储有用的副卡
        temp_level = {}
        # 根据强化方案，用成功率逐次强化所有卡片
        while True:
            # 新一轮开始，将临时等级再度加入到卡片字典中，并清空临时等级
            if temp_level:
                for level, count in temp_level.items():
                    card_dict[level]["数量"] += count
                temp_level = {}
            for level_to_level, info in temp_dict.items():
                enough = True
                main_level = level_to_level.split("-")[0]
                need_levels = info["所需星级"]
                success_rate = info["成功率"]
                other_sub_card = info["额外副卡"]
                # 先检查是否有卡片可以强化
                if card_dict[main_level]["数量"] < 1:
                    enough = False
                    continue
                for level, count in need_levels.items():
                    sub_card_count = card_dict[level]["数量"]
                    if count > sub_card_count:
                        enough = False
                        # 当存在相应副卡，却不足够时，将相应副卡存入临时等级中
                        if sub_card_count > 0:
                            card_dict[level]["数量"] -= sub_card_count
                            if level in temp_level:
                                temp_level[level] += sub_card_count
                            else:
                                temp_level[level] = sub_card_count
                        break
                # 无卡片可强化，跳过当前等级，保留住高等级卡片
                if not enough:
                    continue
                # 统计四叶草消耗
                if info["四叶草"] != "0":
                    statistic["消耗四叶草"][info["四叶草"]] += 1
                # 强化一次卡片
                if self.success_check(success_rate):
                    # 强化成功，主卡+1星
                    card_dict[str(int(main_level) + 1)]["数量"] += 1
                else:
                    # 强化失败，根据主卡等级判断，>=6星时主卡-1星，其余不变
                    if int(main_level) >= 6:
                        card_dict[str(int(main_level) - 1)]["数量"] += 1
                    else:
                        card_dict[main_level]["数量"] += 1
                # 统计金币消耗
                statistic["消耗金币"] += self.main_window.gold_cost_map["主卡等级"][main_level]
                # 单次强化完成，抛去所有副卡，进行下一次强化(不抛去额外副卡，单独计数)
                for level, count in need_levels.items():
                    if other_sub_card > 0:
                        count -= other_sub_card
                        other_card += 1
                    card_dict[level]["数量"] -= count
                # 强化次数+1，跳出循环
                enhance_time += 1
                break
            else:
                break
        # 如果所有等级的强化方案均被跳过，说明无卡片可强了，把临时等级加回去，输出最后的强化字典结果
        for level, count in temp_level.items():
            card_dict[level]["数量"] += count
        print(card_dict)
        statistic["强化次数"] += enhance_time
        statistic["消耗额外副卡"] += other_card

        # 先获取这次强化的成本
        cost_dict = {}
        for level, card in origin_card_dict.items():
            if card["数量"] > 0:
                cost_dict[level] = {
                    "数量": card["数量"],
                    "名称": card["名称"]
                                    }
        print(cost_dict)
        cost_total,net_profit,gold_cost,time_spend = self.earning_rate_message(
            cost_dict=cost_dict, card_dict=card_dict, statistic=statistic)

        # 根据价格，输出总收益率和收益期望
        self.widget = QWidgetWebExpectation(
            cost_total=cost_total,net_profit=net_profit, gold_cost=gold_cost,time_spend=time_spend)
        self.widget.show()

    def earning_rate_message(self, cost_dict: dict, card_dict: dict, statistic: dict):
        """
        显示成本与最终收益，并计算总收益率和收益期望
        cost_dict = {
            "level": {"名称": str, "数量": int},
        }
        """
        price_dict = self.main_window.settings["物价"]
        cost_total = 0
        profit_total = 0

        # 计算成本 - 来自合成前
        for level, cards in cost_dict.items():
            card_quality = self.main_window.card_info_dict[cards["名称"]]
            if int(level) <= 5:
                cost_total += price_dict[f"{card_quality}卡套"] * cards["数量"]
                match int(level):
                    case 1:
                        cost_total += price_dict[f"天然香料"] * 5 * cards["数量"]
                    case 2:
                        cost_total += price_dict[f"上等香料"] * 5 * cards["数量"]
                    case 3:
                        cost_total += price_dict[f"秘制香料"] * 5 * cards["数量"]
                    case 4:
                        cost_total += price_dict[f"极品香料"] * 5 * cards["数量"]
                    case 5:
                        cost_total += price_dict[f"皇室香料"] * 5 * cards["数量"]
            else:
                cost_total += price_dict[f'{level}星卡'] * cards["数量"]

        # 计算成本 - 四叶草
        for level, num in statistic["消耗四叶草"].items():
            if num == 0:
                continue
            if level in ["超能", "SS", "SSS", "SSR"]:
                clover = f"{level}四叶草"
            else:
                clover = f"{level}级四叶草"
            cost_total += price_dict[clover] * num

        cost_total += price_dict["好卡卡套"] * statistic["消耗额外副卡"]

        # 计算收益
        for level, cards in card_dict.items():
            card_quality = self.main_window.card_info_dict[cards["名称"]]
            if int(level) <= 5:
                profit_total += price_dict[f"{card_quality}卡套"] * cards["数量"]
                match int(level):
                    case 1:
                        profit_total += price_dict[f"天然香料"] * 5 * cards["数量"]
                    case 2:
                        profit_total += price_dict[f"上等香料"] * 5 * cards["数量"]
                    case 3:
                        profit_total += price_dict[f"秘制香料"] * 5 * cards["数量"]
                    case 4:
                        profit_total += price_dict[f"极品香料"] * 5 * cards["数量"]
                    case 5:
                        profit_total += price_dict[f"皇室香料"] * 5 * cards["数量"]
            else:
                profit_total += price_dict[f'{level}星卡'] * cards["数量"]

        # 净利润
        net_profit = profit_total - cost_total

        # 消耗金币
        gold_cost = statistic['消耗金币']

        # 强化时间 秒 估算
        time_spend = f'{statistic["强化次数"] * 2 / 3600:.2f}h'

        return cost_total,net_profit,gold_cost,time_spend

    def delete_slot(self, name: str):
        """
        删除槽位
        :param name: 槽位名
        """
        if name == "main_card_slot":
            self.simulator_cards.pop("0", None)
        elif name == "sub_card_slot_1":
            self.simulator_cards.pop("1", None)
        elif name == "sub_card_slot_2":
            self.simulator_cards.pop("2", None)
        elif name == "sub_card_slot_3":
            self.simulator_cards.pop("3", None)
        elif name == "clover_slot":
            self.simulator_clover_level = "0"
        # 删完后刷新UI
        self.refresh_ui()

    def clover_changed(self):
        """
        四叶草等级改变
        :param clover_level: 四叶草等级
        """
        # 获取四叶草文本
        clover_level = self.main_window.clover_select_box.currentText()
        # 去掉等级的四叶草文本
        clover_level = clover_level.replace("四叶草", "")
        # 去掉等级的级文本
        clover_level = clover_level.replace("级", "")
        self.simulator_clover_level = clover_level
        # 刷新UI
        self.refresh_ui()

    def refresh_ui(self):
        """
        根据模拟器卡片配置，刷新模拟器的GUI
        """
        if not self.simulator_cards:
            # 不存在，就删除所有文本，但是可以更新一下四叶草显示
            self.main_window.clover_slot.setText(self.clover_level_map[self.simulator_clover_level])
            # 禁用强化按钮
            self.main_window.enhance_btn.setEnabled(False)
            # 保险金清零
            self.main_window.insurance.setText("0")
            self.main_window.gold_need.setText("需金币:")
            for id in ["0", "1", "2", "3"]:
                if id == "0":
                    self.main_window.main_card_level.setText("")
                    self.main_window.main_card_quality.setText("")
                else:
                    sub_card_level = getattr(self.main_window, "sub_card_level_" + str(id))
                    sub_card_quality = getattr(self.main_window, "sub_card_quality_" + str(id))
                    sub_card_level.setText("")
                    sub_card_quality.setText("")
            return
        # 更新GUI的卡片显示
        for id, card in self.simulator_cards.items():
            if id == "0":
                self.main_window.main_card_level.setText(" " + card["星级"] + "☆")
                self.main_window.main_card_quality.setText(self.card_quality_map[card["质量"]])
            else:
                # 创建对象名
                sub_card_level = getattr(self.main_window, "sub_card_level_" + str(id))
                sub_card_quality = getattr(self.main_window, "sub_card_quality_" + str(id))
                # 设置对象值
                sub_card_level.setText(" " + card["星级"] + "☆")
                sub_card_quality.setText(self.card_quality_map[card["质量"]])
        # 如果字典里没有对应卡片，就删除对应位置的文本
        for id in ["0", "1", "2", "3"]:
            if id in self.simulator_cards:
                continue
            if id == "0":
                self.main_window.main_card_level.setText("")
                self.main_window.main_card_quality.setText("")
            else:
                sub_card_level = getattr(self.main_window, "sub_card_level_" + str(id))
                sub_card_quality = getattr(self.main_window, "sub_card_quality_" + str(id))
                sub_card_level.setText("")
                sub_card_quality.setText("")
        # 更新四叶草显示
        self.main_window.clover_slot.setText(self.clover_level_map[self.simulator_clover_level])
        # 根据主卡等级，改变保险金,需金币,副卡星级选框
        if self.simulator_cards.get("0", None):
            main_card_level = self.simulator_cards["0"]["星级"]
            insurance = self.probability[main_card_level]["insurance"]
            gold_need = self.probability[main_card_level]["gold"]
            self.main_window.insurance.setText(str(insurance))
            self.main_window.gold_need.setText("需金币:" + gold_need)
            # 刷新副卡星级选框
            sub_card_levels = list(self.probability[main_card_level]["rate"]["0"].keys())
            for i in range(1, 4):
                sub_card_level_box = getattr(self.main_window, "sub_card_level_box_" + str(i))
                sub_card_level_box.clear()
                for level in sub_card_levels:
                    sub_card_level_box.addItem(level)
        else:
            self.main_window.insurance.setText("0")
            self.main_window.gold_need.setText("需金币:")
        # 同时存在主卡和至少一张副卡时，刷新成功率显示
        if self.simulator_cards.get("0", None) and len(self.simulator_cards.keys()) >= 2:
            sub_cards = [self.simulator_cards[id] for id in self.simulator_cards.keys() if id != "0"]
            main_card = self.simulator_cards["0"]
            success_rate, bonus_rate = self.success_rate_calculate(main_card, sub_cards, self.simulator_clover_level)
            if success_rate == 1:
                without_bonus_rate = 1
            else:
                without_bonus_rate = success_rate - bonus_rate
            self.cyber_success_rate = success_rate
            self.main_window.success_rate.setText(f"成功率:{without_bonus_rate:.2%}+{bonus_rate:.2%}")
            # 启用强化按钮
            self.main_window.enhance_btn.setEnabled(True)
        else:
            # 禁用强化按钮
            self.main_window.enhance_btn.setEnabled(False)
            self.main_window.success_rate.setText("成功率:")
            self.cyber_success_rate = 0

    def cyber_enhance(self):
        """
        赛博强化，虚拟上卡
        """
        success = self.success_check(self.cyber_success_rate)
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        if success:
            # 主卡等级+1，副卡消失
            self.simulator_cards["0"]["星级"] = str(int(self.simulator_cards["0"]["星级"]) + 1)
            # 如果主卡等级是16，那主卡也消失
            if self.simulator_cards["0"]["星级"] == "16":
                self.simulator_cards.pop("0", None)
            self.simulator_cards.pop("1", None)
            self.simulator_cards.pop("2", None)
            self.simulator_cards.pop("3", None)
            # 编辑窗口
            msg.setWindowTitle("喜悦的消息")
            msg.setText("物品强化成功,您可以到物品栏查看该卡的属性")
            ok_button = msg.button(QMessageBox.StandardButton.Ok)
            ok_button.setText("好耶")
        else:
            if self.main_window.insurance_check.isChecked():
                # 有保险，编辑窗口
                msg.setWindowTitle("预期中的消息")
                msg.setText("不够好运,升级失败")
                ok_button = msg.button(QMessageBox.StandardButton.Ok)
                ok_button.setText("呜呜呜")
            else:
                # 无保险，编辑窗口
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setText("不够好运,升级失败")
                msg.setWindowTitle("悲伤的消息")
                ok_button = msg.button(QMessageBox.StandardButton.Ok)
                ok_button.setText("伤心")
                # 检查主卡等级
                if int(self.simulator_cards["0"]["星级"]) > 5:
                    # 高于五级就降一级
                    self.simulator_cards["0"]["星级"] = str(int(self.simulator_cards["0"]["星级"]) - 1)
                # 清空副卡
                self.simulator_cards.pop("1", None)
                self.simulator_cards.pop("2", None)
                self.simulator_cards.pop("3", None)
        msg.exec()
        # 刷新UI
        self.refresh_ui()
