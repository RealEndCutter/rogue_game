from collections import deque

from domain.models.enemy import EnemyType
from domain.services.movement import move_enemy
from domain.services.visibility import bresenham_line

VAMPIRE_BLINK_CHANCE = 0.25
VAMPIRE_EXPOSED_HIT_BONUS = 5


def make_enemy_turn(enemy, game_state):
    player = game_state.character
    level = game_state.current_level
    rng = game_state.level_generator.rng

    if enemy.enemy_type == EnemyType.MIMIC and enemy.disguised:
        return

    if enemy.blink_home is not None:
        return_from_blink(enemy, level, player)
        return

    if enemy.enemy_type == EnemyType.OGRE and enemy.ogre_sleep:
        enemy.ogre_sleep = False
        enemy.guaranteed_attack = True
        game_state.enemy_message = "Z...z...z"
        return

    path = get_shortest_path(enemy, player, level)
    in_range = bool(path) and len(path) - 1 <= enemy.hostility

    if enemy.chasing and not in_range:
        enemy.chasing = False
    elif not enemy.chasing and in_range and can_see(enemy, player, level):
        enemy.chasing = True

    if enemy.enemy_type == EnemyType.GHOST:
        if enemy.chasing:
            enemy.ghost_visible = True
        else:
            enemy.ghost_turn += 1
            enemy.ghost_visible = enemy.ghost_turn % 2 == 1

    if enemy.enemy_type == EnemyType.VAMPIRE and try_vampire_blink(enemy, game_state, path, rng):
        return

    if enemy.chasing:
        chase_player(enemy, game_state, path)
    else:
        move_by_pattern(enemy, level, player, rng)


def can_see(enemy, player, level):
    line = bresenham_line((enemy.x, enemy.y), (player.x, player.y))
    return all(level.is_walkable(x, y) for x, y in line[1:-1])


def try_vampire_blink(enemy, game_state, path, rng):
    player = game_state.character
    level = game_state.current_level
    if not path or not 2 <= len(path) - 1 <= enemy.hostility:
        return False
    if not can_see(enemy, player, level) or rng.random() >= VAMPIRE_BLINK_CHANCE:
        return False

    spots = [
        (player.x + dx, player.y + dy)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        if level.is_walkable(player.x + dx, player.y + dy)
        and level.get_enemy_at(player.x + dx, player.y + dy) is None
    ]
    if not spots:
        return False

    enemy.blink_home = (enemy.x, enemy.y)
    enemy.x, enemy.y = rng.choice(spots)
    game_state.handle_enemy_attack(enemy)
    game_state.enemy_message = "Вампир метнулся к вам: " + game_state.enemy_message.lower()
    return True


def return_from_blink(enemy, level, player):
    home_x, home_y = enemy.blink_home
    enemy.blink_home = None
    home_free = level.get_enemy_at(home_x, home_y) is None and (home_x, home_y) != (player.x, player.y)
    if home_free:
        enemy.x, enemy.y = home_x, home_y

def chase_player(enemy, game_session, path):
    player = game_session.character
    level = game_session.current_level

    if len(path) > 1:
        next_x, next_y = path[1]

        if (next_x, next_y) == (player.x, player.y):
            game_session.handle_enemy_attack(enemy)
        else:
            dx = next_x - enemy.x
            dy = next_y - enemy.y

            move_enemy(enemy, level, player, dx, dy)

def move_by_pattern(enemy, level, player, rng):
    if get_enemy_room(enemy, level) is None:
        step_to_room(enemy, level, player)
    elif enemy.enemy_type == EnemyType.ZOMBIE:
        move_zombie(enemy, level, player, rng)
    elif enemy.enemy_type == EnemyType.VAMPIRE:
        move_vampire(enemy, level, player, rng)
    elif enemy.enemy_type == EnemyType.GHOST:
        move_ghost(enemy, level, player, rng)
    elif enemy.enemy_type == EnemyType.OGRE:
        move_orge(enemy, level, player, rng)
    elif enemy.enemy_type == EnemyType.SNAKE_MAGE:
        move_snake_mage(enemy, level, player)                            

def move_zombie(enemy, level, player, rng):
    directions = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1)
    ]

    dx, dy = rng.choice(directions)

    new_x = enemy.x + dx
    new_y = enemy.y + dy

    if move_in_room(enemy, level, player, new_x, new_y):
        enemy.x = new_x
        enemy.y = new_y

VAMPIRE_TURN_CHANCE = 0.1


