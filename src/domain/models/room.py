
from dataclasses import dataclass, field

@dataclass
class Room:
    index: int  # Номер сектора
    x: int      # координаты по горизонтали
    y: int      # координаты по вертикали
    width: int  # размер комнаты по горизонтали
    height: int # размер комнаты по вертикали
    doors: dict = field(default_factory=dict) # сторона: клетка двери


    @property
    def end_x(self):
        '''Координата x правой стенки комнаты'''
        return self.x + self.width - 1

    @property
    def end_y(self):
        '''Координата y нижней стенки комнаты'''
        return self.y + self.height - 1

    def contains(self, x, y):
        '''Проверка что текущая клетка в комнате'''
        return self.x < x < self.end_x and self.y < y < self.end_y
    
    def get_random_position(self, rng):
        '''Возвращает случайную точку из комнаты'''
        return rng.choice(self.floor_cells())

    def floor_cells(self):
        '''Список всех клеток пола комнаты (без стен)'''
        return [
            (x, y)
            for y in range(self.y + 1, self.end_y)
            for x in range(self.x + 1, self.end_x)
        ]