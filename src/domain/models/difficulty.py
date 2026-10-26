MIN_LEVEL = -3
MAX_LEVEL = 3

STRUGGLE_HEALTH_RATIO = 0.35
DRAINED_MAX_HEALTH_RATIO = 0.6
EASY_HEALTH_RATIO = 0.8
EASY_MAX_HITS_TAKEN = 3

ENEMY_STATS_STEP = 0.08
ITEM_CHANCE_STEP = 0.07
HEALING_WEIGHT_STEP = 0.5


class DynamicDifficulty:
    def __init__(self, level=0):
        self.level = level

    def update(self, health, max_health, start_max_health, hits_taken):
        before = self.level
        health_ratio = health / max(max_health, 1)
        drained = max_health < start_max_health * DRAINED_MAX_HEALTH_RATIO
        if health_ratio < STRUGGLE_HEALTH_RATIO or drained:
            self.level -= 1
        elif health_ratio >= EASY_HEALTH_RATIO and hits_taken <= EASY_MAX_HITS_TAKEN:
            self.level += 1
        self.level = max(MIN_LEVEL, min(MAX_LEVEL, self.level))
        return self.level - before

    @property
    def enemy_stats_multiplier(self):
        return 1 + ENEMY_STATS_STEP * self.level

    @property
    def enemies_per_room_shift(self):
        if self.level >= 2:
            return 1
        if self.level <= -2:
            return -1
        return 0

    @property
    def item_chance_shift(self):
        return -ITEM_CHANCE_STEP * self.level

    @property
    def healing_weight_multiplier(self):
        return 1 + HEALING_WEIGHT_STEP * max(0, -self.level)