def move_vampire(enemy, level, player, rng):
    room = get_enemy_room(enemy, level)
    path = room_perimeter(room)
    position = (enemy.x, enemy.y)

    if position not in path:
        target = min(path, key=lambda cell: abs(cell[0] - enemy.x) + abs(cell[1] - enemy.y))
        dx = (target[0] > enemy.x) - (target[0] < enemy.x)
        dy = (target[1] > enemy.y) - (target[1] < enemy.y) if dx == 0 else 0
        if move_in_room(enemy, level, player, enemy.x + dx, enemy.y + dy):
            enemy.x += dx
            enemy.y += dy
        return

    if rng.random() < VAMPIRE_TURN_CHANCE:
        enemy.patrol_direction = -enemy.patrol_direction

    index = path.index(position)
    next_x, next_y = path[(index + enemy.patrol_direction) % len(path)]
    if move_in_room(enemy, level, player, next_x, next_y):
        enemy.x, enemy.y = next_x, next_y
    else:
        enemy.patrol_direction = -enemy.patrol_direction


def room_perimeter(room):
    left, right = room.x + 1, room.end_x - 1
    top, bottom = room.y + 1, room.end_y - 1
    cells = [(x, top) for x in range(left, right + 1)]
    cells += [(right, y) for y in range(top + 1, bottom + 1)]
    cells += [(x, bottom) for x in range(right - 1, left - 1, -1)]
    cells += [(left, y) for y in range(bottom - 1, top, -1)]
    return list(dict.fromkeys(cells))

def move_ghost(enemy, level, player, rng):
    enemy_room = None
 
    for room in level.rooms:
        if (enemy.x, enemy.y) in room.floor_cells():
            enemy_room = room

    if enemy_room is not None:
        free_cells = []

        for x, y in enemy_room.floor_cells():
            if move_in_room(enemy, level, player, x, y):
                free_cells.append((x, y))

        if free_cells:
            enemy.x, enemy.y = rng.choice(free_cells)

def move_orge(enemy, level, player, rng):
    directions = [
        (2, 0),
        (-2, 0),
        (0, 2),
        (0, -2)
    ]

    dx, dy = rng.choice(directions)

    middle_x = enemy.x + dx // 2
    middle_y = enemy.y + dy // 2

    target_x = enemy.x + dx
    target_y = enemy.y + dy

    middle_free = move_in_room(enemy, level, player, middle_x, middle_y)

    target_free = move_in_room(enemy, level, player, target_x, target_y)

    if middle_free and target_free:
        enemy.x = target_x
        enemy.y = target_y

def move_snake_mage(enemy, level, player):
    dx = enemy.snake_side
    dy = enemy.snake_vertical

    new_x = enemy.x + dx
    new_y = enemy.y + dy

    if move_in_room(enemy, level, player, new_x, new_y):
        enemy.x = new_x
        enemy.y = new_y
    else:
        enemy.snake_vertical *= -1

        new_y = enemy.y + enemy.snake_vertical

        if move_in_room(enemy, level, player, new_x, new_y):
            enemy.x = new_x
            enemy.y = new_y

    enemy.snake_side *= -1

def can_visit_cell(level, enemy, cell, came_from):
    x, y = cell

    not_visited = cell not in came_from
    walkable = level.is_walkable(x, y)

    other_enemy = level.get_enemy_at(x, y)
    free_from_enemy = other_enemy is None or other_enemy is enemy

    return not_visited and walkable and free_from_enemy

def build_path(came_from, target):
    path = []
    current = target

    while current is not None:
        path.append(current)
        current = came_from[current]

    path.reverse()

    return path

def get_shortest_path(enemy, player, level):
    start = (enemy.x, enemy.y)
    target = (player.x, player.y)

    queue = deque([start])
    came_from = {start: None}

    directions = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1)
    ]

    found = False

    while queue and not found:
        current_x, current_y = queue.popleft()

        if (current_x, current_y) == target:
            found = True
        else:
            for dx, dy in directions:
                next_cell = (
                    current_x + dx,
                    current_y + dy
                )

                if can_visit_cell(level, enemy, next_cell, came_from):
                    came_from[next_cell] = (current_x, current_y)
                    queue.append(next_cell)

    path = []

    if target in came_from:
        path = build_path(came_from, target)

    return path
#для того чтобы не выходили в случайном перемещении за пределы комнаты
def get_enemy_room(enemy, level):
    enemy_room = None

    for room in level.rooms:
        if (enemy.x, enemy.y) in room.floor_cells():
            enemy_room = room
    return enemy_room

def move_in_room(enemy, level, player, x, y):
    room = get_enemy_room(enemy, level)
    can_move = False

    if room is not None:
        inside_room = (x, y) in room.floor_cells()
        free_from_enemy = level.get_enemy_at(x, y) is None
        not_player = (x, y) != (player.x, player.y)

        can_move = (inside_room and free_from_enemy and not_player)
    
    return can_move


def step_to_room(enemy, level, player):
    floor = {cell for room in level.rooms for cell in room.floor_cells()}
    start = (enemy.x, enemy.y)
    came_from = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current in floor:
            while came_from[current] != start:
                current = came_from[current]
            move_enemy(enemy, level, player, current[0] - enemy.x, current[1] - enemy.y)
            return
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cell = (current[0] + dx, current[1] + dy)
            if cell not in came_from and can_visit_cell(level, enemy, cell, came_from) and cell != (player.x, player.y):
                came_from[cell] = current
                queue.append(cell)
