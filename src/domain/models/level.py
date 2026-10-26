from dataclasses import dataclass, field

from .room import Room
from .corridor import Corridor
from .enemy import Enemy, EnemyType
from .item import Item, ItemType

@dataclass
class Level:
    number: int
    rooms: list[Room]
    corridors: list[Corridor]
    start_room: int     # Индекс стартовой комнаты
    exit_room: int      # Индекс комнаты с выходом
    start_position: tuple[int, int] # Точ-ка появления игрока
    exit_position: tuple[int, int]  # Клетка перехода на следующий lvl

    enemies: list[Enemy] = field(default_factory=list) # Враги на уровне
    items: list[Item] = field(default_factory=list)    # Предметы на уровне

    # Запертые двери: клетка двери -> цвет замка
    locked_doors: dict[tuple[int, int], str] = field(default_factory=dict)

    # Все проходимые клетки. Не передаётся в конструктор, считается в __post_init__
    walkable: set[tuple[int, int]] = field(init=False, default_factory=set)

    def __post_init__(self):
        self.walkable = self._collect_walkable()

    def _collect_walkable(self):
        '''Собираем пол всех комнат + двери + клетки коридоров'''
        cells = set()
        for room in self.rooms:
            cells.update(room.floor_cells())
            cells.update(room.doors.values())
        for corridor in self.corridors:
            cells.update(corridor.path)
        return cells

    def is_walkable(self, x, y):
        '''Проверка, что данная ячейка игровая. Запертая дверь непроходима'''
        return (x, y) in self.walkable and (x, y) not in self.locked_doors

    def lock_color(self, x, y):
        '''Цвет замка на клетке (x, y) или None, если там нет запертой двери'''
        return self.locked_doors.get((x, y))

    def unlock(self, color):
        '''Открыть все двери этого цвета (ключ не тратится, как в DOOM)'''
        self.locked_doors = {
            cell: lock for cell, lock in self.locked_doors.items() if lock != color
        }

    def get_enemy_at(self, x, y):
        '''Возвращает противника, стоящего на клетке (x, y), либо None'''
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                return enemy
        return None

    def get_item_at(self, x, y):
        '''Возвращает предмет, лежащий на клетке (x, y), либо None'''
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None

    def remove_enemy(self, enemy):
        '''Убриает убитого/исчезнувшего противника с уровня'''
        if enemy in self.enemies:
            self.enemies.remove(enemy)

    def remove_item(self, item):
        '''Убрает предмет с уровня '''
        if item in self.items:
            self.items.remove(item)
            item.x = None
            item.y = None

    def add_item(self, item, x, y):
        '''Кладёт предмет на клетку (x, y) уровня'''
        item.x = x
        item.y = y
        self.items.append(item)

    def is_exit(self, x, y):
        return (x, y) == self.exit_position

    def get_start_position(self):
        return self.start_position