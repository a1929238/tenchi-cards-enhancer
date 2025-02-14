from PyQt6.QtCore import QTime

from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.globals.EventManager import event_manager
from module.globals.ResourceInit import resource

_CARD_SLOT_POSITION = {
    1: (267, 324, 40, 50),  # 主卡槽
    2: (267, 253, 40, 50),  # 卡槽2
    3: (211, 324, 40, 50),  # 卡槽3
    4: (323, 324, 40, 50),  # 卡槽4
    5: (162, 375, 40, 40)  # 四叶草槽
}


def enhance_log(used_card_list, clover, clover_bind, success):
    """按格式输出强化日志"""
    # 先分离出各种信息
    main_card = used_card_list[0]
    text = f"{main_card.level}星{main_card.name}强化"
    if success:
        text += "成功！"
    else:
        text += "失败！"
    text += "使用卡片："
    for sub_card in used_card_list[1:]:
        text += f"[{sub_card.level}星{sub_card.name}]"
    # 添加上四叶草种类
    clover_bind_dict = {0: "不绑", 1: "绑定"}
    if clover != "无":
        text += f"，使用[{clover_bind_dict[clover_bind]}{clover}四叶草]"
    # 在开头添加上时间戳，只要有小时跟秒数就行了
    text = f"[{QTime.currentTime().toString()}]{text}"
    # 给不同星级的强化成功日志加上不同颜色
    if success:
        if main_card.level <= 2:
            text = f"<font color='gray'>{text}</font>"
        elif main_card.level <= 5:
            text = f"<font color='green'>{text}</font>"
        elif main_card.level <= 7:
            text = f"<font color='blue'>{text}</font>"
        elif main_card.level <= 9:
            text = f"<font color='purple'>{text}</font>"
        elif main_card.level <= 11:
            text = f"<font color='orange'>{text}</font>"
        else:
            text = f"<font color='deep pink'>{text}</font>"
    else:
        text = f"<font color='red'>{text}</font>"
    event_manager.log_signal.emit(text)


def is_card_placed(card_index):
    """判断目标卡片槽位中是否放置了卡片"""
    position = _CARD_SLOT_POSITION[card_index]
    img = get_image(*position)
    result = direct_img_match(img, resource.enhance_slot_image_dict[card_index])
    return not result
