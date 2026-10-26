class Character:
    def __init__(self, max_health, health, agility, strength, x, y):
        self.max_health = max_health
        self.health = health
        self.agility = agility
        self.strength = strength
        self.x = x
        self.y = y

        self.active_effects = []
        self.current_weapon = None
        self.treasures = 0

    def heal(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health

    def increase_max_health(self, amount):
        self.max_health += amount
        self.heal(amount)

    def increase_agility(self, amount):
        self.agility += amount

    def increase_strength(self, amount):
        self.strength += amount

    def add_treasures(self, amount):
        self.treasures += amount
