class ItemType:
    TREASURE = "treasure"
    FOOD = "food"
    ELIXIR = "elixir"
    SCROLL = "scroll"
    WEAPON = "weapon"
    KEY = "key"             

class Item:
    def __init__(
        self,
        item_type,
        subtype, # subtype цвет ключа: "red", "yellow", "blue"
        name="",
        symbol="",
        max_health=0,
        health=0,
        agility=0,
        strength=0,
        value=0,
        duration=0,
        x=None,
        y=None,
        dice=""
    ):
        self.item_type = item_type
        self.subtype = subtype
        self.name = name
        self.symbol = symbol
        self.max_health = max_health
        self.health = health
        self.agility = agility
        self.strength = strength
        self.value = value
        self.duration = duration
        self.x = x
        self.y = y
        self.dice = dice                # кости урона оружия, например "3d4"
