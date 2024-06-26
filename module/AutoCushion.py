from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox

# 自动垫卡
class AutoCushion():
    # 自动垫卡分为几步：1.强化成功率计算器，找到相等的成功几率 2.选择卡片配方 3.自行选择多种规律 4.进行自动制卡跟垫卡，出现任意一种规律后停止
    def __init__(self, main_window):
        # 实例化主窗口
        self.main_window = main_window
        # 初始化变量
        self.cushion_rules = []
        self.results = []
        self.cushion_card_dict = {}
        self.cushion_produce_dict = {}
        # 初始化垫卡线程
        self.cushion_thread = None
        # 初始化结果表格
        self.init_result_table()
        

    def add_rules(self):
        """
        根据用户输入的规律，添加规律
        """
        times = int(self.main_window.rule_times_box.currentText())
        failed_times = int(self.main_window.failed_times_box.currentText())
        success_times = int(self.main_window.success_times_box.currentText())
        # 没有选择就不添加
        if failed_times == 0 and success_times == 0:
            return
        self.cushion_rules.append((times, failed_times, success_times)) # 在变量中保存规律
        
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
        # 在列表中添加规律
        self.main_window.target_rule_list.addItem(text)
    
    def delete_rule(self):
        """
        删除当前选择的规律
        """
        rule_list = self.main_window.target_rule_list
        rule_list.takeItem(rule_list.currentRow())

    def init_result_table(self):
        """
        初始化结果表格,表格为五行十列的表格，拥有红色，绿色和没颜色三种颜色
        """
        table = self.main_window.result_table
        # 初始化表格内容
        # for i in range(5):
        #     for j in range(10):
        #         item = QTableWidgetItem()
        #         item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # Make cell non-editable
        #         item.setBackground(QColor('white'))
        #         table.setItem(i, j, item)


    def update_result_table(self):
        # 只记录最近50个结果
        results = self.results[-50:]
        
        for index, result in enumerate(results):
            row = index // self.table_widget.columnCount()
            column = index % self.table_widget.columnCount()
            
            item = QTableWidgetItem()
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)  # Make cell non-editable
            
            if result:
                item.setBackground(QColor('green'))
            else:
                item.setBackground(QColor('red'))
                
            self.table_widget.setItem(row, column, item)
    
    def update_result_list(self):

        pass

    def result_check(self):
        pass

    def auto_cushion(self):
        """
        自动垫卡，独立于强卡器
        """
        # 重置垫卡方案字典，垫卡生产方案字典
        self.cushion_card_dict = {}
        self.cushion_produce_list = []
        # 读取控件，获得垫卡方案字典，传入强化字典中
        # 主卡部分
        main_card_name = self.main_window.cushion_main_card_box.currentText()
        main_card_level = self.main_window.cushion_main_card_level.text().replace("星", "")
        main_card_bind = self.main_window.cushion_main_card_bind_check.isChecked()
        self.cushion_card_dict["主卡"] = {
            "卡片名称": main_card_name,
            "星级": main_card_level,
            "绑定": main_card_bind,
        }
        # 副卡部分
        for i in range(1, 4):
            sub_card_name_box = getattr(self.main_window, f"cushion_sub_card_box_{i}")
            sub_card_level_label = getattr(self.main_window, f"cushion_sub_card_level_{i}")
            sub_card_bind_check = getattr(self.main_window, f"cushion_sub_card_bind_check_{i}")
            sub_card_name = sub_card_name_box.currentText()
            sub_card_level = sub_card_level_label.text().split("星")[0]
            sub_card_bind = sub_card_bind_check.isChecked()
            self.cushion_card_dict[f"副卡{i}"] = {
                "卡片名称": sub_card_name,
                "星级": sub_card_level,
                "绑定": sub_card_bind,
            }
        # 四叶草部分
        clover_level = self.main_window.cushion_clover_level.text().replace("四叶草", "")
        clover_bind = self.main_window.cushion_clover_bind_check.isChecked()
        self.cushion_card_dict["四叶草"] = {
            "种类": clover_level,
            "绑定": clover_bind,
        }
        # 根据垫卡方案，设置垫卡生产方案
        spice_list = list(self.main_window.spice_dict.keys())
        self.cushion_produce_list = [{
            "名称": main_card_name,
            "使用香料": spice_list[int(main_card_level)],
            "绑定": main_card_bind
        }]
        for i in range(1, 4):
            sub_card_name = self.cushion_card_dict[f"副卡{i}"]["卡片名称"]
            if sub_card_name == "无":
                continue
            sub_card_level = self.cushion_card_dict[f"副卡{i}"]["星级"]
            sub_card_bind = self.cushion_card_dict[f"副卡{i}"]["绑定"]
            self.cushion_produce_list.append({
                "名称": sub_card_name,
                "使用香料": int(sub_card_level),
                "绑定": sub_card_bind
            })
        # 实例化垫卡线程
        self.cushion_thread = CushionThread(self.main_window, self.cushion_card_dict, self.cushion_produce_list)
        # 重复进行强化-制卡，并存储结果，结果链条一旦匹配到停止字符串，则停止，并通知
        
    def get_result(self, target_level):
        """
        获取垫卡结果
        """
        # 获取结果
        result = self.main_window.check_enhance_result(target_level, result_bind=None, need_record=False)
        # 将结果添加到结果列表中
        self.results.append(result)
        # 更新结果列表
        self.update_result_list()
        # 更新结果表格
        self.update_result_table()
        # 检查结果是否符合规律
        self.result_check()
    
    def find_combination(self):
        """
        按照用户输入，寻找出对应成功率的卡片组合
        """
        # 获取目标成功率
        target_success_rate = self.main_window.target_success_rate_input.value() / 100
        # 获取目标成功率是否算上加成
        with_bonus_rate = self.main_window.with_bonus_rate_check.isChecked()
        # 获取最多使用副卡数量
        max_sub_cards = int(self.main_window.max_sub_cards_box.currentText())
        # 获取最接近成功率组合
        nearest_combination = self.main_window.enhance_simulator.success_rate_finder(target_success_rate, max_sub_cards, with_bonus_rate)
        for key, value in nearest_combination.items():
            match key:
                case "main_card":
                    main_card_level = value["星级"]
                case "sub_cards":
                    sub_card_text = ""
                    index = 1
                    for sub_card in value:
                        sub_card_level = sub_card["星级"]
                        sub_card_quality = self.main_window.enhance_simulator.card_quality_map[sub_card["质量"]]
                        sub_card_text += f"副卡{index}:{sub_card_level}星{sub_card_quality}  "
                        index += 1
                case "clover_level":
                    clover_level = self.main_window.enhance_simulator.clover_level_map[value]
                case "success_rate":
                    success_rate = value
        # 发出弹窗，提示找到的组合
        QMessageBox.information(self.main_window, "成功率查找器", f"最接近目标成功率的组合为：\n主卡:{main_card_level}星\n{sub_card_text}\n四叶草等级:{clover_level} \n成功率:{success_rate:.2%}")
        # 刷新UI
        # 主卡部分
        self.main_window.cushion_main_card_level.setText(f"{main_card_level}星")
        self.main_window.init_recipe_box(self.main_window.cushion_main_card_box, need_suffix=False)
        # 副卡部分，先根据长度，将一些空的副卡设置为无
        sub_card_count = len(nearest_combination["sub_cards"])
        for i in range(3, sub_card_count, -1):
            level_label = getattr(self.main_window, f"cushion_sub_card_level_{i}")
            box = getattr(self.main_window, f"cushion_sub_card_box_{i}")
            level_label.setText("无")
            box.clear()
        # 为存在的副卡设置对应的星级和卡片
        for i in range(1, sub_card_count + 1):
            sub_card = nearest_combination["sub_cards"][i - 1]
            sub_card_quality = self.main_window.enhance_simulator.card_quality_map[sub_card["质量"]]
            level_label = getattr(self.main_window, f"cushion_sub_card_level_{i}")
            box = getattr(self.main_window, f"cushion_sub_card_box_{i}")
            box.clear()
            level_label.setText(f"{sub_card['星级']}星{sub_card_quality}")
            # 设置对应质量的卡片选择框
            self.main_window.init_recipe_box(box, filter_word=sub_card_quality, need_suffix=False)
        # 四叶草部分
        self.main_window.cushion_clover_level.setText(clover_level)


