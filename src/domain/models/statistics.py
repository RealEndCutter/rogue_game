class Statistics:
    def __init__(self):
        self.treasures = 0         
        self.max_lvl = 1             
        self.enemies_defeated = 0
        self.food_eaten = 0
        self.elixirs_drunk = 0
        self.scrolls_read = 0
        self.hits_landed = 0        
        self.hits_missed = 0        
        self.tiles_walked = 0       

    def record_treasure(self, amount):
        self.treasures += amount

    def record_enemy_killed(self):
        self.enemies_defeated += 1

    def record_food_used(self):
        self.food_eaten += 1

    def record_elixir_used(self):
        self.elixirs_drunk += 1

    def record_scroll_used(self):
        self.scrolls_read += 1

    def record_hit_dealt(self):
        self.hits_landed += 1

    def record_hit_received(self):
        self.hits_missed += 1

    def record_step(self):
        self.tiles_walked += 1

    def set_reached_level(self, level):
        self.max_lvl = max(self.max_lvl, level)

    def snapshot(self):
        '''Копия счётчиков для меню и таблицы рекордов.
        Ключи совпадают с _STAT_LABELS в presentation/menu.py'''
        return {
            "treasures": self.treasures,
            "depth": self.max_lvl,
            "enemies_defeated": self.enemies_defeated,
            "food_eaten": self.food_eaten,
            "elixirs_drunk": self.elixirs_drunk,
            "scrolls_read": self.scrolls_read,
            "hits_landed": self.hits_landed,
            "hits_missed": self.hits_missed,
            "tiles_walked": self.tiles_walked,
        }