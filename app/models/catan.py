"""
Модели для Catan (Enums и типы для игровой логики)
Эти модели используются для типизации, но данные хранятся в JSON в game_state
"""
import enum


class ResourceType(str, enum.Enum):
    """Типы ресурсов в Catan"""
    WOOD = "wood"      # Лес
    BRICK = "brick"    # Глина
    SHEEP = "sheep"    # Овца
    WHEAT = "wheat"    # Пшеница
    ORE = "ore"        # Камень
    DESERT = "desert"  # Пустыня


class HexType(str, enum.Enum):
    """Типы гексов"""
    FOREST = "forest"    # Лес
    HILLS = "hills"      # Холмы (глина)
    PASTURE = "pasture"  # Пастбище (овца)
    FIELDS = "fields"    # Поля (пшеница)
    MOUNTAINS = "mountains"  # Горы (камень)
    DESERT = "desert"    # Пустыня


class BuildingType(str, enum.Enum):
    """Типы построек"""
    SETTLEMENT = "settlement"  # Поселение
    CITY = "city"             # Город
    ROAD = "road"             # Дорога


class GamePhase(str, enum.Enum):
    """Фазы игры"""
    INITIAL_SETUP = "initial_setup"  # Начальная расстановка
    TURN = "turn"                    # Обычный ход
    FINISHED = "finished"            # Игра завершена


# Данные игрового поля (гексы, вершины, ребра, ресурсы) хранятся в JSON в game_state
# Эти модели не создают таблицы в БД, используются только для типизации через Enums выше

