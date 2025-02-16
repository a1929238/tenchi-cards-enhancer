from PyQt6.QtCore import QThread

from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.core.MouseEvent import click, drag
from module.globals.ResourceInit import resource

repo_area = (564, 98, 50, 50)


def click_gem(pos):
    """
    根据传入的位置列表，点击目标位置的宝石
    """
    click(584 + pos[1] * 49, 118 + (pos[0] + 1) * 49)


def scroll_repo_slider(current_position, distance, check_interval=20):
    """
    Args:
        current_position: 当前滚动条位置
        distance: 滑动距离
        check_interval: 动态检测滑动参数的完成性间隔
    Notes:
        仓库滚动条滑动函数
        含对滚动条的任何长度滑动参数，以及动态检测滑动参数的完成性
    """
    # 如果已经在最下方，则直接返回False，表示不需要再次滑动
    bottom_area_img = get_image(905, 520, 10, 10)
    if not direct_img_match(bottom_area_img, resource.scroll_bottom_area):
        return False
    repo_img_hash = hash(get_image(*repo_area).tobytes())
    drag(908, 120 + current_position, 0, distance)
    for _ in range(20):
        QThread.msleep(check_interval)
        current_repo_img = get_image(*repo_area)
        # 发生变化，代表滑动完成
        if not direct_img_match(current_repo_img, repo_img_hash):
            return True


def reset_repo_slider(check_interval=20):
    """点击滚动条最上方重置滚动条"""
    # 如果已经在最上方，则直接返回False
    top_area_img = get_image(905, 110, 10, 10)
    if not direct_img_match(top_area_img, resource.scroll_top_area):
        return False
    repo_img_hash = hash(get_image(*repo_area).tobytes())
    click(908, 120)
    for _ in range(20):
        QThread.msleep(check_interval)
        current_repo_img = get_image(*repo_area)
        if not direct_img_match(current_repo_img, repo_img_hash):
            return True
