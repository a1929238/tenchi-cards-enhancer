from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, Qt, QTime
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
import re
import numpy as np

from module.core.CardProducer import produce_card
from module.core.LevelCheck import check_card_enhance_result
from module.core.PositionCheck import change_position, check_position
from module.globals import GLOBALS
from module.globals.EventManager import event_manager
from module.statistic.AsyncProduceStatistic import produce_recorder

if TYPE_CHECKING:
    from TenchiCardEnhancer import TenchiCardsEnhancer


# 自动垫卡
class AutoCushion:
    # 自动垫卡分为几步：1.强化成功率计算器，找到相等的成功几率 2.选择卡片配方 3.自行选择多种规律 4.进行自动制卡跟垫卡，出现任意一种规律后停止
    def __init__(self, enhancer: TenchiCardsEnhancer):
        # 实例化主窗口
        self.enhancer = enhancer
        # 初始化变量
        self.cushion_rules = []
        self.cushion_list_rules = []
        self.results = []
        self.cushion_card_dict = {}
        self.cushion_produce_dict = {}
        # 初始化垫卡线程
        self.cushion_thread = None
        # 禁用垫卡按钮
        self.enhancer.start_cushion_btn.setEnabled(False)
        # 初始化结果表格
        self.init_result_table()
        # 读取已有的目标规律
        self.read_cushion_rules()
        # 读取已有的垫卡方案
        self.read_cushion_card_dict()

    def add_rules(self):
        """
        根据用户输入的规律，添加规律，保存为两种形式的规律：用于数组匹配的布尔数组规律，用于保存的列表规律
        """
        times = int(self.enhancer.rule_times_box.currentText())
        failed_times = int(self.enhancer.failed_times_box.currentText())
        success_times = int(self.enhancer.success_times_box.currentText())
        # 没有选择就不添加
        if failed_times == 0 and success_times == 0:
            return
        # 将规律处理为布尔数组
        rule = self.get_rule_bool_list(times, failed_times, success_times)
        self.cushion_rules.append(rule)  # 在变量中保存规律
        # 获取规律文本
        text = self.get_rule_text(times, failed_times, success_times)
        # 在列表中添加规律
        self.enhancer.target_rule_list.addItem(text)

        # 准备用于保存的列表规律
        list_rule = [times, failed_times, success_times]
        self.cushion_list_rules.append(list_rule)

        # 保存规律
        self.save_cushion_rules()

    def get_rule_text(self, times, failed_times, success_times):
        """
        根据规律，返回规律文本
        """
        # 处理规律
        if times == 1:
            text = "单次"
        else:
            text = f"连续{times}次"
        if failed_times == 0:
            text += f"{success_times}连成"
        elif success_times == 0:
            text += f"{failed_times}连败"
        else:
            text += f"{failed_times}败{success_times}成"
        return text

    def get_rule_bool_list(self, times, failed_times, success_times):
        """
        将规律转化为布尔数组
        """
        rule = []
        for time in range(times):
            if failed_times:
                for failed_time in range(failed_times):
                    rule.append(False)
            if success_times:
                for success_time in range(success_times):
                    rule.append(True)
        return rule

    def delete_rule(self):
        """
        删除当前选择的规律
        """
        # 如果列表是空的，则不删除
        if not self.cushion_list_rules:
            return
        rule_list = self.enhancer.target_rule_list
        # 获取当前选择的规律
        current_row = rule_list.currentRow()
        rule_list.takeItem(current_row)
        # 删掉变量里的规律
        self.cushion_rules.pop(current_row)
        self.cushion_list_rules.pop(current_row)
        # 保存规律
        self.save_cushion_rules()

    def init_result_table(self):
        """
        初始化结果表格,表格为五行十列的表格，拥有红色，绿色和没颜色三种颜色
        """
        table = self.enhancer.result_table
        # 初始化表格内容
        for i in range(5):
            for j in range(10):
                item = QTableWidgetItem()
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # Make cell non-editable
                table.setItem(i, j, item)

    def update_result_table(self):
        # 只记录最近50个结果
        results = self.results[-50:]
        table = self.enhancer.result_table

        for index, result in enumerate(results):
            row = index // table.columnCount()
            column = index % table.columnCount()

            item = QTableWidgetItem()
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # Make cell non-editable

            if result:
                item.setBackground(QColor('green'))
            else:
                item.setBackground(QColor('red'))

            table.setItem(row, column, item)

    def update_result_list(self, result):
        """
        根据最新的结果，更新结果列表，如果最后一个结果与上一个结果不同，如果是失败，则增加一个item，如果是成功，则更新最后一个item。相同则更新最后一个item
        结果列表有三种结果：X连成，X连败，X败X成
        """
        # 获取结果列表
        result_list = self.enhancer.result_list
        # 获取最后一个item的文本（如果存在）
        last_item_text = result_list.item(result_list.count() - 1).text() if result_list.count() > 0 else ""

        # 解析最后一个item的文本
        if last_item_text:
            if "连成" in last_item_text:
                last_result = 0
                count = int(last_item_text.replace("连成", ""))
            elif "连败" in last_item_text:
                last_result = 1
                count = int(last_item_text.replace("连败", ""))
            elif "败" in last_item_text and "成" in last_item_text:
                last_result = 2
                numbers = re.findall(r'\d+', last_item_text)
                numbers = [int(num) for num in numbers]
        else:
            last_result = None
            count = 0

        # 更新或添加item
        if last_result == 0:
            if result:
                # 结果相同，更新最后一个item
                count += 1
                new_text = f"{count}连成"
                result_list.takeItem(result_list.count() - 1)
            else:
                # 结果不同，添加新item
                new_text = "1连败"
        elif last_result == 1:
            if result:
                # 连败后成，改名为X败1成
                new_text = f"{count}败1成"
                result_list.takeItem(result_list.count() - 1)
            else:
                # 还是连败
                count += 1
                new_text = f"{count}连败"
                result_list.takeItem(result_list.count() - 1)
        elif last_result == 2:
            if result:
                # 增加成数
                new_text = f"{numbers[0]}败{numbers[1] + 1}成"
                result_list.takeItem(result_list.count() - 1)
            else:
                # 添加新item
                new_text = f"1连败"
        else:
            # 结果不同，添加新item
            new_text = f"1连{'成' if result else '败'}"

        result_list.addItem(new_text)

    def result_check(self):
        """
        检查目标规律有没有在规律中出现
        """
        # 只检查最近的50条规律
        results = self.results[-50:]
        results = np.array(results)
        for rule in self.cushion_rules:
            if rule[0] == False and True in results:
                rule.insert(0, True)
            rule = np.array(rule)
            len1 = results.size
            len2 = rule.size
            if len2 > len1:
                continue
            # 遍历第一个数组，使用滑动窗口比较
            for i in range(len1 - len2 + 1):
                if np.array_equal(results[i:i + len2], rule):
                    return True
        return False

    def clear_result(self):
        """
        清空已有结果规律列表，清空结果规律表格
        """
        self.results = []
        self.enhancer.result_list.clear()
        self.enhancer.result_table.clearContents()

    def auto_cushion(self):
        """
        自动垫卡，独立于强卡器
        """
        # 重置垫卡方案字典，垫卡生产方案字典
        self.cushion_card_dict = {}
        self.cushion_produce_list = []
        # 读取控件，获得垫卡方案字典，传入强化字典中
        # 主卡部分
        main_card_name = self.enhancer.cushion_main_card_box.currentText()
        main_card_level = self.enhancer.cushion_main_card_level.text().replace("星", "")
        main_card_bind = self.enhancer.cushion_main_card_bind_check.isChecked()
        self.cushion_card_dict["主卡"] = {
            "卡片名称": main_card_name,
            "星级": main_card_level,
            "绑定": main_card_bind,
        }
        # 副卡部分
        for i in range(1, 4):
            sub_card_name_box = getattr(self.enhancer, f"cushion_sub_card_box_{i}")
            sub_card_level_label = getattr(self.enhancer, f"cushion_sub_card_level_{i}")
            sub_card_bind_check = getattr(self.enhancer, f"cushion_sub_card_bind_check_{i}")
            sub_card_name = sub_card_name_box.currentText()
            if sub_card_name == "":
                sub_card_name = "无"
            sub_card_level = sub_card_level_label.text().split("星")[0]
            sub_card_bind = sub_card_bind_check.isChecked()
            self.cushion_card_dict[f"副卡{i}"] = {
                "卡片名称": sub_card_name,
                "星级": sub_card_level,
                "绑定": sub_card_bind,
            }
        # 四叶草部分
        clover_level = self.enhancer.cushion_clover_level.text().replace("四叶草", "")
        clover_bind = self.enhancer.cushion_clover_bind_check.isChecked()
        self.cushion_card_dict["四叶草"] = {
            "种类": clover_level,
            "绑定": clover_bind,
        }
        # 深拷贝原强化方案，将其中的一级设置为垫卡强化方案
        enhance_plan = copy.deepcopy(self.enhancer.settings["强化方案"])
        enhance_plan[f"{int(main_card_level)}-{int(main_card_level) + 1}"] = self.cushion_card_dict
        # 根据垫卡方案，设置垫卡生产方案
        cushion_produce_list = [{
            "名称": main_card_name,
            "使用香料": int(main_card_level),
            "绑定": main_card_bind
        }]
        for i in range(1, 4):
            sub_card_name = self.cushion_card_dict[f"副卡{i}"]["卡片名称"]
            if sub_card_name == "无":
                continue
            sub_card_level = self.cushion_card_dict[f"副卡{i}"]["星级"]
            sub_card_bind = self.cushion_card_dict[f"副卡{i}"]["绑定"]
            cushion_produce_list.append({
                "名称": sub_card_name,
                "使用香料": int(sub_card_level),
                "绑定": sub_card_bind
            })
        # 保存目前的垫卡方案
        self.save_cushion_card_dict()
        # 实例化垫卡线程
        self.cushion_thread = CushionThread(self.enhancer, enhance_plan, cushion_produce_list)
        # 开始重复进行强化-制卡，并存储结果，结果链条一旦匹配到停止字符串，则停止，并通知
        self.enhancer.is_running = True
        GLOBALS.IS_RUNNING = True
        # 禁止垫卡按钮，允许停止按钮
        self.enhancer.start_cushion_btn.setEnabled(False)
        self.enhancer.stopbtn.setEnabled(True)
        # 启动线程
        self.cushion_thread.start_loop()

    def get_result(self, target_level):
        """
        获取垫卡结果
        """
        # 获取结果
        result = check_card_enhance_result(int(target_level))
        # 将结果添加到结果列表中
        self.results.append(result)
        # 更新结果列表
        self.update_result_list(result)
        # 更新结果表格
        self.update_result_table()
        # 检查结果是否符合规律
        if self.result_check():
            self.enhancer.show_dialog_signal.emit("登登！", "垫卡结果已符合规律，快强化！")

    def find_combination(self):
        """
        按照用户输入，寻找出对应成功率的卡片组合
        """
        # 获取目标成功率
        target_success_rate = self.enhancer.target_success_rate_input.value() / 100
        # 获取目标成功率是否算上加成
        with_bonus_rate = self.enhancer.with_bonus_rate_check.isChecked()
        # 获取最多使用副卡数量
        max_sub_cards = int(self.enhancer.max_sub_cards_box.currentText())
        # 获取最接近成功率组合
        nearest_combination = self.enhancer.enhance_simulator.success_rate_finder(target_success_rate, max_sub_cards,
                                                                                  with_bonus_rate)
        for key, value in nearest_combination.items():
            match key:
                case "main_card":
                    main_card_level = value["星级"]
                case "sub_cards":
                    sub_card_text = ""
                    index = 1
                    for sub_card in value:
                        sub_card_level = sub_card["星级"]
                        sub_card_quality = self.enhancer.enhance_simulator.card_quality_map[sub_card["质量"]]
                        sub_card_text += f"副卡{index}:{sub_card_level}星{sub_card_quality}  "
                        index += 1
                case "clover_level":
                    clover_level = self.enhancer.enhance_simulator.clover_level_map[value]
                case "success_rate":
                    success_rate = value
        # 发出弹窗，提示找到的组合
        QMessageBox.information(self.enhancer, "成功率查找器",
                                f"最接近目标成功率的组合为：\n主卡:{main_card_level}星\n{sub_card_text}\n四叶草等级:{clover_level} \n成功率:{success_rate:.2%}")
        # 刷新UI
        # 主卡部分
        self.enhancer.cushion_main_card_level.setText(f"{main_card_level}星")
        self.enhancer.init_recipe_box(self.enhancer.cushion_main_card_box, need_suffix=False)
        # 副卡部分，先根据长度，将一些空的副卡设置为无
        sub_card_count = len(nearest_combination["sub_cards"])
        for i in range(3, sub_card_count, -1):
            level_label = getattr(self.enhancer, f"cushion_sub_card_level_{i}")
            box = getattr(self.enhancer, f"cushion_sub_card_box_{i}")
            level_label.setText("无")
            box.clear()
        # 为存在的副卡设置对应的星级和卡片
        for i in range(1, sub_card_count + 1):
            sub_card = nearest_combination["sub_cards"][i - 1]
            sub_card_quality = self.enhancer.enhance_simulator.card_quality_map[sub_card["质量"]]
            level_label = getattr(self.enhancer, f"cushion_sub_card_level_{i}")
            box = getattr(self.enhancer, f"cushion_sub_card_box_{i}")
            box.clear()
            level_label.setText(f"{sub_card['星级']}星{sub_card_quality}")
            # 设置对应质量的卡片选择框
            self.enhancer.init_recipe_box(box, filter_word=sub_card_quality, need_suffix=False)
        # 四叶草部分
        self.enhancer.cushion_clover_level.setText(clover_level)
        # 成功率部分
        self.enhancer.success_rate_label.setText(f"成功率:{success_rate:.2%}")
        # 保存目前方案成功率
        self.enhancer.settings["自动垫卡"]["方案成功率"] = success_rate
        self.enhancer.save_settings(self.enhancer.settings)

    def save_cushion_card_dict(self):
        """
        保存垫卡方案
        """
        self.enhancer.settings["自动垫卡"]["垫卡方案"] = self.cushion_card_dict
        self.enhancer.save_settings(self.enhancer.settings)

    def save_cushion_rules(self):
        """
        保存目标规律的列表版
        """
        self.enhancer.settings["自动垫卡"]["目标规律"] = self.cushion_list_rules
        self.enhancer.save_settings(self.enhancer.settings)

    def read_cushion_rules(self):
        """
        读取垫卡规律
        """
        self.cushion_list_rules = self.enhancer.settings["自动垫卡"]["目标规律"]
        if not self.cushion_list_rules:
            return
        # 读取每一个规律，将它们加入到规律列表与列表控件中
        for rule in self.cushion_list_rules:
            times = rule[0]
            failed_times = rule[1]
            success_times = rule[2]
            target_rule = self.get_rule_bool_list(times, failed_times, success_times)
            self.cushion_rules.append(target_rule)  # 在变量中保存规律
            text = self.get_rule_text(times, failed_times, success_times)
            # 在列表控件中添加规律
            self.enhancer.target_rule_list.addItem(text)

    def read_cushion_card_dict(self):
        """
        读取已有的垫卡方案
        """
        self.cushion_card_dict = self.enhancer.settings["自动垫卡"]["垫卡方案"]
        if not self.cushion_card_dict:
            return
        success_rate = self.enhancer.settings["自动垫卡"]["方案成功率"]
        # 根据垫卡方案，初始化GUI
        # 主卡部分
        self.enhancer.cushion_main_card_level.setText(f"{self.cushion_card_dict['主卡']['星级']}星")
        self.enhancer.cushion_main_card_bind_check.setChecked(self.cushion_card_dict["主卡"]["绑定"])
        self.enhancer.init_recipe_box(self.enhancer.cushion_main_card_box, need_suffix=False)
        # 根据主卡名，改变box的索引
        index = self.enhancer.cushion_main_card_box.findText(self.cushion_card_dict["主卡"]["卡片名称"])
        if index != -1:
            self.enhancer.cushion_main_card_box.setCurrentIndex(index)
        # 副卡部分，先获取一共有几张副卡
        sub_card_count = 0
        for i in range(1, 4):
            if self.cushion_card_dict[f"副卡{i}"]["卡片名称"] != "无":
                sub_card_count += 1
        for i in range(3, sub_card_count, -1):
            level_label = getattr(self.enhancer, f"cushion_sub_card_level_{i}")
            box = getattr(self.enhancer, f"cushion_sub_card_box_{i}")
            level_label.setText("无")
            box.clear()
        # 为存在的副卡设置对应的星级和卡片
        for i in range(1, sub_card_count + 1):
            sub_card = self.cushion_card_dict[f"副卡{i}"]
            sub_card_quality = self.enhancer.card_info_dict[sub_card["卡片名称"]]  # 把名称映射为质量
            level_label = getattr(self.enhancer, f"cushion_sub_card_level_{i}")
            box = getattr(self.enhancer, f"cushion_sub_card_box_{i}")
            box.clear()
            level_label.setText(f"{sub_card['星级']}星{sub_card_quality}")
            # 设置对应质量的卡片选择框
            self.enhancer.init_recipe_box(box, filter_word=sub_card_quality, need_suffix=False)
            # 改变选择框索引
            index = box.findText(sub_card["卡片名称"])
            if index != -1:
                box.setCurrentIndex(index)
            # 设置副卡的绑定
            bind_check = getattr(self.enhancer, f"cushion_sub_card_bind_check_{i}")
            bind_check.setChecked(sub_card["绑定"])
        # 四叶草部分
        self.enhancer.cushion_clover_level.setText(f"{self.cushion_card_dict['四叶草']['种类']}四叶草")
        self.enhancer.cushion_clover_bind_check.setChecked(self.cushion_card_dict["四叶草"]["绑定"])
        # 成功率部分
        self.enhancer.success_rate_label.setText(f"成功率:{success_rate:.2%}")


