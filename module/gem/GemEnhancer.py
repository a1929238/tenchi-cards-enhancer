from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, QTime

from module.core.DepositoryTab import click_gem
from module.core.DynamicWait import dynamic_wait_gem_enhance_btn_to_gry
from module.core.GetImg import get_image
from module.core.ImgMatch import direct_img_match, has_area_changed
from module.core.ItemTab import get_target_item
from module.core.LevelCheck import check_gem_enhance_result
from module.core.MouseEvent import click
from module.core.PositionCheck import change_position
from module.globals.EventManager import event_manager
from module.globals.ResourceInit import resource
from module.ocr.NumberOcr import get_num
from module.utils import template_match_with_mask, load_level_crystal_map

if TYPE_CHECKING:
    from TenchiCardEnhancer import TenchiCardsEnhancer


def get_crystal_info():
    """
    获取当前所有强化水晶、高级强化水晶的数量与绑定状态
    """
    crystal_info = {
        "绑定高级强化水晶": 0,
        "不绑高级强化水晶": 0,
        "绑定强化水晶": 0,
        "不绑强化水晶": 0
    }
    # 截图道具栏，只需要截图前四格
    tab_img = get_image(33, 526, 196, 49)
    # 分割成4个49x49的图像
    for i in range(4):
        img = tab_img[0:49, i * 49: (i + 1) * 49]
        # 提取物品种类区域
        kind = img[4: 28, 4: 42]
        # 只取其中的44x44区域
        img = img[1:45, 1:45]
        # 匹配出是强化水晶还是高级强化水晶
        for crystal_name, crystal_img in resource.crystal_images.items():
            if direct_img_match(kind, crystal_img):
                name = crystal_name
                bind_icon = img[37:44, 2:8]
                num_img = img[33:41, 9:44]
                # 判断绑定
                bind = direct_img_match(bind_icon, resource.spice_bind_img)
                # 获取数量
                num = get_num(num_img)
                if num is None:
                    num = 1
                full_name = ('绑定' if bind else '不绑') + name
                crystal_info[full_name] = num
                break
        else:
            # 如果没有匹配到水晶，说明水晶已经被匹配完成了
            break
    if crystal_info:
        return crystal_info
    else:
        return None


