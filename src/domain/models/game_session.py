import random

from domain import constants
from domain.generation import constants as gen
from domain.models.item import Item, ItemType
from domain.models.enemy import Enemy, EnemyType
from domain.services import combat, inventory, movement, enemy_ai, visibility
from domain.models.character import Character
from domain.models.backpack import Backpack
from domain.models.statistics import Statistics
from domain.models.game_options import GameOptions
from domain.models.difficulty import DynamicDifficulty

START_MAX_HEALTH = 100

EMPTY_CHAR = " "
WALL_CHAR = "#"
FLOOR_CHAR = "."
DOOR_CHAR = "+"
CORRIDOR_CHAR = "░"
EXIT_CHAR = ">"

def _to_dict(obj):
    '''Копия всех полей объекта (Item, Enemy, Character, Statistics) словарём'''
    return dict(vars(obj))


_BLANK_OBJECTS = {
    Enemy: lambda: Enemy("", 0, 0, 0, 0, 0, 0),
    Item: lambda: Item("", ""),
    Character: lambda: Character(0, 0, 0, 0, 0, 0),
    Statistics: lambda: Statistics(),
}


def _from_dict(cls, data):
    '''Объект класса cls с полями из словаря.
    Сначала объект со значениями по умолчанию, потом поля из сохранения:
    поля, добавленные после сохранения, получают значения по умолчанию'''
    obj = _BLANK_OBJECTS[cls]() if cls in _BLANK_OBJECTS else cls.__new__(cls)
    obj.__dict__.update(data)
    return obj

