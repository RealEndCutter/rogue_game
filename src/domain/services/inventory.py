from domain.models.item import ItemType

def pick_up_item(character, backpack, item):
    flag = False
    if item.item_type == ItemType.TREASURE:
        character.add_treasures(item.value)
        flag = True
    elif backpack.add_item(item):
        flag = True
    return flag    


def use_item(character, backpack, item):
    flag = False
    if item.item_type == ItemType.FOOD:
        flag = use_food(character, backpack, item)
    elif item.item_type == ItemType.SCROLL:
        flag = use_scroll(character, backpack, item)
    elif item.item_type == ItemType.ELIXIR:
        flag = use_elixir(character, backpack, item)
    
    return flag               


def use_food(character, backpack, item):
    character.heal(item.health)
    backpack.remove_item(item)

    return True   

def use_elixir(character, backpack, item):
    flag = False
    if item.strength > 0:
        character.increase_strength(item.strength)
        effect = {"attribute": "strength", "amount": item.strength, "turns_left": item.duration}
        character.active_effects.append(effect)
        flag = True
    elif item.agility > 0:
        character.increase_agility(item.agility)
        effect = {"attribute": "agility", "amount": item.agility, "turns_left": item.duration}
        character.active_effects.append(effect)
        flag = True
    elif item.max_health > 0:
        character.increase_max_health(item.max_health)
        effect = {"attribute": "max_health", "amount": item.max_health, "turns_left": item.duration}
        character.active_effects.append(effect)
        flag = True
    if flag:
        backpack.remove_item(item)
    return flag    

def update_temporary_effects(character):
    for effect in character.active_effects.copy():
        effect["turns_left"] -= 1
        if effect["turns_left"] <= 0:
            remove_effect(effect, character)

def remove_effect(effect, character):
    if effect["attribute"] == "strength":
        character.strength -= effect["amount"]
    elif effect["attribute"] == "agility":
        character.agility -= effect["amount"]
    elif effect["attribute"] == "max_health":
        character.max_health = max(1, character.max_health - effect["amount"])
        character.health -= effect["amount"]
        if character.health <= 0:
            character.health = 1
    character.active_effects.remove(effect)            

def use_scroll(character, backpack, item):
    flag = False
    if item.strength > 0:
        character.increase_strength(item.strength)
        flag = True
    elif item.agility > 0:
        character.increase_agility(item.agility)
        flag = True
    elif item.max_health > 0:
        character.increase_max_health(item.max_health)
        flag = True

    if flag:
        backpack.remove_item(item)
    return flag                

def equip_weapon(character, backpack, item):
    old_weapon = None

    if item.item_type == ItemType.WEAPON and item in backpack.get_items():
        old_weapon = character.current_weapon
        backpack.remove_item(item)
        character.current_weapon = item
    
    return old_weapon

def unequip_weapon(character, backpack):
    flag = True
    if character.current_weapon is None:
        flag = False
    else:
        if backpack.add_item(character.current_weapon):
            character.current_weapon = None
        else:
            flag = False
    return flag                
