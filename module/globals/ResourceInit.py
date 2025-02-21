# 资源初始化模块，有常用图片资源的初始化，并保存为全局变量，也有图片读取的方法

from module.utils import imread, resource_path, imread_to_hash
import os


def load_num_images():
    num_images_without_hash = {}
    num_dir = resource_path("items/ocr/num")
    for num_file in os.listdir(num_dir):
        # 去掉文件扩展名
        num = os.path.splitext(num_file)[0]
        num_images_without_hash[num] = imread(os.path.join(num_dir, num_file), True)  # 单通道图像不能用read color
    # 预计算所有数字的宽度和最大步长
    num_entries = []
    num_entries_without_hash = []
    for num_str, num_img in num_images_without_hash.items():
        # 解析数字字符串格式
        width_str, digit = num_str[0], num_str[1]
        width = int(width_str)
        num_entries_without_hash.append((width, digit, num_img))
        num_entries.append((width, digit, hash(num_img.tobytes())))
    return num_entries, num_entries_without_hash


def load_success_rate_num_images() -> list[tuple]:
    success_rate_num_images = {}
    success_rate_num_dir = resource_path("items/ocr/success_rate_num")
    for success_rate_file in os.listdir(success_rate_num_dir):
        # 去掉文件扩展名
        success_rate = os.path.splitext(success_rate_file)[0]
        success_rate_num_images[success_rate] = imread(os.path.join(success_rate_num_dir, success_rate_file), True)
    # 预计算所有数字的宽度和最大步长
    num_entries = []
    for num_str, num_img in success_rate_num_images.items():
        # 解析数字字符串格式
        width_str, digit = num_str[0], num_str[1]
        width = int(width_str)
        num_entries.append((width, digit, num_img))
        # 按宽度升序排列（优先匹配短的数字）
        num_entries.sort(key=lambda x: x[0])
    return num_entries


def load_gem_images():
    gem_images = {}
    gem_dir = resource_path("items/gem/")
    # 获得宝石文件夹内所有文件名
    for gem_file in os.listdir(gem_dir):
        # 去掉文件扩展名
        gem_name = os.path.splitext(gem_file)[0]
        # 读取宝石图像并存储到字典中
        gem_images[gem_name] = imread(os.path.join(gem_dir, gem_file), with_alpha=True)
    return gem_images


def load_spice_images():
    spice_images = {}
    spice_dir = resource_path("items/spice/")
    # 获取香料文件夹内所有文件名
    for spice_file in os.listdir(spice_dir):
        # 去掉文件扩展名，得到香料的名称
        spice_name = os.path.splitext(spice_file)[0]
        # 读取香料图像并存储到字典中
        spice_images[spice_name] = imread_to_hash(os.path.join(spice_dir, spice_file))
    return spice_images


def load_clover_images():
    clover_images = {}
    clover_dir = resource_path("items/clover/")
    # 获取四叶草文件夹内所有文件名
    for clover_file in os.listdir(clover_dir):
        # 去掉文件扩展名，得到四叶草的名称
        clover_name = os.path.splitext(clover_file)[0]
        clover_name = clover_name.replace("四叶草", "")  # 只保留四叶草的种类
        # 读取四叶草图像并存储到字典中
        clover_images[clover_name] = imread_to_hash(os.path.join(clover_dir, clover_file))
    return clover_images


def load_recipe_images():
    recipe_images = {}
    recipe_dir = resource_path("items/recipe/")
    # 获取配方文件夹内所有文件名
    for recipe_file in os.listdir(recipe_dir):
        # 去掉文件扩展名，得到配方的名称
        recipe_name = os.path.splitext(recipe_file)[0]
        recipe_name = recipe_name.replace("配方", "")  # 只保留配方的种类
        # 读取配方图像并存储到字典中
        recipe_images[recipe_name] = imread(os.path.join(recipe_dir, recipe_file), with_alpha=True)
    return recipe_images


