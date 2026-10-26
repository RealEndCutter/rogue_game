from .. import constants as game_constants

# Сетка уровня 3 на 3
ROOMS_PER_SIDE = 3
ROOMS_COUNT = ROOMS_PER_SIDE * ROOMS_PER_SIDE 

# Размер сектора
SECTOR_WIDTH = game_constants.SCREEN_WIDTH // ROOMS_PER_SIDE           
SECTOR_HEIGHT = game_constants.SCREEN_HEIGHT // ROOMS_PER_SIDE         

# Размер карты
MAP_WIDTH = SECTOR_WIDTH * ROOMS_PER_SIDE                               
MAP_HEIGHT = SECTOR_HEIGHT * ROOMS_PER_SIDE                             

# Размер комнаты вместе со стенами.
# Минимум: 4x4 (пол 2x2).
# Максимум = сектор - 2: по 1 клетке отступа с каждой стороны сектора
MIN_ROOM_WIDTH = 4
MIN_ROOM_HEIGHT = 4
MAX_ROOM_WIDTH = SECTOR_WIDTH - 2                                    
MAX_ROOM_HEIGHT = SECTOR_HEIGHT - 2                                

# Сколько коридоров добавить сверх остовного дерева
MAX_EXTRA_CORRIDORS = 4

# Сколько раз пробовать сгенерировать уровень, если проверка связности не прошла
MAX_GENERATION_ATTEMPTS = 10

# Стороны комнаты (ключи словаря Room.doors)
ROOM_TOP = "top"
ROOM_RIGHT = "right"
ROOM_BOTTOM = "bottom"
ROOM_LEFT = "left"

# Сколько врагов может быть в одной комнате 
MIN_ENEMIES_PER_ROOM = 0
MAX_ENEMIES_PER_ROOM = 2

# Каждые EXTRA_ENEMY_EVERY_N_LEVELS уровней верхняя граница количества врагов
# в комнате растёт на ENEMIES_PER_ROOM_STEP, но не больше MAX_ENEMIES_PER_ROOM_CAP
EXTRA_ENEMY_EVERY_N_LEVELS = 5
ENEMIES_PER_ROOM_STEP = 1
MAX_ENEMIES_PER_ROOM_CAP = 5

# На сколько % растут характеристики врага за каждый уровень глубже первого
ENEMY_HEALTH_SCALING = 0.18
ENEMY_STRENGTH_SCALING = 0.08
ENEMY_AGILITY_SCALING = 0.03

# Сколько предметов максимум в одной комнате
MAX_ITEMS_PER_ROOM = 2

# Шанс появления отдельного предмета на уровне
ITEM_SPAWN_CHANCE_BASE = 0.6
ITEM_SPAWN_CHANCE_MIN = 0.15
ITEM_SPAWN_CHANCE_MAX = 0.9
ITEM_SPAWN_DECAY_PER_LEVEL = 0.02

# Окно спавна врагов
SPAWN_WINDOW_BELOW = 2
SPAWN_WINDOW_ABOVE = 1

# Двери и ключи
KEY_COLORS = ["red", "yellow", "blue"]   # порядок появления цветов
LOCKS_START_LEVEL = 3                    # с какого уровня появляется первый замок
LEVELS_PER_EXTRA_LOCK = 6                # +1 замок каждые N уровней, не больше количества цветов

KEY_NAMES = {"red": "Красный ключ", "yellow": "Жёлтый ключ", "blue": "Синий ключ"}
KEY_SYMBOL = "-"
LOCK_PLACEMENT_ATTEMPTS = 20               # сколько раз пробовать поставить один замок

# Оружие: +1 к максимальному бонусу урона каждые N уровней (на 21-м уровне до +6)
WEAPON_BONUS_EVERY_N_LEVELS = 3
