from dataclasses import dataclass


@dataclass(frozen=True)
class GameOptions:
    start_level: int = 1       # с какого уровня начинать новую игру
    seed: int | None = None    # seed уровней. None — случайный для каждой новой игры
    fog_of_war: bool = True    # False вся карта видна сразу
    spawn_enemies: bool = True # False врагов на уровнях нет
    spawn_locks: bool = True   # False — без запертых дверей и ключей
    dynamic_difficulty: bool = True
