from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.models.game import Game as GameModel, GameStatus
from app.models.user import User as UserModel
from app.game_logic.catan_engine import CatanEngine
from app.game_logic.ai_player import AIPlayer
from app.schemas.catan import (
    StartGameRequest, StartGameResponse,
    DiceRollRequest, DiceRollResponse,
    BuildSettlementRequest, BuildCityRequest, BuildRoadRequest, BuildResponse,
    GameStateResponse,
    MoveRobberRequest, MoveRobberResponse,
    TradeWithBankRequest, TradeWithBankResponse,
    TradeWithPortRequest, TradeWithPortResponse,
    CreateTradeOfferRequest, AcceptTradeOfferRequest, TradeOfferResponse,
    BuyDevCardResponse, PlayDevCardRequest, PlayDevCardResponse,
    InitialSetupActionRequest, InitialSetupActionResponse
)

router = APIRouter()


def get_game_with_state(game_id: int, db: Session) -> GameModel:
    """Получает игру и проверяет её существование"""
    game = db.query(GameModel).filter(GameModel.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Игра не найдена"
        )
    return game


@router.post("/start", response_model=StartGameResponse)
async def start_game(request: StartGameRequest, db: Session = Depends(get_db)):
    """Запускает игру Catan"""
    game = get_game_with_state(request.game_id, db)
    
    # Проверяем, что игра в статусе ожидания
    if game.status != GameStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра уже запущена или завершена"
        )
    
    # Проверяем количество игроков (нужно минимум 2, максимум 4)
    players_count = len(game.players)
    if players_count < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно игроков. Нужно минимум 2 игрока"
        )
    
    # Создаем начальное состояние игры
    player_list = []
    player_resources = {}
    player_dev_cards = {}
    player_played_knights = {}
    
    for i, game_player in enumerate(game.players):
        player_data = {
            "player_id": game_player.player_id,
            "position": game_player.position,
            "is_ai": False,
            "victory_points": 0
        }
        player_list.append(player_data)
        player_resources[str(game_player.player_id)] = {
            "wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0
        }
        player_dev_cards[str(game_player.player_id)] = []
        player_played_knights[game_player.player_id] = 0
    
    # Если игроков меньше 4, добавляем AI игроков
    ai_count = 4 - players_count
    for i in range(ai_count):
        ai_player_id = -(i + 1)
        player_data = {
            "player_id": ai_player_id,
            "position": players_count + i + 1,
            "is_ai": True,
            "victory_points": 0
        }
        player_list.append(player_data)
        player_resources[str(ai_player_id)] = {
            "wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0
        }
        player_dev_cards[str(ai_player_id)] = []
        player_played_knights[ai_player_id] = 0
    
    # Создаем игровой движок с начальным состоянием
    initial_state = {
        "players": player_list,
        "hexes": [],
        "hex_layout": [],
        "vertices": [],
        "vertices_dict": {},
        "edges": [],
        "player_resources": player_resources,
        "player_dev_cards": player_dev_cards,
        "player_played_knights": player_played_knights,
        "current_player_index": 0,
        "phase": "initial_setup",
        "setup_phase": {"round": 1, "player_index": 0, "actions": []},
        "last_dice_roll": None,
        "longest_road_player": None,
        "longest_road_length": 0,
        "largest_army_player": None,
        "robber_location": None,
        "ports": {},
        "dev_cards_deck": [],
        "pending_trades": []
    }
    
    engine = CatanEngine(initial_state)
    board = engine.generate_board()
    
    # Обновляем состояние с данными доски
    game_state = engine.get_game_state()
    game_state["hexes"] = board["hexes"]
    game_state["hex_layout"] = board["hex_layout"]
    game_state["vertices"] = board["vertices"]
    game_state["vertices_dict"] = board["vertices_dict"]
    game_state["edges"] = board["edges"]
    game_state["ports"] = board["ports"]
    game_state["dev_cards_deck"] = board["dev_cards_deck"]
    game_state["robber_location"] = board["robber_location"]
    
    # Обновляем игру
    game.game_state = game_state
    game.status = GameStatus.IN_PROGRESS
    game.current_player_id = player_list[0]["player_id"]
    
    db.commit()
    db.refresh(game)
    
    return StartGameResponse(
        success=True,
        message="Игра запущена успешно",
        game_state=game_state
    )


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(game_id: int, db: Session = Depends(get_db)):
    """Получает текущее состояние игры"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index] if engine.players else None
    
    # Проверяем, есть ли победитель
    winner = None
    for player in engine.players:
        if engine.check_win(player["player_id"]):
            winner = player["player_id"]
            break
    
    return GameStateResponse(
        game_state=game.game_state,
        current_player_id=current_player["player_id"] if current_player else None,
        phase=engine.phase.value,
        winner=winner
    )


@router.post("/{game_id}/roll-dice", response_model=DiceRollResponse)
async def roll_dice(game_id: int, db: Session = Depends(get_db)):
    """Бросает кубики для текущего игрока"""
    game = get_game_with_state(game_id, db)
    
    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра не в процессе"
        )
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    
    # Бросаем кубики
    dice_roll = engine.roll_dice()
    
    # Обрабатываем результат броска
    if dice_roll == 7:
        # Разбойник - обрабатываем отдельно
        current_player = engine.players[engine.current_player_index]
        engine.handle_dice_roll_7(current_player["player_id"])
    else:
        # Распределяем ресурсы
        current_player = engine.players[engine.current_player_index]
        engine.distribute_resources(dice_roll, current_player["player_id"])
    
    # Обновляем состояние игры
    game.game_state = engine.get_game_state()
    db.commit()
    db.refresh(game)
    
    return DiceRollResponse(
        dice_roll=dice_roll,
        game_state=game.game_state
    )


@router.post("/{game_id}/build-settlement", response_model=BuildResponse)
async def build_settlement(
    game_id: int,
    request: BuildSettlementRequest,
    db: Session = Depends(get_db)
):
    """Строит поселение"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    engine._update_vertices_dict()  # Обновляем словарь вершин
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    # Определяем, начальная фаза или нет
    is_initial_setup = engine.phase.value == "initial_setup"
    give_resources = not is_initial_setup or engine.setup_phase.get("round", 1) == 2
    
    try:
        result = engine.build_settlement(player_id, request.vertex_id, initial_setup=is_initial_setup, give_resources=give_resources)
        
        # Если начальная фаза, переходим к следующему действию
        if is_initial_setup:
            engine.setup_phase["actions"] = engine.setup_phase.get("actions", [])
            engine.setup_phase["actions"].append({"action": "settlement", "vertex_id": request.vertex_id})
        
        # Проверяем победу
        if engine.check_win(player_id):
            game.status = GameStatus.FINISHED
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return BuildResponse(
            success=result["success"],
            message=result["message"],
            resources=result["resources"],
            victory_points=result["victory_points"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/build-city", response_model=BuildResponse)
async def build_city(
    game_id: int,
    request: BuildCityRequest,
    db: Session = Depends(get_db)
):
    """Строит город (улучшает поселение)"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.build_city(player_id, request.vertex_id)
        
        # Проверяем победу
        winner = None
        if engine.check_win(player_id):
            winner = player_id
            game.status = GameStatus.FINISHED
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return BuildResponse(
            success=result["success"],
            message=result["message"],
            resources=result["resources"],
            victory_points=result["victory_points"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/build-road", response_model=BuildResponse)
async def build_road(
    game_id: int,
    request: BuildRoadRequest,
    db: Session = Depends(get_db)
):
    """Строит дорогу"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.build_road(player_id, request.vertex1_id, request.vertex2_id)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        # Получаем очки победы через метод engine
        victory_points = 0
        for player in engine.players:
            if player.get("player_id") == player_id:
                victory_points = player.get("victory_points", 0)
                break
        
        return BuildResponse(
            success=result["success"],
            message=result["message"],
            resources=result["resources"],
            victory_points=victory_points,
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/end-turn")
async def end_turn(game_id: int, db: Session = Depends(get_db)):
    """Заканчивает ход текущего игрока"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    
    # Если начальная фаза, используем специальную логику
    if engine.phase.value == "initial_setup":
        engine.advance_setup_phase()
        next_player = engine.players[engine.current_player_index] if engine.current_player_index < len(engine.players) else engine.players[0]
    else:
        # Переходим к следующему игроку
        engine.current_player_index = (engine.current_player_index + 1) % len(engine.players)
        next_player = engine.players[engine.current_player_index]
        
        # Если следующий игрок - AI, выполняем его ход автоматически
        if next_player.get("is_ai"):
            ai = AIPlayer(next_player["player_id"], engine)
            ai.make_move()
    
    game.current_player_id = next_player["player_id"]
    game.game_state = engine.get_game_state()
    db.commit()
    db.refresh(game)
    
    return {
        "success": True,
        "message": "Ход передан следующему игроку",
        "current_player_id": next_player["player_id"],
        "game_state": game.game_state
    }


# ========== НОВЫЕ ENDPOINTS ДЛЯ ДОРАБОТАННЫХ ФУНКЦИЙ ==========

@router.post("/{game_id}/move-robber", response_model=MoveRobberResponse)
async def move_robber(
    game_id: int,
    request: MoveRobberRequest,
    db: Session = Depends(get_db)
):
    """Перемещает разбойника"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.move_robber(player_id, request.hex_index, request.steal_from_player_id)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return MoveRobberResponse(
            success=result["robber_moved"],
            message="Разбойник перемещен",
            new_location=result["new_location"],
            stolen_resource=result.get("stolen_resource"),
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/trade-bank", response_model=TradeWithBankResponse)
async def trade_with_bank(
    game_id: int,
    request: TradeWithBankRequest,
    db: Session = Depends(get_db)
):
    """Торговля с банком (4:1)"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.trade_with_bank(
            player_id,
            request.give_resource,
            request.give_amount,
            request.take_resource,
            request.take_amount
        )
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return TradeWithBankResponse(
            success=result["success"],
            message=result["message"],
            resources=result["resources"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/trade-port", response_model=TradeWithPortResponse)
async def trade_with_port(
    game_id: int,
    request: TradeWithPortRequest,
    db: Session = Depends(get_db)
):
    """Торговля через порт"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    engine._update_vertices_dict()
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.trade_with_port(
            player_id,
            request.vertex_id,
            request.give_resource,
            request.give_amount,
            request.take_resource,
            request.take_amount
        )
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return TradeWithPortResponse(
            success=result["success"],
            message=result["message"],
            resources=result["resources"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/buy-dev-card", response_model=BuyDevCardResponse)
async def buy_dev_card(game_id: int, db: Session = Depends(get_db)):
    """Покупает развивающую карту"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.buy_development_card(player_id)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return BuyDevCardResponse(
            success=result["success"],
            message=result["message"],
            card=result["card"],
            revealed=result["revealed"],
            resources=result["resources"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/play-dev-card", response_model=PlayDevCardResponse)
async def play_dev_card(
    game_id: int,
    request: PlayDevCardRequest,
    db: Session = Depends(get_db)
):
    """Играет развивающую карту"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        result = engine.play_development_card(player_id, request.card_type, request.card_data)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return PlayDevCardResponse(
            success=result["success"],
            message=result["message"],
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/create-trade-offer", response_model=TradeOfferResponse)
async def create_trade_offer(
    game_id: int,
    request: CreateTradeOfferRequest,
    db: Session = Depends(get_db)
):
    """Создает предложение торговли между игроками"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        # Проверяем, что у игрока достаточно ресурсов для обмена
        resources = engine.player_resources.get(str(player_id), {})
        for resource, amount in request.give_resources.items():
            if resources.get(resource, 0) < amount:
                raise ValueError(f"Недостаточно ресурсов: {resource}")
        
        offer = engine.create_trade_offer(player_id, request.give_resources, request.want_resources)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return TradeOfferResponse(
            success=True,
            message="Предложение торговли создано",
            trade_offer=offer,
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/accept-trade-offer", response_model=TradeOfferResponse)
async def accept_trade_offer(
    game_id: int,
    request: AcceptTradeOfferRequest,
    db: Session = Depends(get_db)
):
    """Принимает предложение торговли"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    current_player = engine.players[engine.current_player_index]
    accepting_player_id = current_player["player_id"]
    
    try:
        result = engine.accept_trade_offer(request.trade_offer_id, accepting_player_id)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return TradeOfferResponse(
            success=result["success"],
            message=result["message"],
            trade_offer=None,
            game_state=game.game_state
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{game_id}/initial-setup", response_model=InitialSetupActionResponse)
async def initial_setup_action(
    game_id: int,
    request: InitialSetupActionRequest,
    db: Session = Depends(get_db)
):
    """Действие в начальной фазе (расстановка поселений и дорог)"""
    game = get_game_with_state(game_id, db)
    
    if not game.game_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Игра еще не запущена"
        )
    
    engine = CatanEngine(game.game_state)
    engine._update_vertices_dict()
    current_player = engine.players[engine.current_player_index]
    player_id = current_player["player_id"]
    
    try:
        # Формируем данные для действия
        data = {}
        if request.action == "place_settlement" and request.vertex_id is not None:
            data["vertex_id"] = request.vertex_id
        elif request.action == "place_road":
            if request.vertex1_id is None or request.vertex2_id is None:
                raise ValueError("Для дороги нужны vertex1_id и vertex2_id")
            data["vertex1_id"] = request.vertex1_id
            data["vertex2_id"] = request.vertex2_id
        else:
            raise ValueError(f"Неизвестное действие: {request.action}")
        
        result = engine.handle_initial_setup(player_id, request.action, data)
        
        game.game_state = engine.get_game_state()
        db.commit()
        db.refresh(game)
        
        return InitialSetupActionResponse(
            success=result.get("success", True),
            message=result.get("message", "Действие выполнено"),
            game_state=game.game_state,
            setup_phase=engine.setup_phase
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

