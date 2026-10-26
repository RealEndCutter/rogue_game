def move_enemy(enemy, level, player, dx, dy):
    new_x = enemy.x + dx
    new_y = enemy.y + dy
    flag = False
    if can_move(level, player, new_x, new_y):
        enemy.x = new_x
        enemy.y = new_y
        flag = True
    return flag    


def can_move(level, player, x, y):
    '''На клетку можно встать: она проходимая и на ней нет врага и игрока'''
    not_player = (x, y) != (player.x, player.y)
    return level.is_walkable(x, y) and level.get_enemy_at(x, y) is None and not_player
