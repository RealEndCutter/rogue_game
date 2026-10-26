def weapon_damage(dice, bonus):
    if not dice:
        return f"+{bonus}" if bonus else ""
    count, sides = (int(part) for part in dice.split("d"))
    text = f"{count}-{count * sides}"
    if bonus:
        text += f" (+{bonus})"
    return text
