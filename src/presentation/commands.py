"""Команды для GameSession.handle. Presentation собирает dict, domain принимает так же."""


def move(dx, dy):
    return {"action": "move", "dx": dx, "dy": dy}


def use_item(category, index):
    return {"action": "use", "category": category, "index": index}


def unequip_weapon():
    return {"action": "use", "category": "weapons", "index": 0}