class GameSession:

    def __init__(self, level_generator, save_repository, options=None):
        self.level_generator = level_generator
        self.save_repository = save_repository
        self.options = options or GameOptions()
        self.seed = self.options.seed if self.options.seed is not None else random.randrange(2 ** 32)


        self.game_over = False
        self.completed = False
        self.level_number = 0
        self.current_level = None
        self.player_sleeping = False

        self.character = None
        self.backpack = Backpack()
        self.statistics = Statistics()
        self.difficulty = DynamicDifficulty()
        self._hits_at_level_start = 0
        self._explored = set()

        self.player_message = ""
        self.enemy_message = ""
        
    def handle_player_attack(self, enemy):
        hit = False
        self.statistics.record_hit_dealt()
        if enemy.enemy_type == EnemyType.MIMIC:
            enemy.chasing = True

        if enemy.enemy_type == EnemyType.VAMPIRE and combat.is_first_vampire(enemy):
            self.player_message = "Первый удар по вампиру - промах!"
        else:

            old_health = enemy.health
            exposed = enemy.enemy_type == EnemyType.VAMPIRE and enemy.blink_home is not None
            bonus = enemy_ai.VAMPIRE_EXPOSED_HIT_BONUS if exposed else 0
            hit = combat.attack(self.character, enemy, bonus)

            if  hit:
                damage = old_health - enemy.health
                self.player_message = f"Вы нанесли {damage} урона"
                if combat.is_dead(enemy):
                    self.handle_enemy_dead(enemy)
            else:
                self.player_message = "Вы промахнулись"        

        return hit

    def handle_enemy_attack(self, enemy):
        old_health = self.character.health
        old_max_health = self.character.max_health

        if enemy.enemy_type == EnemyType.MIMIC:
            enemy.chasing = True
            hit = combat.attack(enemy, self.character)
        elif enemy.enemy_type == EnemyType.VAMPIRE:
            hit = combat.vampire_attack(enemy, self.character)
        elif enemy.enemy_type == EnemyType.SNAKE_MAGE:
            hit, sleep = combat.snake_mage_attack(enemy, self.character)
            if sleep:
                self.player_sleeping = True
        elif enemy.enemy_type == EnemyType.OGRE:
            ogre_counterattack = enemy.guaranteed_attack
            hit = combat.ogre_attack(enemy, self.character, enemy.guaranteed_attack)

            if enemy.guaranteed_attack:
                enemy.guaranteed_attack = False
            else:
                enemy.ogre_sleep = True    
        else:    
            hit = combat.attack(enemy,self.character)

        if hit:
            self.statistics.record_hit_received()
            damage = old_health - self.character.health
            if enemy.enemy_type == EnemyType.OGRE and ogre_counterattack:
                self.enemy_message = f"Контратака! Вам нанесли {damage} урона"
            elif enemy.enemy_type == EnemyType.VAMPIRE:
                max_health_loss = old_max_health - self.character.max_health
                self.enemy_message = (f"Вампир нанёс вам {damage} урона "
                                      f"и уменьшил максимальное HP на {max_health_loss}")
            else:
                self.enemy_message = f"Противник нанёс вам {damage} урона"
            if combat.is_dead(self.character):
                self.finish_game(completed=False)
        else:
            self.enemy_message = "Противник промахнулся"        

        return hit

    def handle_enemy_dead(self,enemy):
        treasure = combat.calculate_treasure_drop(enemy)
        self.character.add_treasures(treasure)
        self.statistics.record_enemy_killed()
        self.statistics.record_treasure(treasure)
        self.current_level.remove_enemy(enemy)
        self.enemy_message = f"Противник погиб"

    def handle_use_item(self, item):
        return inventory.use_item(self.character,self.backpack,item)

    def handle_equip_weapon(self, item):
        old_weapon = inventory.equip_weapon(
            self.character,
            self.backpack,
            item
        )

        if old_weapon is not None:
            x, y = self._free_neighbor_cell()
            self.current_level.add_item(old_weapon, x, y)

        return True

    def _free_neighbor_cell(self):
        '''Соседняя клетка, куда можно положить предмет. Если таких нет — клетка игрока'''
        level = self.current_level
        x, y = self.character.x, self.character.y
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            cell = (x + dx, y + dy)
            if (
                level.is_walkable(*cell)
                and level.get_item_at(*cell) is None
                and level.get_enemy_at(*cell) is None
                and not level.is_exit(*cell)
            ):
                return cell
        return x, y

    def handle_unequip_weapon(self):
        return inventory.unequip_weapon(self.character, self.backpack)

    def handle(self, command):
        '''Обработка команд от presentation'''
        if self.current_level is None or self.game_over:
            return

        if self.player_sleeping:
            self.player_sleeping = False
            self.player_message = "Z..z..z"
            self._end_turn()
            return

        action = command.get("action")
        
        if action == "move":
            x = self.character.x + command.get("dx", 0)
            y = self.character.y + command.get("dy", 0)

            color = self.current_level.lock_color(x, y)
            if color is not None:
                if not self._has_key(color):
                    self.player_message = f"Заперто. Нужен {gen.KEY_NAMES[color].lower()}"
                    return                      # ход не потрачен, враги не ходят
                self.current_level.unlock(color)
                self.player_message = f"{gen.KEY_NAMES[color]} открыл дверь"

            enemy = self.current_level.get_enemy_at(x, y)

            if enemy is not None:
                if enemy.enemy_type == EnemyType.MIMIC and enemy.disguised:
                    enemy.disguised = False
                    enemy.chasing = True
                    self.player_message = "Это оказался мимик!"
                else:
                    self.handle_player_attack(enemy)
                    self._end_turn()

            elif movement.can_move(self.current_level, self.character, x, y):
                self.character.x, self.character.y = x, y
                self.statistics.record_step()

                item = self.current_level.get_item_at(x,y)
                if item is not None:
                    picked_up = inventory.pick_up_item(
                        self.character,
                        self.backpack,
                        item
                    )

                    if picked_up:
                        self.current_level.remove_item(item)
                        if item.item_type == ItemType.KEY:
                            self.player_message = f"Подобран {item.name.lower()}"
                    else:
                        self.player_message = f"Рюкзак полон: {item.name}"

                if self.current_level.is_exit(x, y):
                    self.next_level()
                else:
                    self._end_turn()
        elif action == "use":
            if self.handle_inventory_command(command):
                self._end_turn()

    def _end_turn(self):
        '''После действия игрока: ход врагов и тик временных эффектов'''
        if not self.game_over:
            self.make_enemies_turn()
        if not self.game_over:
            inventory.update_temporary_effects(self.character)
                            
    def snapshot(self):
        '''Данные для отрисовки игры'''
        if self.current_level is None:
            return None

        level = self.current_level
        character = self.character
        tiles = self._build_tiles()
        if self.options.fog_of_war:
            visible = visibility.get_visible_cells(character, level, tiles)
        else:
            visible = {
                (x, y)
                for y, row in enumerate(tiles)
                for x, char in enumerate(row)
                if char != EMPTY_CHAR
            }
        self._explored = visibility.update_explored_area(self._explored, visible)

        return {
            "level_index": self.level_number,
            "tiles": tiles,
            "player": {
                "x": character.x,
                "y": character.y,
                "health": character.health,
                "max_health": character.max_health,
                "agility": character.agility,
                "strength": character.strength,
                "weapon": ({"name": character.current_weapon.name,
                        "strength": character.current_weapon.strength,
                        "dice": getattr(character.current_weapon, "dice", "")}
                    if character.current_weapon is not None
                    else None),
            },
            "enemies": [{"x": e.x, "y": e.y, "kind": e.enemy_type,
                        "symbol": (e.disguise_symbol if e.enemy_type == EnemyType.MIMIC and e.disguised else e.symbol),
                        "disguised": e.disguised,
                        "disguise_type": e.disguise_type,
                        "ghost_visible": e.ghost_visible,
                        } for e in level.enemies],
            "items": [
                {
                    "x": i.x, "y": i.y, "kind": i.item_type, "symbol": i.symbol,
                    "color": i.subtype if i.item_type == ItemType.KEY else None,
                }
                for i in level.items
            ],
            "locked_doors": [
                {"x": x, "y": y, "color": color} for (x, y), color in level.locked_doors.items()
            ],
            "keys": [key.subtype for key in self.backpack.get_items_by_type(ItemType.KEY)],
            "treasures": character.treasures,
            "player_message": self.player_message,
            "enemy_message": self.enemy_message,
            "backpack": self._backpack_snapshot(),
            "visible": [[x, y] for x, y in visible],
            "explored": [[x, y] for x, y in self._explored],
        }

    def _build_tiles(self):
        '''Карта уровня строками'''
        level = self.current_level
        grid = [[EMPTY_CHAR] * gen.MAP_WIDTH for _ in range(gen.MAP_HEIGHT)]

        for room in level.rooms:
            for y in range(room.y, room.end_y + 1):
                for x in range(room.x, room.end_x + 1):
                    is_wall = x in (room.x, room.end_x) or y in (room.y, room.end_y)
                    grid[y][x] = WALL_CHAR if is_wall else FLOOR_CHAR
        for corridor in level.corridors:
            for x, y in corridor.path:
                grid[y][x] = CORRIDOR_CHAR
        for room in level.rooms:
            for x, y in room.doors.values():
                grid[y][x] = DOOR_CHAR

        exit_x, exit_y = level.exit_position
        grid[exit_y][exit_x] = EXIT_CHAR

        return ["".join(row) for row in grid]

    def start_new_game(self):
        self.game_over = False
        self.completed = False

        self.character = Character(
            max_health = START_MAX_HEALTH,
            health = START_MAX_HEALTH,
            agility = 10,
            strength = 10,
            x = 0,
            y = 0,
        )

        self.backpack = Backpack()
        self.statistics = Statistics()
        self.difficulty = DynamicDifficulty()
        self.level_number = self.options.start_level
        self._explored = set()
        self._enter_level(self.level_number)

    def next_level(self):
        self.backpack.remove_item_by_type(ItemType.KEY)
        if self.level_number >= constants.LEVELS_COUNT:
            self.finish_game(completed=True)
            return

        self._update_difficulty()
        self.level_number += 1
        self._enter_level(self.level_number)

    def _update_difficulty(self):
        if not self.options.dynamic_difficulty:
            return 0
        hits_taken = self.statistics.hits_missed - self._hits_at_level_start
        return self.difficulty.update(
            self.character.health,
            self.character.max_health,
            START_MAX_HEALTH,
            hits_taken,
        )

    def _enter_level(self, level_number):
        difficulty = self.difficulty if self.options.dynamic_difficulty else None
        self.current_level = self.level_generator.generate(level_number, self.seed, difficulty)
        self._hits_at_level_start = self.statistics.hits_missed
        self.character.x, self.character.y = self.current_level.start_position
        self.statistics.set_reached_level(level_number)
        self._explored = set()
        self.player_message = ""
        self.enemy_message = ""
        self._save_progress()

    def finish_game(self, completed):
        '''Конец попытки: completed=True — победа, False — смерть'''
        if self.game_over:       
            return
        self.completed = completed
        self.game_over = True
        self.save_repository.save_statistics(self.statistics.snapshot())
        self.save_repository.clear()

    def make_enemies_turn(self):
        for enemy in self.current_level.enemies.copy():
            if not self.game_over:
                enemy_ai.make_enemy_turn(enemy, self)

    def is_game_completed(self):
        return self.completed

    def is_game_over(self):
        return self.game_over

    def get_run_stats(self):
        return self.statistics.snapshot()

    @staticmethod
    def get_last_run(save_repository):
        '''Статистика последней законченной попытки или {}'''
        runs = save_repository.load_statistics()
        return runs[-1] if runs else {}

    @staticmethod
    def get_leaderboard(save_repository):
        '''Все попытки, лучшие по сокровищам первыми'''
        runs = save_repository.load_statistics()
        return sorted(runs, key=lambda run: run["treasures"], reverse=True)

    def _save_progress(self):
        self.save_repository.save(self.to_state())

    def to_state(self):
        character = _to_dict(self.character)
        weapon = self.character.current_weapon
        character["current_weapon"] = _to_dict(weapon) if weapon is not None else None
        character["active_effects"] = [dict(effect) for effect in self.character.active_effects]

        return {
            "seed": self.seed,
            "level_number": self.level_number,
            "player_sleeping": self.player_sleeping,
            "character": character,
            "backpack": [_to_dict(item) for item in self.backpack.get_items()],
            "statistics": _to_dict(self.statistics),
            "enemies": [_to_dict(enemy) for enemy in self.current_level.enemies],
            "items": [_to_dict(item) for item in self.current_level.items],
            "explored": [[x, y] for x, y in self._explored],
            "locked_doors": [[x, y, color] for (x, y), color in self.current_level.locked_doors.items()],
            "difficulty": self.difficulty.level,
            "hits_at_level_start": self._hits_at_level_start,
        }

    def continue_game(self):
        state = self.save_repository.load()
        if not state:
            return False
        self._restore_state(state)
        return True

    def _restore_state(self, state):
        self.seed = state["seed"]
        self.level_number = state["level_number"]
        self.player_sleeping = state["player_sleeping"]
        self.game_over = False
        self.completed = False

        character_data = dict(state["character"])
        weapon_data = character_data.pop("current_weapon")
        self.character = _from_dict(Character, character_data)
        self.character.current_weapon = _from_dict(Item, weapon_data) if weapon_data else None

        self.backpack = Backpack()
        for item_data in state["backpack"]:
            self.backpack.add_item(_from_dict(Item, item_data))

        self.statistics = _from_dict(Statistics, state["statistics"])
        self.difficulty = DynamicDifficulty(state.get("difficulty", 0))
        self._hits_at_level_start = state.get("hits_at_level_start", self.statistics.hits_missed)
        
        self.current_level = self.level_generator.generate(self.level_number, self.seed)
        self.current_level.enemies = [_from_dict(Enemy, data) for data in state["enemies"]]
        if not self.options.spawn_enemies:
            self.current_level.enemies = []
        self.current_level.items = [_from_dict(Item, data) for data in state["items"]]
        self._explored = {tuple(cell) for cell in state["explored"]}

        self.current_level.locked_doors = {
            (x, y): color for x, y, color in state.get("locked_doors", [])
        }
        if not self.options.spawn_locks:
            self.current_level.locked_doors = {}

        self.player_message = ""
        self.enemy_message = ""

    def _backpack_snapshot(self):
        return {
            "food": [
                {"name": item.name,
                "health": item.health,}
                for item in self.backpack.get_items_by_type(ItemType.FOOD)
            ],
            "elixirs": [
                {"name": item.name,
                "max_health": item.max_health,
                "agility": item.agility,
                "strength": item.strength,
                "duration": item.duration,}
                for item in self.backpack.get_items_by_type(ItemType.ELIXIR)],
            "scrolls": [
                {"name": item.name,
                "max_health": item.max_health,
                "agility": item.agility,
                "strength": item.strength,}
                for item in self.backpack.get_items_by_type(ItemType.SCROLL)
            ],
            "weapons": [
                {"name": item.name,
                "strength": item.strength,
                "dice": getattr(item, "dice", ""),}
                for item in self.backpack.get_items_by_type(ItemType.WEAPON)
            ],
        }

    def handle_inventory_command(self, command):
        category = command.get("category")
        index = command.get("index")

        item_types = {
            "food": ItemType.FOOD,
            "elixirs": ItemType.ELIXIR,
            "scrolls": ItemType.SCROLL,
            "weapons": ItemType.WEAPON,
        }

        item_type = item_types.get(category)
        acted = False

        if item_type is not None:
            if item_type == ItemType.WEAPON and index == 0:
                acted = self.handle_unequip_weapon()
            else:
                item = self.backpack.get_item_in_slot(item_type, index)

                if item is not None:
                    if item_type == ItemType.WEAPON:
                        acted = self.handle_equip_weapon(item)
                    elif self.handle_use_item(item):
                        self._record_item_used(item_type)
                        acted = True
        return acted

    def _has_key(self, color):
        '''В рюкзаке есть ключ этого цвета'''
        keys = self.backpack.get_items_by_type(ItemType.KEY)
        return any(key.subtype == color for key in keys)

    def _record_item_used(self, item_type):
        if item_type == ItemType.FOOD:
            self.statistics.record_food_used()
        elif item_type == ItemType.ELIXIR:
            self.statistics.record_elixir_used()
        elif item_type == ItemType.SCROLL:
            self.statistics.record_scroll_used()