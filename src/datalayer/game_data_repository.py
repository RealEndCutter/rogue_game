import json
from pathlib import Path

from domain.ports import GameDataRepository

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

class JsonGameDataRepository(GameDataRepository):
    '''Читает типы врагов и предметов из json'''

    def __init__(self, data_dir=DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)

    def load_enemies(self):
        return self._load("enemies.json")

    def load_items(self):
        return self._load("items.json")

    def _load(self, file_name):
        with open(self.data_dir / file_name, "r", encoding="utf-8") as file:
            return json.load(file)
