from PyQt6.QtCore import QThread
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match, screenshot_and_direct_img_match
from module.core.MouseEvent import click
from module.globals.DataClass import Item
from module.globals.ResourceInit import resource
from module.log.TenchiLogger import logger
from module.ocr.NumberOcr import get_num

"""
关于合成屋内道具栏所有内容的函数
"""


def get_item_tab_img(num=10) -> list:
    """
    获取合成屋道具栏，在分割后返回图像数组
    默认获取十张图片
    """
    tab_img = get_image(33, 526, num * 49, 49)
    item_img_list = []
    for index in range(num):
        block = tab_img[0: 49, index * 49:(index + 1) * 49]
        item_img_list.append(block)
    return item_img_list


def is_item_bind(item_img) -> bool:
    """
    判断道具是否绑定

    Args:
        item_img: 49x49的标准道具图像
    """
    bind_flag = item_img[38:45, 3:9]
    bind = direct_img_match(bind_flag, resource.spice_bind_img)
    return bind


def get_item_count(item_img) -> int:
    """
    获取道具数量

    Args:
        item_img: 49x49的标准道具图像
    """
    num_img = item_img[34:42, 10:45]
    count = get_num(num_img)
    # 道具截图总是能截到数字，没有数字就代表该道具只有一个
    if count is None:
        count = 1
    return count


def get_item_name(item_img, tar_img_dict) -> str:
    """
    获取道具名称

    Args:
        item_img: 49x49的标准道具图像
        tar_img_dict: 目标图片字典
    """
    # 裁剪图片
    item_img = item_img[4: 28, 4: 42]
    for name, tar_img in tar_img_dict.items():
        if direct_img_match(item_img, tar_img):
            return name
    else:
        return "未知"


def item_tab_page_up():
    """一直翻页到向上翻页按钮变灰"""
    # 如果向上翻页按钮本来就是灰的，则直接返回
    if screenshot_and_direct_img_match(532, 539, resource.page_up):
        return True
    for _ in range(10):
        # 点击三下向上翻页键
        for _ in range(3):
            click(532, 539)
        QThread.msleep(200)
        # 检测翻页按钮是否变灰
        if screenshot_and_direct_img_match(532, 539, resource.page_up):
            return True
    return False


def item_tab_page_down():
    """一直翻页直到翻页按钮变灰。该翻页方法仅适用于道具总量小于20的情况"""
    # 如果向下翻页按钮本来就是灰的，则直接返回
    if screenshot_and_direct_img_match(532, 560, resource.page_down):
        return True
    for _ in range(10):
        # 点击三下向下翻页键
        for _ in range(3):
            click(535, 563)
        QThread.msleep(200)
        # 检测翻页按钮是否变灰
        if screenshot_and_direct_img_match(532, 560, resource.page_down):
            return True
    return False


def click_item(index):
    """
    点击对应位置的道具，上限9格
    """
    click(55 + 49 * index, 550)


def get_item_list(mode, page_down=True) -> list[Item]:
    """根据类型获取完整的道具列表
    Args:
        mode(str):道具类型，有香料，四叶草，强化水晶
        page_down(bool): 是否翻页，默认为True
    Returns:
        item_list:包含道具字典的列表
    """
    item_list = []
    # 确保处于道具页最上方
    item_tab_page_up()
    match mode:
        case "香料":
            tar_img_dict = resource.spice_images
            num = 10
        case "四叶草":
            tar_img_dict = resource.clover_images
            num = 10
        case "强化水晶":
            tar_img_dict = resource.crystal_images
            num = 4
        case _:
            logger.warning("未知道具类型，道具列表获取失败")
            return []
    if page_down:
        page_down_times = 2
    else:
        page_down_times = 1
    for _ in range(page_down_times):
        item_img_list = get_item_tab_img(num)
        for item_img in item_img_list:
            item_name = get_item_name(item_img, tar_img_dict)
            if item_name == "未知":
                break
            item = Item(
                name=item_name,
                bind=is_item_bind(item_img),
                count=get_item_count(item_img)
            )
            if item not in item_list:
                item_list.append(item)
        if page_down:
            item_tab_page_down()
    return item_list


def get_target_item(tar_img, bind, page_down=True, num=10) -> (bool, bool):
    """
    寻找并点击目标道具

    Args:
        tar_img: 目标道具图片，38x24大小
        bind(int): 绑定情况,0/1/2, 2 代表忽略绑定情况
        page_down(bool): 是否翻页，默认为True
        num(int): 需要检查的格数，默认为10
    Returns:
        bool: 是否找到目标道具
        bind: 目标道具的绑定情况，统计用
    """
    # 确保处于道具页最上方
    item_tab_page_up()
    if page_down:
        page_down_times = 2
    else:
        page_down_times = 1
    for _ in range(page_down_times):
        item_img_list = get_item_tab_img(num)
        for index, img in enumerate(item_img_list):
            # 匹配目标道具种类
            kind = img[4: 28, 4: 42]
            if direct_img_match(kind, tar_img):
                # 匹配成功，检测绑定情况
                item_bind = is_item_bind(img)
                if bind == 2 or bind == item_bind:
                    # 匹配成功，点击目标道具
                    click_item(index)
                    return True, item_bind
        # 第一轮识图结束，如果需要，进行翻页
        if page_down:
            item_tab_page_down()
    return False, False
