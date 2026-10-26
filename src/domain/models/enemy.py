class EnemyType:
    ZOMBIE = "zombie"
    VAMPIRE = "vampire"
    GHOST = "ghost"
    OGRE = "ogre"
    SNAKE_MAGE = "snake_mage"
    MIMIC = "mimic"

class Enemy:

    def __init__(self, enemy_type, health, agility, strength, hostility, x, y, symbol = ""):
        self.enemy_type = enemy_type
        self.health = health
        self.max_health = health
        self.agility = agility
        self.strength = strength
        self.hostility = hostility
        self.x = x
        self.y = y
        self.symbol = symbol

        self.first_hit_received = False
        self.ogre_sleep = False
        self.guaranteed_attack = False
        self.chasing = False
        self.blink_home = None
        self.patrol_direction = 1

        self.ghost_visible = True
        self.ghost_turn = 0

        self.snake_vertical = 1
        self.snake_side = 1

        #все что ниже только для мимика
        self.disguised = enemy_type == EnemyType.MIMIC
        self.disguise_symbol = ""
        self.disguise_type = ""
   