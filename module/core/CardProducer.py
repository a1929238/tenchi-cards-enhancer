from collections import Counter

from PyQt6.QtCore import QThread

from module.core.DynamicWait import dynamic_check_gold
from module.core.GetImg import get_image
from module.core.ImgMatch import template_img_match, screenshot_and_direct_img_match, find_and_crop_template, \
    direct_img_match
from module.core.ItemTab import get_target_item, get_item_list
from module.core.MouseEvent import click
from module.globals.DataClass import Card, Item
import module.globals.GLOBALS as GLOBALS
from module.globals.ResourceInit import resource
from module.globals.EventManager import event_manager
from module.ocr.NumberOcr import get_num
from module.utils import merge_card_counts

import cv2


def get_spice_usable(spice_stock: list[Item], produce_plan):
    """从香料列表获取可用香料，返回按等级倒序的可用香料列表"""
    # print(spice_stock)
    # 剔除数量少于5的香料
    usable_spice = [spice for spice in spice_stock if spice.count > 5]
    # 暂时方案，总是加入无限多的零星香料
    usable_spice.append(Item("不放香料", False, 9999))
    # 剔除生产方案中不可用的香料
    usable_spice = [spice for spice in usable_spice if produce_plan[spice.name]]
    print(usable_spice)
    return usable_spice


def filter_spice(usable_spice, settings):
    """
    根据强化方案剔除不符合绑定情况的香料，纯绑定和不绑的逻辑都很简单
    """
    max_level, min_level = settings["个人设置"]["最小星级"], settings["个人设置"]["最大星级"]
    bind_list = []
    level_bind_list = set()
    for level in range(int(max_level), int(min_level)):
        enhance_type = f'{level}-{level + 1}'
        enhance_plan = settings["强化方案"][enhance_type]
        # 遍历所要使用的所有卡片，判断是否全为一种情况，同时给出元组列表
        for card, info in enhance_plan.items():
            if not card.startswith("副卡") and not card.startswith("主卡"):
                continue
            if info.get("星级", "无") == "无":
                continue
            # 无视零星卡的绑定情况
            card_level = int(info.get("星级", 0)) == 0
            if card_level == 0:
                continue
            bind = info["绑定"]
            bind_list.append(bind)
            level_bind_list.add((card_level, bind))
    # 如果绑定情况全部相等，则按照绑定情况过滤
    if len(set(bind_list)) == 1:
        if bind_list[0] == 2:
            # 全部为绑定+不绑，直接返回
            return usable_spice
        # 返回对应绑定情况的香料
        return [spice for spice in usable_spice if spice.bind == bind_list[0]]
    else:
        # 如果绑定情况不全等，则根据集合内的元组进行过滤
        return [spice for spice in usable_spice if (spice.get_level(), spice.bind) in level_bind_list]


def get_recipe(card_name, level, bind, count, card_pack_dict):
    """
    获取配方以及它的可用状态，剩余个数。支持卡包
    Args:
        card_name(str): 卡片名称
        level(int): 期望使用的香料等级
        bind(int): 是否绑定
        count(int): 期望卡片数量
        card_pack_dict(dict): 卡包字典
    Returns:
        produce_count(int): 最终制卡的数量
        actual_card_name(str): 实际使用的卡片名
    """
    if card_pack_dict and card_name in card_pack_dict:
        # 按卡包列表的顺序查找配方
        for card_name in card_pack_dict[card_name]:
            # 过滤掉没有配方的卡片和在不可用列表中的卡片
            if card_name not in resource.recipe_images or card_name in GLOBALS.NOT_USABLE_RECIPES:
                continue
            # 递归调用自己，尝试获取对应的配方
            produce_count, actual_card_name = get_recipe(card_name, level, bind, count, card_pack_dict)
            # 如果卡片的实际数量小于期望生产数量，则单独调用一次生产方法，生产剩余需要的卡片
            if 0 < produce_count < count:
                produce_card(card_name, level, bind, count - produce_count, card_pack_dict)
                return produce_count, actual_card_name
            # 如果卡片的实际数量大于等于期望生产数量，则直接返回
            elif produce_count >= count:
                return count, actual_card_name
            else:
                # 将该不可用的配方加入不可用列表中
                GLOBALS.NOT_USABLE_RECIPES.append(card_name)
        # 全是用不可制作的卡包为啥还要点制卡并强卡
        else:
            return 0, None
    # 点击一下滚动条最顶端，重置位置
    click(907, 112)
    # 等待图像加载
    QThread.msleep(400)
    recipe_img = resource.recipe_images[card_name]
    for _ in range(4):
        # 尝试校验目标配方可用性与数量
        recipe_tab_img = get_image(559, 90, 343, 196)
        usable, actual_count = get_recipe_usable_and_count(recipe_tab_img, recipe_img)
        if usable:
            print(f"{card_name} 是否可用：{usable}，实际数量：{actual_count}")
            break
        # 点俩下下滑键
        for _ in range(2):
            click(910, 278)
        # 等待图像加载
        QThread.msleep(400)
    else:
        return 0, None
    return min(count, actual_count), card_name


