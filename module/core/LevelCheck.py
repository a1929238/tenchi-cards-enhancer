import cv2
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match
from module.globals.ResourceInit import resource


def check_gem_enhance_result(current_level):
    """
    截图宝石的星级，判定强化结果
    """
    # 截图
    img = get_image(239, 289, 7, 7)
    # 计算出目标等级
    target_level = current_level + 1
    # 识别.因为宝石在强化后会有一圈特效，故快速比对无法使用，只能使用模板匹配
    result = cv2.matchTemplate(img, resource.level_images_without_hash[target_level], cv2.TM_CCORR_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= 0.95:
        return True
    else:
        return False


def check_card_enhance_result(current_level):
    """截图卡片强化后星级，判定强化结果"""
    # 截图强化区域
    result_img = get_image(267, 323, 40, 50)
    level_img = result_img[5:12, 5:12]
    success_img = resource.level_images[current_level + 1]
    # 判定强化结果
    if direct_img_match(level_img, success_img):
        return True
    else:
        return False