class CushionThread(QThread):
    """
    垫卡线程，类似于强化线程，但是既不刷新，也不退出合成屋
    """

    def __init__(self, enhancer: TenchiCardsEnhancer, enhance_plan, cushion_produce_list):
        super().__init__()
        self.enhancer = enhancer
        self.enhance_plan = enhance_plan
        self.cushion_produce_list = cushion_produce_list

    def run(self):
        # 检查目前位置
        if not self.init_position():
            # 垫卡结束
            self.enhancer.start_cushion_btn.setEnabled(True)
            return
        while self.enhancer.is_running:
            # 制卡
            for card_dict in self.cushion_produce_list:
                name = card_dict["名称"]
                level = card_dict["使用香料"]
                bind = card_dict["绑定"]
                card_pack_dict = self.enhancer.settings["卡包配置"]
                produce_check_interval = int(self.enhancer.settings["个人设置"]["制卡检测间隔"])

                actual_count, actual_card_name = produce_card(name, level, bind,
                                                              7, card_pack_dict, produce_check_interval)
                if actual_count == 0:
                    continue
                # 记录制卡数据
                bind_str = "绑定" if bind else "不绑"
                produce_recorder.save_produce_statistic(bind, level, actual_count)
                event_manager.log_signal.emit(
                    f"<font color='blue'>[{QTime.currentTime().toString()}]"
                    f"为垫卡制卡{bind_str}{level}星{actual_card_name}{actual_count}次</font>"
                )
            if not self.enhancer.is_running:
                break
            # 制卡完成后，切换到强化页面
            change_position("卡片强化", "卡片制作")
            # 开始垫卡
            self.enhancer.main_enhancer(enhance_plan=self.enhance_plan)
            if not self.enhancer.is_running:
                break
            # 垫卡完成后，切换到制作页面，再次循环
            change_position("卡片制作", "卡片强化")
        # 垫卡结束，允许垫卡开始按钮
        self.enhancer.start_cushion_btn.setEnabled(True)

    def init_position(self):
        """
        初始化目前位置，垫卡特殊，只有处于合成屋时才会开始
        """
        position = check_position()  # 获取位置标识
        if position == "卡片制作":  # 处于制作页面
            return True  # 开始垫卡循环
        elif position == "卡片强化":  # 处于强化页面
            self.enhancer.main_enhancer(single_plan=self.cushion_card_dict)  # 进行一轮垫卡
            if not self.enhancer.is_running:
                return False  # 说明直接出结果了，返回
            # 点击卡片制作，进入垫卡循环
            change_position("卡片制作", "卡片强化")
            return True
        else:
            # 未知位置，弹窗提示
            self.enhancer.show_dialog_signal.emit("咳咳", "请进入合成屋再点我")
            return False  # 不处于制作页面，不进行垫卡循环

    def start_loop(self):
        self.start()
