from collections import Counter

from module.core.ImgMatch import direct_img_match, template_img_match
from module.globals.DataClass import Card
from module.globals.ResourceInit import resource

CARD_HEIGHT = 57
CARD_WIDTH = 49
TYPE_ROI = (slice(22, 37), slice(8, 41))  # 卡片类型检测区域
BIND_ROI = (slice(45, 52), slice(5, 11))  # 绑定标志检测区域
LEVEL_ROI = (slice(8, 15), slice(9, 16))  # 星级检测区域


def get_card_list(img, cards, rows=7, columns=7, min_level=0, max_level=9) -> list[Card]:
    """
    遍历识图图像中的卡片，然后返回卡片对象的列表
    Args:
        img(np.array):卡片列表图像，宽一定为57的倍数，高一定为49的倍数
        cards(set):需要识别的卡片名
        rows:行数
        columns:列数
        min_level:最低识别等级
        max_level:最高识别等级
    Returns:
        card_list(list[Card]):包含卡片对象的列表
    """

    card_list = []
    max_possible_level = len(resource.level_images) - 1  # 防止数组越界

    # 参数有效性校验
    max_level = min(max_level, max_possible_level)

    for y in range(rows):
        for x in range(columns):
            # 提取卡片区块
            block = img[y * CARD_HEIGHT:(y + 1) * CARD_HEIGHT,
                        x * CARD_WIDTH:(x + 1) * CARD_WIDTH]

            # 卡片类型识别
            card_type = block[TYPE_ROI]
            matched_name = next((name for name in cards
                                 if direct_img_match(card_type, resource.card_images[name])), None)
            if not matched_name:
                continue

            # 绑定状态检测
            is_bind = direct_img_match(block[BIND_ROI], resource.card_bind_img)

            # 星级检测
            level_img = block[LEVEL_ROI]
            level = None
            for k in range(max(min_level, 1), 15):
                if direct_img_match(level_img, resource.level_images[k]):
                    level = k
                    break

            # 处理默认0星情况（仅在允许0星且未检测到其他星级时）
            if level is None and min_level == 0:
                level = 0
            elif level is None:
                continue  # 既未检测到星级又不允许0星时跳过
            elif level > max_level:
                continue  # 检测到大于最大星级的卡片时跳过

            # 创建卡片对象
            card_list.append(Card(
                name=matched_name,
                level=level,
                bind=1 if is_bind else 0,
                position=(y, x)
            ))

    return card_list


def make_card_count_dict(card_list):
    if not card_list:
        return {}
    return {card: count for card, count in Counter(card_list).items()}


def get_card_names(enhance_plan, card_pack, min_level, max_level):
    """
    获取所有需要强化的卡片名称
    """
    card_names = set()
    for level in range(min_level, max_level):
        level_key = f"{level}-{level + 1}"
        cards = [enhance_plan[level_key]["主卡"]["卡片名称"]]
        for sub in range(1, 4):
            if enhance_plan[level_key][f"副卡{sub}"]["星级"] == "无":
                continue
            cards.append(enhance_plan[level_key][f"副卡{sub}"]["卡片名称"])

        for card_name in cards:
            if card_name in card_pack:
                card_names.update(card_pack[card_name])
            else:
                card_names.add(card_name)
    return card_names


def exist_empty_block(img):
    """
    模版匹配，判断图像中是否存在空格
    """
    return template_img_match(img, resource.empty_card, threshold=0.99, with_click=False)