class GemEnhancer:
    """
    宝石强化器，根据设置强化宝石
    流程为 获取图像->获得具体宝石详情->分配强化方案->根据强化方案与数字ocr判断强化水晶是否满足强化需求->开始强化
    """

    def __init__(self, tenchi_cards_enhancer: TenchiCardsEnhancer):
        self.enhancer = tenchi_cards_enhancer
        # 初始化全局变量
        self.start_x = 0
        self.start_y = 0

        self.level_crystal_map = load_level_crystal_map()
        self.plan = self.enhancer.settings["宝石方案"]
        self.name_cache = None

    def get_gem_info(self, img):
        """
        :param img: numpy 数组，单个宝石图片
        :return: 宝石信息字典，包括名称，星级，绑定
        获取宝石的名称，星级，绑定
        """
        gem_info = {}
        level = None
        name = None
        img = img[1:45, 1:45]
        level_icon = img[3:10, 4:11]
        bind_icon = img[37:44, 2:8]
        # 如果存在缓存，那么先试着用缓存名称来匹配宝石
        if self.name_cache:
            if template_match_with_mask(img, resource.gem_images[self.name_cache], resource.gem_mask):
                name = self.name_cache
            else:
                self.name_cache = None  # 清空缓存
        # 如果缓存没有命中，那么就遍历所有宝石
        if not name:
            # 使用掩码模板匹配每一个宝石，获取宝石名称
            for gem_name, gem_img in resource.gem_images.items():
                if template_match_with_mask(img, gem_img, resource.gem_mask):
                    name = gem_name
                    # 缓存这次的名称
                    self.name_cache = name
                    break
            # 判断是否为空格
            else:
                if direct_img_match(img[22:37, 8:41], hash(resource.empty_card.tobytes())):
                    gem_info['name'] = '空格'
                    return gem_info
                else:
                    return None
        # 获取绑定状态
        bind = direct_img_match(bind_icon, resource.spice_bind_img)
        # 获取该宝石星级，如果该星级不在范围内，则返回None
        for i in range(1, 11):
            if direct_img_match(level_icon, resource.level_images[i]):
                level = i
                break
        # 只有当最低星级为0时，获取不到星级的宝石才是0星宝石
        if self.plan["等级范围"][0] == 0 and level is None:
            level = 0
        if level < self.plan["等级范围"][0] or level >= self.plan["等级范围"][1]:
            return None
        # 返回结果
        gem_info: dict[str, [str, list[int]]] = {
            'name': name,
            'level': level,
            'bind': bind
        }
        return gem_info

    def get_gem_list(self, img):
        """
        :param img: numpy 数组,包含8行7列的宝石页面
        :return: 宝石字典列表
        将宝石页面的截图分割成单个49x49的单个图像，然后获取所有宝石信息
        宝石页面排列规则：一开始固定为超级武器、副武器，宝石被夹在中间，而最后才是主武器。所以在初始化识别出宝石开始与结束位置后，就可以只分割开始位置的图像了
        """
        gem_info_list = []
        end_flag = 0
        # 分割宝石分解页面的格子，以49x49分割
        for i in range(self.start_y, 8):
            if end_flag > 2:
                break
            # 确定当前行的起始列
            current_start_x = self.start_x if i == self.start_y else 0
            for j in range(current_start_x, 7):
                if not self.enhancer.is_running:
                    return False
                block = img[i * 49: (i + 1) * 49, j * 49: (j + 1) * 49]
                # 获取宝石信息
                gem_info = self.get_gem_info(block)
                if gem_info:
                    if gem_info['name'] == '空格':
                        end_flag += 1  # 遇到两个空格就结束
                        continue
                    if self.start_x == 0 and self.start_y == 0:
                        # 记录开始位置
                        self.start_x = j
                        self.start_y = i
                    gem_info['pos'] = [i, j]  # 行和列
                    gem_info_list.append(gem_info)
        return gem_info_list

    def init_gem_enhancer(self):
        """
        重新初始化全局变量
        """
        self.start_x = 0
        self.start_y = 0

    def enhance_gem_main(self):
        """
        强化宝石主函数, 截图并根据设置执行强化宝石的操作
        """
        while self.enhancer.is_running:
            # 截图宝石页面
            img = get_image(559, 139, 343, 392)
            # 获取宝石列表
            gem_list = self.get_gem_list(img)
            tar_gem_list = self.plan["宝石选择"]
            # 遍历宝石列表，寻找匹配方案的宝石
            for gem in gem_list:
                # 寻找到宝石后，点击宝石
                if gem["name"] in tar_gem_list:
                    if tar_gem_list[gem["name"]] == gem["bind"] or gem["bind"] == 2:
                        click_gem(gem["pos"])
                        break
            else:
                event_manager.show_dialog_signal.emit("哇啊啊啊啊", "没有宝石了！")
                return
            # 执行强化操作
            if not self.enhance_gem_until_complete(gem["level"], gem["name"]):
                # 单个宝石强化没完成，返回
                return
            # 成功强化到目标等级，点掉宝石，尝试下一个宝石的强化
            click(258, 309)
            QThread.msleep(self.enhancer.enhance_interval)

    def enhance_gem_until_complete(self, current_level, gem_name):
        """
        用水晶强化宝石，直到水晶/四叶草不够，或宝石强化完成
        """
        while current_level < self.plan["等级范围"][1]:
            bind = self.plan["水晶绑定"]
            # 查看目前的强化水晶量
            crystal_info = get_crystal_info()
            # 如果强化水晶不够，就弹窗提示并停止宝石强化
            if not self.is_crystal_enough(crystal_info, current_level, bind):
                event_manager.show_dialog_signal.emit("啊哇哇", "水晶用完了！就算我再怎么高性能，也没法强化啦")
                return False
            if not self.enhancer.is_running:
                return False
            # 开始强化
            if self.enhance_gem_once(current_level, bind):
                event_manager.log_signal.emit(f"{gem_name}成功强化到{current_level + 1}级")
                current_level += 1
            elif current_level > 5:
                current_level -= 1
            if not self.enhancer.is_running:
                return False
            # 等待一段时间
            QThread.msleep(self.enhancer.enhance_interval)
        # 顺利强化到目标等级，返回True
        return True

    def is_crystal_enough(self, crystal_info, current_level, bind):
        crystal_name = "强化水晶" if current_level < 10 else "高级强化水晶"

        if bind != 2:
            bind_name = "绑定" if bind else "不绑"
            crystal_full_name = bind_name + crystal_name
            return crystal_info[crystal_full_name] >= self.level_crystal_map[f"{current_level}"]
        else:
            return (crystal_info[f"绑定{crystal_name}"] +
                    crystal_info[f"不绑{crystal_name}"] >= self.level_crystal_map[f"{current_level}"])

    def enhance_gem_once(self, current_level, bind):
        """
        执行一次强化
        """
        if not self.enhancer.is_running:
            return False
        # 点击所需强化水晶、所选四叶草
        crystal_name = "强化水晶" if current_level < 10 else "高级强化水晶"
        get_target_item(resource.crystal_images[crystal_name], bind)
        clover_name = self.plan["方案"][f"{current_level + 1}"]
        if clover_name != "无":
            if not get_target_item(resource.clover_images[clover_name], bind):
                event_manager.show_dialog_signal.emit("啊哇哇", "四叶草用完了！就算我再怎么高性能，也没法强化啦")
                return False
        QThread.msleep(100)
        if not self.enhancer.is_running:
            return False
        # 点击强化按钮
        click(288, 436)
        # 等待强化按钮变灰
        dynamic_wait_gem_enhance_btn_to_gry(interval=200, times=20)
        # 检测三轮强化结果，防止特效出现误判
        for _ in range(3):
            if check_gem_enhance_result(current_level):
                return True
            QThread.msleep(500)
        return False

    def gem_decomposition(self):
        # 尝试输入二级密码
        self.enhancer.check_second_password()
        # 将页面切换到宝石分解界面
        change_position("宝石分解")
        # 等待500毫秒加载
        QThread.msleep(500)
        while self.enhancer.is_running:
            # 点一下滑块顶端，进行宝石分解
            click(908, 109)
            if self.decompose_once():
                # 宝石分解一次成功，就继续循环
                QThread.msleep(200)
            else:
                # 宝石分解失败，就退出循环
                self.enhancer.is_running = False
                break
        # 分解完成后弹窗提醒
        event_manager.show_dialog_signal.emit("真棒", "宝石分解完成！")

    def decompose_once(self):
        # 等待200毫秒
        # 截图宝石分解页面
        img = get_image(559, 139, 343, 392)
        # 分割宝石分解页面的格子，以49x49分割，再取44x44部分
        gem_list = self.get_gem_list(img)
        tar_gem_list = self.plan["宝石选择"]
        for gem in gem_list:
            if not self.enhancer.is_running:
                return False
            if (gem["name"] in tar_gem_list and
                    (gem["bind"] == tar_gem_list[gem["name"]]) or tar_gem_list[gem["name"]] == 2):
                break
        else:
            return False
        click_gem(gem["pos"])
        # 点击一次后，等待200毫秒，防止卡顿
        QThread.msleep(200)
        for k in range(40):  # 循环等待宝石是否成功被点击
            gem_slot_img = get_image(269, 315, 30, 30)
            if not direct_img_match(gem_slot_img, resource.gem_slot):
                break
            QThread.msleep(100)
        else:
            # 点击失败，弹窗
            event_manager.show_dialog_signal.emit("哎呦", "宝石怎么点不上去")
            return False
        # 点击分解
        click(284, 377)
        # 检测槽里的宝石有没有消失
        if has_area_changed(267, 315, 30, 30):
            # 输出分解日志
            gem_name = gem["name"]
            gem_bind = "绑定" if gem["bind"] else "不绑"
            text = f"<font color='purple'>[{QTime.currentTime().toString()}]{gem_bind}{gem_name}分解成功!</font>"
            event_manager.log_signal.emit(text)
            return True  # 成功分解，返回True
        else:
            # 分解失败，弹窗
            event_manager.show_dialog_signal.emit("哎呦", "这宝石分解不了啊")
            return False


class GemEnhancerThread(QThread):
    def __init__(self, tenchi_cards_enhancer):
        super().__init__()
        self.gem_enhancer = GemEnhancer(tenchi_cards_enhancer)
        self.mode = None

    def run(self):
        self.gem_enhancer.enhancer.is_running = True
        match self.mode:
            case "enhance":
                self.gem_enhancer.enhance_gem_main()
            case "decompose":
                self.gem_enhancer.gem_decomposition()

    def start_enhance(self):
        self.mode = "enhance"
        self.start()

    def start_decompose(self):
        self.mode = "decompose"
        self.start()
