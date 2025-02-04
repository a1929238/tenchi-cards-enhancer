from module.core.MouseEvent import click


def click_gem(pos):
    """
    根据传入的位置列表，点击目标位置的宝石
    """
    click(584 + pos[1] * 49, 118 + (pos[0] + 1) * 49)