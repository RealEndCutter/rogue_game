import argparse

from datalayer.game_data_repository import JsonGameDataRepository
from datalayer.save_manager import JsonSaveRepository
from domain import constants
from domain.generation.level_generator import LevelGenerator
from domain.models.game_options import GameOptions
from domain.models.game_session import GameSession
from presentation.controller import Controller


def level_number(text):
    value = int(text)
    if not 1 <= value <= constants.LEVELS_COUNT:
        raise argparse.ArgumentTypeError(
            f"уровень должен быть от 1 до {constants.LEVELS_COUNT}, получено {value}"
        )
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="python3 main.py",
        description="Rogue: консольный рогалик по мотивам Rogue 1980.",
        epilog="Параметры действуют только для «1. Новая игра»."
    )
    parser.add_argument(
        "--lvl", type=level_number, default=1, metavar="N",
        help=f"начать новую игру с уровня N (1..{constants.LEVELS_COUNT})",
    )
    parser.add_argument(
        "--seed", type=int, default=None, metavar="SEED",
        help="сгенерировать уровень по seed",
    )
    parser.add_argument(
        "--smog-off", action="store_true",
        help="отключить туман войны",
    )
    parser.add_argument(
        "--enemy-off", action="store_true",
        help="не создавать врагов на уровнях",
    )
    parser.add_argument(
        "--locks-off", action="store_true",
        help="не создавать запертые двери и ключи",
    )
    parser.add_argument(
        "--balance-off", action="store_true",
        help="отключить динамическую сложность",
    )
    parser.add_argument(
        "--3d", dest="mode_3d", action="store_true",
        help="3D-режим: вид от первого лица и мини-карта (W/S шаг, A/D поворот)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    options = GameOptions(
        start_level=args.lvl,
        seed=args.seed,
        fog_of_war=not args.smog_off,
        spawn_enemies=not args.enemy_off,
        spawn_locks=not args.locks_off,
        dynamic_difficulty=not args.balance_off,
    )

    game_data = JsonGameDataRepository()
    saves = JsonSaveRepository()

    def new_session():
        generator = LevelGenerator(
            game_data,
            spawn_enemies=options.spawn_enemies,
            spawn_locks=options.spawn_locks,
        )
        return GameSession(generator, saves, options=options)

    if args.mode_3d:
        # Отдельный фронтенд: импортируем, только когда он нужен
        from presentation3d.controller3d import Controller3D
        Controller3D(new_session, saves).run()
    else:
        Controller(new_session, saves).run()


if __name__ == "__main__":
    main()
