import json
from pathlib import Path

from domain.ports import SaveRepository

DEFAULT_SAVE_DIR = Path(__file__).resolve().parents[1] / "saves"

SAVE_FILE = "save.json"
STATISTICS_FILE = "statistics.json"


class JsonSaveRepository(SaveRepository):
    def __init__(self, save_dir=DEFAULT_SAVE_DIR):
        self.save_dir = Path(save_dir)

    def save(self, game_state):
        self._write(SAVE_FILE, game_state)

    def load(self):
        return self._read(SAVE_FILE, default=None)

    def clear(self):
        path = self.save_dir / SAVE_FILE
        if path.exists():
            path.unlink()

    def save_statistics(self, statistics):
        runs = self.load_statistics()
        runs.append(statistics)
        self._write(STATISTICS_FILE, runs)

    def load_statistics(self):
        return self._read(STATISTICS_FILE, default=[])

    def _read(self, file_name, default):
        path = self.save_dir / file_name
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, file_name, data):
        self.save_dir.mkdir(parents=True, exist_ok=True)
        with open(self.save_dir / file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
