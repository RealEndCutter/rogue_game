from dataclasses import dataclass, field

@dataclass
class Corridor:
    room_a: int # Индекс первой комнаты
    room_b: int # Индекс второй комнаты

    # Путь коридора между комнатами
    path: list[tuple[int, int]] = field(default_factory=list)

    door_a: tuple[int, int] | None = None   # дверь коридора в комнате room_a
    door_b: tuple[int, int] | None = None   # дверь коридора в комнате room_b
    lock: str | None = None                 # цвет замка на обеих дверях или None

    def contains(self, x, y):
        '''Клетка (x, y) принадлежит коридору'''
        return (x, y) in self.path

    def get_cells(self):
        '''Все клетки коридора по порядку от двери A до двери B'''
        return self.path