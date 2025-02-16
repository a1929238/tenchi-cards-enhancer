from dataclasses import dataclass

spice_list = ["不放香料", "天然香料", "上等香料", "秘制香料", "极品香料", "皇室香料", "魔幻香料", "精灵香料",
              "天使香料", "圣灵香料"]


@dataclass
class Item:
    """
    代表一个物品的全部信息
    """
    name: str
    bind: bool
    count: int

    def print(self):
        print(f"{self.name} {self.bind} {self.count}")

    def get_level(self):
        return spice_list.index(self.name)


@dataclass
class Card:
    name: str = ""
    level: int = 0
    bind: int = 0
    position: tuple = ()

    def load_from_dict(self, card_dict):
        self.name = card_dict["卡片名称"]
        self.level = int(card_dict["星级"])
        self.bind = card_dict["绑定"]

    def get_state(self) -> tuple[str, int, int]:
        return self.name, self.level, self.bind

    def get_text(self) -> str:
        text = ""
        text += "绑定" if self.bind else "不绑"
        text += f"{self.level}星"
        text += f"{self.name}"
        return text

    def __hash__(self):
        # 基于不可变字段计算哈希值
        return hash((self.name, self.level, self.bind))

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return (self.name, self.level, self.bind) == (other.name, other.level, other.bind)