def get_recipe_count(recipe_tab_img, recipe_img):
    """获取目标配方的数量"""
    img = find_and_crop_template(recipe_tab_img, recipe_img, extra_h=15, extra_w=7)
    # 剪切一下图像，保留下半部分
    img = img[int(img.shape[0] / 2):, :]
    cv2.imwrite("test.png", img)
    count = get_num(img, resource.num_images)
    if count:
        return count
    else:
        # 如果没匹配到数量，那就点一下下滑键，再截一次图
        click(910, 278)
        # 等待图像加载
        QThread.msleep(300)
        recipe_tab_img = get_image(559, 90, 343, 196)
        img = find_and_crop_template(recipe_tab_img, recipe_img, extra_h=15, extra_w=7)
        count = get_num(img, resource.num_images)
        return count


def get_recipe_usable_and_count(recipe_tab_img, recipe_img):
    """获得配方的可用性和数量"""
    # 配方栏左上角坐标
    origin_pos = [559, 90]
    # 模版匹配，获取目标配方的位置，并点一下
    if template_img_match(recipe_tab_img, recipe_img, origin_pos=origin_pos):
        # 获取到了的话，看看能不能对目标位置进行识别数字
        count = get_recipe_count(recipe_tab_img, recipe_img)
    else:
        return False, 0
    # 等待图片被点上合成屋
    QThread.msleep(200)
    # 能识别数字，就检查可用性
    btn_img = get_image(259, 416, 10, 10)
    if not direct_img_match(btn_img, resource.can_card_produce):
        return False, 0
    # 可用，返回可用性，数量
    return True, count


def get_recipe_tab_img():
    """获取配方栏的图片"""
    return get_image(559, 90, 343, 196)


def produce_card(card_name, level, bind, count, card_pack_dict):
    """
    制造对应数量的卡片，支持卡包和校验
    Args:
        card_name(str): 卡片名称
        level(int): 卡片等级
        bind(int): 是否绑定
        count(int): 制造数量
        card_pack_dict(dict): 卡包字典
    Returns:
        count: 实际生产的数量
        card_name: 实际生产出的卡片名
    """
    spice_list = ["不放香料", "天然香料", "上等香料", "秘制香料", "极品香料", "皇室香料", "魔幻香料", "精灵香料",
                  "天使香料"]
    # 尝试获取剩余数量大于需要生产量的配方，如果获取配方的剩余数量小于需要生产量，且配方为卡包，则递归调用该方法来生产剩下的卡片
    count, card_name = get_recipe(card_name, level, bind, count, card_pack_dict)
    if count == 0:
        event_manager.show_dialog_signal.emit("强化完成！", "你的卡套已经全部制作完成！什么也不剩啦")
        return 0, None
    # 点击对应的香料
    if level != 0:
        find, _ = get_target_item(resource.spice_images[spice_list[level]], bind)
        # 如果找不到香料，弹窗
        if not find:
            event_manager.show_dialog_signal.emit("没有找到对应的香料！", "恭喜你触发了一个几乎不可能触发的弹窗！")
        return 0, None
    for _ in range(count):
        if not GLOBALS.IS_RUNNING:
            return 0, None
        # 点击制作按钮
        click(285, 425)
        # 通过动态等待金币变化，检测是否制作成功
        if not dynamic_check_gold(with_click=True, click_pos=(285, 425)):
            event_manager.show_dialog_signal.emit("卡片制作卡住啦！", "发生什么事了，快去看看吧")
            return 0, None
    # 制作完成后返回数量以及实际的卡片名
    return count, card_name


