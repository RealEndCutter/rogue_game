import random as r

from collections import deque

from . import constants as gen
from .. import constants as game_constants
from ..models.room import Room
from ..models.corridor import Corridor
from ..models.level import Level
from ..models.difficulty import DynamicDifficulty
from ..models import enemy, item

DEFAULT_ENEMY_RANK = 0

def _enemy_power(stats):
    '''Сила врага по семму характеристик'''
    return stats["health"] + stats["agility"] + stats["strength"] + stats["hostility"]

def _enemy_sort_key(stats):
    return (stats.get("rank", DEFAULT_ENEMY_RANK), _enemy_power(stats))

class LevelGenerator:
    def __init__(self, game_data, spawn_enemies=True, spawn_locks=True):
        '''game_data коллекция врагов и предметов'''
        self.rng = r.Random()
        self.difficulty = DynamicDifficulty()
        self.spawn_enemies = spawn_enemies
        self.spawn_locks = spawn_locks

        self.enemies_data = game_data.load_enemies()
        self.items_data = game_data.load_items()

        self.enemy_order = sorted(
            self.enemies_data,
            key=lambda enemy_type: _enemy_sort_key(self.enemies_data[enemy_type])
        )

    def generate_room(self, index):
        '''Комната случайного размера и положения внутри сектора index'''
        col = index % gen.ROOMS_PER_SIDE
        row = index // gen.ROOMS_PER_SIDE

        # Левый верхний угол сектора
        sector_x = col * gen.SECTOR_WIDTH
        sector_y = row * gen.SECTOR_HEIGHT

        # Сначала размер, потом позиция в пределах, где комната помещается
        width = self.rng.randint(gen.MIN_ROOM_WIDTH, gen.MAX_ROOM_WIDTH)
        height = self.rng.randint(gen.MIN_ROOM_HEIGHT, gen.MAX_ROOM_HEIGHT)

        # Отступ 1 клетка от левого/верхнего края сектора и 1 от правого/нижнего
        x = self.rng.randint(sector_x + 1, sector_x + gen.SECTOR_WIDTH - 1 - width)
        y = self.rng.randint(sector_y + 1, sector_y + gen.SECTOR_HEIGHT - 1 - height)

        return Room(index=index, x=x, y=y, width=width, height=height)

    def generate(self, level_number, seed=None, difficulty=None):
        '''Генератор уровня'''
        self.rng = r.Random(f"{seed}:{level_number}") if seed is not None else r.Random()
        self.difficulty = difficulty or DynamicDifficulty()

        for _ in range(gen.MAX_GENERATION_ATTEMPTS):
            rooms = self.generate_rooms()
            edges = self.connect_rooms(rooms)
            corridors = self.generate_corridors(rooms, edges)
            if self.is_connected(rooms, corridors):
                break
        else:
            raise RuntimeError("Не удалось сгенерировать связный уровень")

        start_room = self.choose_start_room(rooms)
        exit_room = self.choose_exit_room(rooms, start_room)

        level = Level(
            number=level_number,
            rooms=rooms,
            corridors=corridors,
            start_room=start_room,
            exit_room=exit_room,
            start_position=rooms[start_room].get_random_position(self.rng),
            exit_position=rooms[exit_room].get_random_position(self.rng),
        )

        # Ключи кладём до врагов и предметов, чтобы они заняли клетки первыми
        keys_in_rooms = self.place_locks_and_keys(level) if self.spawn_locks else {}
        reachable = self.reachable_rooms(level.start_room, level.corridors, keys_in_rooms)
        if level.exit_room not in reachable:
            raise RuntimeError("Генерация замков сделала выход недостижимым")

        if self.spawn_enemies:
            self.place_enemies(level)
        self.place_items(level)

        return level

    def generate_rooms(self):
        '''Список из 9 комнат, комната i находится в секторе i'''
        return [self.generate_room(index) for index in range(gen.ROOMS_COUNT)]

    def _all_edges(self):
        '''Все 12 пар соседних по сетке комнат'''
        edges = []
        for i in range(gen.ROOMS_COUNT):
            if i % gen.ROOMS_PER_SIDE < gen.ROOMS_PER_SIDE - 1:
                edges.append((i, i + 1))
            if i < gen.ROOMS_COUNT - gen.ROOMS_PER_SIDE:
                edges.append((i, i + gen.ROOMS_PER_SIDE))
        return edges

    def _horizontal_corridor(self, left, right):
        # Клетка двери, любая на вертикальной стене
        door_a_y = self.rng.randint(left.y + 1, left.end_y - 1)
        door_b_y = self.rng.randint(right.y + 1, right.end_y - 1)

        # Добавляем двери
        left.doors[gen.ROOM_RIGHT] = (left.end_x, door_a_y)
        right.doors[gen.ROOM_LEFT] = (right.x, door_b_y)

        # Клетка изгиба. Любая между комнатами
        bend_x = self.rng.randint(left.end_x + 1, right.x - 1)

        path = []

        for x in range(left.end_x + 1, bend_x):
            path.append((x, door_a_y))

        step = 1 if door_b_y >= door_a_y else -1
        for y in range(door_a_y, door_b_y + step, step):
            path.append((bend_x, y))

        for x in range(bend_x + 1, right.x):
            path.append((x, door_b_y))

        return Corridor(
            left.index, right.index, path,
            door_a=left.doors[gen.ROOM_RIGHT],
            door_b=right.doors[gen.ROOM_LEFT],
        )

    def _vertical_corridor(self, top, bottom):
        # Возможные клетки двери на горизонтальной стенке
        door_a_x = self.rng.randint(top.x + 1, top.end_x - 1)
        door_b_x = self.rng.randint(bottom.x + 1, bottom.end_x - 1)

        # Добавляем двери
        top.doors[gen.ROOM_BOTTOM] = (door_a_x, top.end_y)
        bottom.doors[gen.ROOM_TOP] = (door_b_x, bottom.y)

        # Клетка изгиба. Любая между комнатами
        bend_y = self.rng.randint(top.end_y + 1, bottom.y - 1)

        path = []

        for y in range(top.end_y + 1, bend_y):
            path.append((door_a_x, y))

        step = 1 if door_b_x >= door_a_x else -1
        for x in range(door_a_x, door_b_x + step, step):
            path.append((x, bend_y))

        for y in range(bend_y + 1, bottom.y):
            path.append((door_b_x, y))

        return Corridor(
            top.index, bottom.index, path,
            door_a=top.doors[gen.ROOM_BOTTOM],
            door_b=bottom.doors[gen.ROOM_TOP],
        )

    def generate_corridors(self, rooms, edges):
        corridors = []
        for a, b in edges:
            if b - a == 1:
                corridors.append(self._horizontal_corridor(rooms[a], rooms[b]))
            else:
                corridors.append(self._vertical_corridor(rooms[a], rooms[b]))
        return corridors

    def connect_rooms(self, rooms):
        ''' Пары комнат, между которыми будут коридоры.
            Всегда связывают все 9 комнат + от 0 до gen.MAX_EXTRA_CORRIDORS лишних. '''

        edges = self._all_edges()
        self.rng.shuffle(edges)

        parent = list(range(gen.ROOMS_COUNT))

        def find(room):
            '''Корень группы: идём по старшим, пока не дойдём до того, кто сам себе старший'''
            while parent[room] != room:
                room = parent[room]
            return room

        tree = []   # пары, без которых связности не будет
        unused = [] # пары, которые соединили бы уже связанные комнаты

        for a, b in edges:
            root_a = find(a)
            root_b = find(b)

            if root_a != root_b:
                parent[root_a] = root_b
                tree.append((a, b))
            else:
                unused.append((a, b))

        # Дополнительные коридоры
        extra_count = self.rng.randint(0, min(gen.MAX_EXTRA_CORRIDORS, len(unused)))
        extra = self.rng.sample(unused, extra_count)

        return tree + extra

    def is_connected(self, rooms, corridors):
        '''Провери что из комнаты 0 по коридорам можно дойти до всех комнат'''

        neighbours = {room.index: [] for room in rooms}
        for corridor in corridors:
            neighbours[corridor.room_a].append(corridor.room_b)
            neighbours[corridor.room_b].append(corridor.room_a)

        visited = {0}
        queue = deque([0])
        while queue:
            current = queue.popleft()
            for room in neighbours[current]:
                if room not in visited:
                    visited.add(room)
                    queue.append(room)

        return len(visited) == len(rooms)

    def choose_start_room(self, rooms):
        return self.rng.randrange(len(rooms))

    def choose_exit_room(self, rooms, start_room):
        return self.rng.choice([room.index for room in rooms if room.index != start_room])

    def _max_enemies_per_room(self, level_number):
        '''Чем глубже уровень, тем выше потолок числа врагов в комнате'''
        steps = (level_number - 1) // gen.EXTRA_ENEMY_EVERY_N_LEVELS
        extra = steps * gen.ENEMIES_PER_ROOM_STEP
        return min(gen.MAX_ENEMIES_PER_ROOM + extra, gen.MAX_ENEMIES_PER_ROOM_CAP)

    def create_enemy(self, level_number, x, y):
        '''Создаёт случайного врага, характеристики растут вместе с уровнем'''
        last = len(self.enemy_order) - 1
        progress = (level_number - 1) / (game_constants.LEVELS_COUNT - 1)
        center = round(progress * last)

        offset = self.rng.randint(-gen.SPAWN_WINDOW_BELOW, gen.SPAWN_WINDOW_ABOVE)
        index = min(max(center + offset, 0), last)

        enemy_type = self.enemy_order[index]
        base = self.enemies_data[enemy_type]

        balance = self.difficulty.enemy_stats_multiplier
        health_scale = (1 + gen.ENEMY_HEALTH_SCALING * (level_number - 1)) * balance
        agility_scale = (1 + gen.ENEMY_AGILITY_SCALING * (level_number - 1)) * balance
        strength_scale = (1 + gen.ENEMY_STRENGTH_SCALING * (level_number - 1)) * balance

        new_enemy = enemy.Enemy(
            enemy_type=enemy_type,
            health=round(base["health"] * health_scale),
            agility=round(base["agility"] * agility_scale),
            strength=round(base["strength"] * strength_scale),
            hostility=round(base["hostility"]),
            x=x,
            y=y,
            symbol=base["symbol"],
        )
        if enemy_type == enemy.EnemyType.MIMIC:
            disguise_type, disguise_symbol = self.random_item_symbol()

            new_enemy.disguise_type = disguise_type
            new_enemy.disguise_symbol = disguise_symbol
        
        return new_enemy

    def place_enemies(self, level):
        '''Расставляет врагов по всем комнатам, кроме стартовой'''
        max_per_room = max(1, self._max_enemies_per_room(level.number) + self.difficulty.enemies_per_room_shift)

        for room in level.rooms:
            if room.index == level.start_room:
                continue

            enemy_count = self.rng.randint(gen.MIN_ENEMIES_PER_ROOM, max_per_room)
            for _ in range(enemy_count):
                cell = self._free_floor_cell(level, room)
                if cell is None:
                    break

                level.enemies.append(self.create_enemy(level.number, *cell))

    def _item_spawn_chance(self, level_number):
        '''Чем глубже уровень, тем реже встречаются полезные предметы'''
        chance = gen.ITEM_SPAWN_CHANCE_BASE - gen.ITEM_SPAWN_DECAY_PER_LEVEL * (level_number - 1)
        chance += self.difficulty.item_chance_shift
        return min(gen.ITEM_SPAWN_CHANCE_MAX, max(gen.ITEM_SPAWN_CHANCE_MIN, chance))

    def create_item(self, level_number=1):
        '''Создаёт случайный предмет'''
        weights = dict(self.items_data["weights"])
        weights["food"] = weights.get("food", 0) * self.difficulty.healing_weight_multiplier

        item_type = self.rng.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]

        variants = self.items_data[item_type]
        data = self.rng.choices(variants, weights=[v.get("weight", 1) for v in variants])[0]

        strength = data.get("strength", 0)
        if item_type == item.ItemType.WEAPON:
            strength += self._weapon_bonus(level_number)

        return item.Item(
            item_type=item_type,
            subtype=data["subtype"],
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            health=data.get("health", 0),
            max_health=data.get("max_health", 0),
            agility=data.get("agility", 0),
            strength=strength,
            value=data.get("value", 0),
            duration=data.get("duration", 0),
            dice=data.get("dice", ""),
        )

    def _weapon_bonus(self, level_number):
        '''Бонус к урону оружия: растёт с глубиной, как зачарование в Rogue'''
        max_bonus = (level_number - 1) // gen.WEAPON_BONUS_EVERY_N_LEVELS
        return self.rng.randint(max_bonus // 2, max_bonus)

    def reachable_rooms(self, start_room, corridors, keys_in_rooms):
        '''Комнаты, в которые можно попасть со старта, подбирая ключи по пути.'''
        have_keys = set()
        visited = {start_room}

        # Найденный ключ открывает новые коридоры, поэтому обходим заново,
        # пока не перестанут находиться новые комнаты
        changed = True
        while changed:
            changed = False
            for room in visited:
                have_keys.update(keys_in_rooms.get(room, []))

            queue = deque(visited)
            while queue:
                room = queue.popleft()
                for corridor in corridors:
                    if corridor.lock is not None and corridor.lock not in have_keys:
                        continue
                    if room == corridor.room_a:
                        other = corridor.room_b
                    elif room == corridor.room_b:
                        other = corridor.room_a
                    else:
                        continue
                    if other not in visited:
                        visited.add(other)
                        queue.append(other)
                        changed = True
        return visited

    def _locks_count(self, level_number):
        '''Сколько замков на уровне: растёт с глубиной, но не больше числа цветов'''
        if level_number < gen.LOCKS_START_LEVEL:
            return 0
        count = 1 + (level_number - gen.LOCKS_START_LEVEL) // gen.LEVELS_PER_EXTRA_LOCK
        return min(count, len(gen.KEY_COLORS))

    def place_locks_and_keys(self, level):
        '''Запирает выходы из группы комнат вокруг старта и кладёт ключ внутрь группы.'''
        keys_in_rooms = {}
        for color in gen.KEY_COLORS[:self._locks_count(level.number)]:
            for _ in range(gen.LOCK_PLACEMENT_ATTEMPTS):
                if self._try_lock_region(level, color, keys_in_rooms):
                    break
        return keys_in_rooms

    def _try_lock_region(self, level, color, keys_in_rooms):
        '''Одна попытка поставить замок цвета color. True, если получилось'''
        region = self._grow_region(level)
        if len(region) < 2:        # ключ нужно положить не в стартовую комнату
            return False

        # Все ещё открытые коридоры, ведущие из группы наружу. Запираем их все,
        # иначе замок можно обойти по другому коридору
        boundary = [
            c for c in level.corridors
            if c.lock is None and (c.room_a in region) != (c.room_b in region)
        ]
        if not boundary:
            return False
        for corridor in boundary:
            corridor.lock = color

        # Куда можно дойти без нового ключа: туда и кладём ключ (кроме стартовой).
        # Замок имеет смысл, только если без ключа до выхода не дойти
        reachable = self.reachable_rooms(level.start_room, level.corridors, keys_in_rooms)
        key_rooms = sorted(room for room in reachable if room != level.start_room)
        if key_rooms and level.exit_room not in reachable:
            key_room = self.rng.choice(key_rooms)
            if self._put_key(level, level.rooms[key_room], color):
                keys_in_rooms.setdefault(key_room, []).append(color)
                for corridor in boundary:
                    level.locked_doors[corridor.door_a] = color
                    level.locked_doors[corridor.door_b] = color
                return True

        for corridor in boundary:  # не подошло — снимаем замки
            corridor.lock = None
        return False

    def _grow_region(self, level):
        '''Случайная связная группа комнат вокруг старта без комнаты выхода.
        Растёт только по открытым коридорам'''
        target_size = self.rng.randint(2, len(level.rooms) - 1)
        region = {level.start_room}
        while len(region) < target_size:
            neighbours = set()
            for corridor in level.corridors:
                if corridor.lock is not None:
                    continue
                if corridor.room_a in region and corridor.room_b not in region:
                    neighbours.add(corridor.room_b)
                elif corridor.room_b in region and corridor.room_a not in region:
                    neighbours.add(corridor.room_a)
            neighbours.discard(level.exit_room)
            if not neighbours:
                break
            region.add(self.rng.choice(sorted(neighbours)))
        return region

    def _put_key(self, level, room, color):
        '''Кладёт ключ на свободную клетку пола комнаты. False, если места нет'''
        cell = self._free_floor_cell(level, room)
        if cell is None:
            return False
        key = item.Item(
            item_type=item.ItemType.KEY,
            subtype=color,
            name=gen.KEY_NAMES[color],
            symbol=gen.KEY_SYMBOL,
        )
        level.add_item(key, *cell)
        return True

    def _free_floor_cell(self, level, room):
        free_cells = [
            cell for cell in room.floor_cells()
            if cell != level.exit_position
            and level.get_item_at(*cell) is None
            and level.get_enemy_at(*cell) is None
        ]
        return self.rng.choice(free_cells) if free_cells else None

    def place_items(self, level):
        '''Расставляет предметы по всем комнатам, кроме стартовой'''
        chance = self._item_spawn_chance(level.number)

        for room in level.rooms:
            if room.index == level.start_room:
                continue

            for _ in range(gen.MAX_ITEMS_PER_ROOM):
                if self.rng.random() >= chance:
                    continue

                cell = self._free_floor_cell(level, room)
                if cell is None:
                    break

                level.add_item(self.create_item(level.number), *cell)
    
    #символ мимика
    def random_item_symbol(self):
        item_types = []

        for item_type in self.items_data:
            if item_type != "weights":
                item_types.append(item_type)

        disguise_type = self.rng.choice(item_types)
        item_data = self.rng.choice(self.items_data[disguise_type])

        return disguise_type, item_data["symbol"]            

