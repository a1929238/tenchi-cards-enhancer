# 资源初始化模块，有常用图片资源的初始化，并保存为全局变量，也有图片读取的方法

from .utils import imread
import os

class ResourceInit:
    def __init__(self):
        # 获取项目根目录路径
        self.root_dir = os.path.dirname(os.path.dirname(__file__))
        # 以完整路径导入图片
        self.card_bind_img = imread(os.path.join(self.root_dir, "items/bind_icon/card_bind.png"))
        self.spice_bind_img = imread(os.path.join(self.root_dir, "items/bind_icon/spice_bind.png"))
        self.line_img = imread(os.path.join(self.root_dir, "items/position/line.png"))
        # 卡片星级以字典形式存储
        self.level_images = {k: imread(os.path.join(self.root_dir, f"items/level/{k}.png")) for k in range(0, 13)}
        # 四叶草也以字典形式存储
        self.clover_images = self.load_clover_images()
        # 香料也一样
        self.spice_images = self.load_spice_images()
        # 位置标志的存储
        self.sub_card_icon = imread(os.path.join(self.root_dir, "items/position/sub_card.png"))
        self.compose_icon = imread(os.path.join(self.root_dir, "items/position/合成屋.png"))
        self.produce_help_icon = imread(os.path.join(self.root_dir, "items/position/制作说明.png"))
        self.enhance_help_icon = imread(os.path.join(self.root_dir, "items/position/强化说明.png"))

    def load_clover_images(self):
        clover_images = {}
        clover_dir = os.path.join(self.root_dir, "items/clover/")
        # 获取四叶草文件夹内所有文件名
        for clover_file in os.listdir(clover_dir):
            # 去掉文件扩展名，得到四叶草的名称
            clover_name = os.path.splitext(clover_file)[0]
            clover_name = clover_name.replace("四叶草", "") # 只保留四叶草的种类
            # 读取四叶草图像并存储到字典中
            clover_images[clover_name] = imread(os.path.join(clover_dir, clover_file))
        return clover_images
    
    def load_spice_images(self):
        spice_images = {}
        spice_dir = os.path.join(self.root_dir, "items/spice/")
        # 获取香料文件夹内所有文件名
        for spice_file in os.listdir(spice_dir):
            # 去掉文件扩展名，得到香料的名称
            spice_name = os.path.splitext(spice_file)[0]
            # 读取香料图像并存储到字典中
            spice_images[spice_name] = imread(os.path.join(spice_dir, spice_file))
        return spice_images