def dynamic_card_producer(settings, card_count_dict=None):
    """
    根据卡片需求动态制卡。将现存的所有卡片看作主卡，计算副卡需求。再用所有主卡需求填充制卡列表
    """
    enhance_plan = settings["强化方案"]
    # 获取香料数量
    spice_stock = get_item_list("香料")
    # 获取可用香料
    usable_spice = get_spice_usable(spice_stock, settings["生产方案"])
    # 根据强化方案的绑定情况，过滤一遍香料
    usable_spice = filter_spice(usable_spice, settings)
    card_demand: list[Card] = []
    # 计算卡片需求
    if card_count_dict:
        # 如果存在卡片等级字典，则根据卡片等级字典计算卡片需求
        card_demand = get_card_demand(enhance_plan, card_count_dict, usable_spice)
    # 用主卡需求进行填充
    card_demand = fill_demand_with_main_card(enhance_plan, card_demand, usable_spice)
    # 截取前 14 项
    limited_cards = card_demand[:14]

    # 将结果转为元组列表
    produce_list: list[tuple[Card, int]] = [(card, count) for card, count in Counter(limited_cards).items()]

    # 将元组列表送到解析器里，然后送给制卡器
    produce_list = parse_produce_list(enhance_plan, produce_list, usable_spice)
    # 如果解析器返回的produce_list为空，则表明没有香料了，返回False
    if not produce_list:
        event_manager.show_dialog_signal.emit("没有香料了！", "你的香料不足，无法进行制卡！")
        return False
    print(f"动态制卡需求：{produce_list}")
    # 进行制卡
    for card, count in produce_list:
        name, level, bind = card.get_state()
        spice = next((item for item in usable_spice if item.get_level() == level), None)
        count = min(count, spice.count // 5)
        actual_count, actual_card_name = produce_card(name, level, bind, count, settings["卡包配置"])
        if actual_count == 0:
            return False
        print(f"动态制卡{card.level}星{actual_card_name}{actual_count}次")


def get_card_demand(enhance_plan, card_count_dict, usable_spice) -> list[Card]:
    """
    根据目前的卡片存量，计算副卡与部分主卡的总需求
    """
    card_demand = []
    sub_cards = ["副卡1", "副卡2", "副卡3"]
    sub_cards_name = []
    max_count = 14
    # 找到最高星级
    max_spice_level = max(usable_spice, key=lambda x: x.get_level()).get_level()
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
            if sub_card in card_count_dict and card_count_dict[sub_card] >= 5:
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


def fill_demand_with_main_card(enhance_plan, card_demand: list[Card], usable_spice):
    """用主卡填满卡片需求，每个主卡7张"""
    spice_list = list(range(9))
    spice_list.sort(reverse=True)

    for spice in usable_spice:
        # 如果香料的余量不足，则仅用这些香料
        if spice.count < 35:
            count = spice.count // 5
        else:
            # 两种香料时用7填充
            if len(usable_spice) > 1:
                count = 7
            else:
                count = 14
        card = Card()
        level = spice.get_level()
        card.load_from_dict(enhance_plan[f"{level}-{level + 1}"]["主卡"])
        for _ in range(count):
            card_demand.append(card)
    return card_demand


def parse_produce_list(enhance_plan, produce_list, usable_spice):
    """
    根据强化方案，解析生产列表
    注意，添加的主卡一定是和使用香料对应的，但是副卡会出现没有可用香料的情况
    这种情况就要解析副卡来源，用可用香料与等级屏蔽进行填充
    """
    # 初始化来源列表，用于记录需要单独制卡的卡片
    needed_list = []
    # 集合化可用香料等级列表
    usable_spice_level = set(spice.get_level() for spice in usable_spice)
    for card, count in produce_list:
        if card.level not in usable_spice_level and count > 5:
            # 分解该卡片来源
            need_cards = calculate_total_base_cards(card.level, usable_spice_level, enhance_plan)
            needed_list += need_cards * count
    # 元组列表化需求列表
    needed_list = [(card, count) for card, count in Counter(needed_list).items()]
    # 再度过滤列表，过滤掉没有对应星级香料的卡片
    filtered_list = [
        (card, count)
        for (card, count) in produce_list
        if card.level in usable_spice_level
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


def calculate_total_base_cards(target_level, usable_spice_level, enhance_plan):
    """
    递归计算强化到目标星级所需的基础0星卡总数
    Args:
        target_level(int):需要分解的目标星级
        usable_spice_level(set):可用香料等级集合
        enhance_plan(dict):强化方案
    Returns:
         total_list:具体的所需卡片列表
    """
    total_list = []

    # 获取对应的强化方案（格式：当前星级-目标星级）
    plan_key = f"{target_level - 1}-{target_level}"
    current_plan = enhance_plan[plan_key]

    # 递归计算主卡消耗
    main_card = Card()
    current_plan["主卡"]["星级"] = target_level - 1
    main_card.load_from_dict(current_plan["主卡"])
    # 香料可用，直接加入列表
    if main_card.level in usable_spice_level:
        total_list.append(main_card)
    else:
        total_list.extend(calculate_total_base_cards(target_level - 1, usable_spice_level, enhance_plan))

    # 计算所有副卡消耗
    for key in current_plan:
        if key.startswith("副卡") and current_plan[key]["星级"] != "无":
            sub_card = Card()
            sub_card.load_from_dict(current_plan[key])
            if sub_card.level in usable_spice_level:
                # 如果香料可用，直接加入列表
                total_list.append(sub_card)
            else:
                total_list.extend(calculate_total_base_cards(sub_card.level, usable_spice_level, enhance_plan))

    return total_list
