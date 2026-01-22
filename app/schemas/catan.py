from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.models.catan import HexType, BuildingType, ResourceType


class DiceRollRequest(BaseModel):
    """Запрос на бросок кубиков"""
    pass


class DiceRollResponse(BaseModel):
    """Ответ на бросок кубиков"""
    dice_roll: int
    game_state: Dict[str, Any]


class BuildSettlementRequest(BaseModel):
    """Запрос на строительство поселения"""
    vertex_id: int


class BuildCityRequest(BaseModel):
    """Запрос на строительство города"""
    vertex_id: int


class BuildRoadRequest(BaseModel):
    """Запрос на строительство дороги"""
    vertex1_id: int
    vertex2_id: int


class BuildResponse(BaseModel):
    """Ответ на строительство"""
    success: bool
    message: str
    resources: Dict[str, int]
    victory_points: int
    game_state: Dict[str, Any]


class StartGameRequest(BaseModel):
    """Запрос на запуск игры"""
    game_id: int


class StartGameResponse(BaseModel):
    """Ответ на запуск игры"""
    success: bool
    message: str
    game_state: Dict[str, Any]


class GameActionRequest(BaseModel):
    """Базовый класс для игровых действий"""
    action: str  # "roll_dice", "build_settlement", "build_city", "build_road"
    data: Dict[str, Any]


class GameStateResponse(BaseModel):
    """Текущее состояние игры"""
    game_state: Dict[str, Any]
    current_player_id: int
    phase: str
    winner: Optional[int] = None


class MoveRobberRequest(BaseModel):
    """Запрос на перемещение разбойника"""
    hex_index: int
    steal_from_player_id: Optional[int] = None


class MoveRobberResponse(BaseModel):
    """Ответ на перемещение разбойника"""
    success: bool
    message: str
    new_location: int
    stolen_resource: Optional[str] = None
    game_state: Dict[str, Any]


class TradeWithBankRequest(BaseModel):
    """Запрос на торговлю с банком"""
    give_resource: str
    give_amount: int = 4
    take_resource: str
    take_amount: int = 1


class TradeWithBankResponse(BaseModel):
    """Ответ на торговлю с банком"""
    success: bool
    message: str
    resources: Dict[str, int]
    game_state: Dict[str, Any]


class TradeWithPortRequest(BaseModel):
    """Запрос на торговлю через порт"""
    vertex_id: int
    give_resource: str
    give_amount: int
    take_resource: str
    take_amount: int = 1


class TradeWithPortResponse(BaseModel):
    """Ответ на торговлю через порт"""
    success: bool
    message: str
    resources: Dict[str, int]
    game_state: Dict[str, Any]


class CreateTradeOfferRequest(BaseModel):
    """Запрос на создание предложения торговли"""
    give_resources: Dict[str, int]
    want_resources: Dict[str, int]


class AcceptTradeOfferRequest(BaseModel):
    """Запрос на принятие предложения торговли"""
    trade_offer_id: int


class TradeOfferResponse(BaseModel):
    """Ответ на предложение торговли"""
    success: bool
    message: str
    trade_offer: Optional[Dict[str, Any]] = None
    game_state: Dict[str, Any]


class BuyDevCardResponse(BaseModel):
    """Ответ на покупку развивающей карты"""
    success: bool
    message: str
    card: str
    revealed: bool
    resources: Dict[str, int]
    game_state: Dict[str, Any]


class PlayDevCardRequest(BaseModel):
    """Запрос на использование развивающей карты"""
    card_type: str
    card_data: Optional[Dict[str, Any]] = None  # Для YEAR_OF_PLENTY, MONOPOLY


class PlayDevCardResponse(BaseModel):
    """Ответ на использование развивающей карты"""
    success: bool
    message: str
    game_state: Dict[str, Any]


class InitialSetupActionRequest(BaseModel):
    """Запрос на действие в начальной фазе"""
    action: str  # "place_settlement" или "place_road"
    vertex_id: Optional[int] = None  # Для поселения
    vertex1_id: Optional[int] = None  # Для дороги
    vertex2_id: Optional[int] = None  # Для дороги


class InitialSetupActionResponse(BaseModel):
    """Ответ на действие в начальной фазе"""
    success: bool
    message: str
    game_state: Dict[str, Any]
    setup_phase: Dict[str, Any]