def load_card_images():
    card_images = {}
    card_dir = resource_path("items/card/")
    for card_file in os.listdir(card_dir):
        # 去掉文件扩展名，得到卡片的名称
        card_name = os.path.splitext(card_file)[0]
        # 读取卡片图像并存储到字典中
        card_images[card_name] = imread_to_hash(os.path.join(card_dir, card_file))
    return card_images


def load_enhance_slot_image_dict():
    """读取强化卡槽的图片"""
    paths = [
        resource_path("items/position/main_card_slot.png"),
        resource_path("items/position/sub_card_1_slot.png"),
        resource_path("items/position/sub_card_2_slot.png"),
        resource_path("items/position/sub_card_3_slot.png"),
        resource_path("items/position/clover_slot.png"),
    ]
    enhance_slot_image_dict = {}
    for index, path in enumerate(paths):
        enhance_slot_image_dict[index+1] = imread_to_hash(path)
    return enhance_slot_image_dict


class ResourceInit:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        # 哈希资源
        self.card_bind_img = imread_to_hash(resource_path("items/bind_icon/card_bind.png"))
        self.spice_bind_img = imread_to_hash(resource_path("items/bind_icon/spice_bind.png"))

        # 卡片星级以字典形式存储
        self.level_images = {k: imread_to_hash(resource_path(f"items/level/{k}.png")) for k in range(1, 15)}
        self.level_images_without_hash = {k: imread(resource_path(f"items/level/{k}.png")) for k in range(1, 15)}
        # 卡片资源
        self.card_images = load_card_images()
        # 以字典形式存储强化水晶
        self.crystal_images = {
            '强化水晶': imread_to_hash(resource_path("items/crystal/强化水晶.png")),
            '高级强化水晶': imread_to_hash(resource_path("items/crystal/高级强化水晶.png"))
        }
        # 四叶草也以字典形式存储
        self.clover_images = load_clover_images()
        # 香料
        self.spice_images = load_spice_images()
        # 强化卡槽
        self.enhance_slot_image_dict = load_enhance_slot_image_dict()
        # 位置标志的存储
        self.compose_icon = imread_to_hash(resource_path("items/position/合成屋.png"))
        self.produce_help_icon = imread_to_hash(resource_path("items/position/制作说明.png"))
        self.enhance_help_icon = imread_to_hash(resource_path("items/position/强化说明.png"))
        self.decompose_help_icon = imread_to_hash(resource_path("items/position/分解说明.png"))
        self.scroll_top_area = imread_to_hash(resource_path("items/position/scroll_top_area.png"))
        self.scroll_bottom_area = imread_to_hash(resource_path("items/position/scroll_bottom_area.png"))
        self.gem_enhance_not_selected = imread_to_hash(resource_path("items/position/宝石强化_未选中.png"))
        self.can_card_produce = imread_to_hash(resource_path("items/position/卡片制作_未选中.png"))
        self.empty_card = imread(resource_path("items/position/empty_card.png"))
        self.gem_slot = imread_to_hash(resource_path("items/position/gem_slot.png"))
        self.bind_dialog = imread_to_hash(resource_path("items/position/bind_dialog.png"))
        self.page_up = imread(resource_path("items/position/PageUp.png"))
        self.page_down = imread(resource_path("items/position/PageDown.png"))
        self.gray_gem_enhance_btn = imread(resource_path("items/position/灰色宝石强化按钮.png"))

        # ocr数字
        self.num_images, self.num_images_without_hash = load_num_images()
        self.success_rate_num_images = load_success_rate_num_images()

        # 非哈希资源
        self.gem_mask = imread(resource_path("items/mask/gem_mask.png"))  # 掩码
        self.recipe_mask = imread(resource_path("items/mask/recipe_mask.png"))

        self.line_img = imread(resource_path("items/position/line.png"))
        self.gem_images = load_gem_images()
        self.recipe_images = load_recipe_images()  # 配方

        # 资源加载完毕
        self._initialized = True


# 全局资源初始化
resource = ResourceInit()
