# Интерфейс справочных данных игры (типы врагов, предметы).
class GameDataRepository:
    def load_enemies(self):
        '''{тип врага: {"health", "agility", "strength", "hostility", ...}}'''
        raise NotImplementedError

    def load_items(self):
        '''{"weights": {тип: вес}, тип: [{"subtype", "name", ...}, ...]}'''
        raise NotImplementedError


# Интерфейс хранения прогресса и рекордов.
# Реализация живёт в datalayer, domain знает только этот интерфейс.
class SaveRepository:
    def save(self, game_state):
        '''Сохранить состояние текущей игры (словарь из простых типов)'''
        raise NotImplementedError

    def load(self):
        '''Состояние последней сохранённой игры или None, если сохранения нет'''
        raise NotImplementedError

    def clear(self):
        '''Удалить сохранение (игра закончилась смертью или победой)'''
        raise NotImplementedError

    def save_statistics(self, statistics):
        '''Добавить результат одной попытки в таблицу рекордов'''
        raise NotImplementedError

    def load_statistics(self):
        '''Список результатов всех попыток'''
        raise NotImplementedError
