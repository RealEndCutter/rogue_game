import random

def attack(attacker, target, hit_bonus=0):
    result = False
    if check_hit(attacker, target, hit_bonus):
        damage = calculate_damage(attacker)
        apply_damage(target, damage)
        result = True
    return result        

def check_hit(attacker, target, hit_bonus=0):
    roll = random.randint(1, 20)

    threshold = 10 + target.agility - attacker.agility - hit_bonus
    threshold = max(2, min(20, threshold))

    return roll >= threshold

def roll_dice(dice):
    '''Бросок костей в записи Rogue: "3d4" — три кубика по 4 грани'''
    if not dice:
        return 0
    count, sides = (int(part) for part in dice.split("d"))
    return sum(random.randint(1, sides) for _ in range(count))


def calculate_damage(attacker):
    damage = attacker.strength

    weapon = getattr(attacker, "current_weapon", None)
    if weapon is not None:
        damage += roll_dice(getattr(weapon, "dice", "")) + weapon.strength

    return damage    


def apply_damage(target, damage):
    target.health -= damage

# расчет награды сделаю рандомной
def calculate_treasure_drop(enemy):
    max_health = getattr(enemy, "max_health", enemy.health)
    base = enemy.hostility + enemy.strength + enemy.agility + max_health // 2
    return random.randint(base // 2, base)

def is_dead(target):
    return target.health <= 0

def vampire_attack(vampire, character):
    hit = attack(vampire, character)

    if hit:
        character.max_health = max(1, character.max_health - 5)

        if character.health > character.max_health:
            character.health = character.max_health
    return hit

def is_first_vampire(enemy):
    first_hit = False
    if not enemy.first_hit_received:
        enemy.first_hit_received = True
        first_hit = True
    return first_hit            

def snake_mage_attack(enemy, character):
    hit = attack(enemy, character)
    sleep = False

    if hit:
        sleep = random.random() < 0.25 #вероятность усыпления 25%

    return hit, sleep    

def ogre_attack(enemy, character, guaranteed=False):
    hit = False

    if guaranteed:
        damage = calculate_damage(enemy)
        apply_damage(character, damage)
        hit = True
    else:
        hit = attack(enemy, character)
    return hit        