class CushionThread(QThread):
    """
    垫卡线程，类似于强化线程，但是既不刷新，也不退出合成屋
    """
    def __init__(self, main_window, cushion_card_dict, cushion_produce_list):
        super().__init__()
        self.main_window = main_window
        self.cushion_card_dict = cushion_card_dict
        self.cushion_produce_list = cushion_produce_list

    def run(self):
        # 检查目前位置
        if not self.init_position():
            return
        while self.main_window.is_running:
            # 制卡
            self.create_cushion_produce_queue()
            self.main_window.execute_produce_queue()
            if not self.main_window.is_running:
                break
            # 制卡完成后，切换到强化页面
            self.msleep(200)
            self.main_window.change_position(1)
            self.msleep(100)
            # 开始垫卡
            self.main_winodw.main_enhancer(single_enhance_plan=self.cushion_card_dict)
            # 垫卡完成后，切换到制作页面，再次循环
            self.msleep(200)
            self.main_window.change_position(0)
            self.msleep(100)

    def create_cushion_produce_queue(self):
        """
        创建垫卡生产队列
        """
        for produce_dict in self.cushion_produce_list:
            # 每种卡片都生产7张
            self.main_window.add_to_produce_queue(produce_dict["名称"], produce_dict["使用香料"], produce_dict)

    def init_position(self):
        """
        初始化目前位置，垫卡特殊，只有处于合成屋时才会开始
        """
        position = self.main_window.check_position() # 获取位置标识
        if position == 1: # 处于制作页面
            return True # 开始垫卡循环
        elif position == 2: # 处于强化页面
            self.main_winodw.main_enhancer(single_enhance_plan=self.cushion_card_dict) # 进行一轮垫卡
            self.msleep(200)
            # 点击卡片制作，进入垫卡循环
            self.enhancer.click(108, 258)
            self.msleep(500)
            return True
        else:
            # 未知位置，弹窗提示
            self.main_window.show_dialog_signal.emit("咳咳","请进入合成屋再点我")
            return False # 不处于制作页面，不进行垫卡循环
    
    def start_loop(self):
        self.start()