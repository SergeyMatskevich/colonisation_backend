from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.game import Game as GameModel, GamePlayer as GamePlayerModel, GameStatus
from app.models.user import User as UserModel
from app.schemas.game import Game, GameCreate, GameUpdate

router = APIRouter()


@router.post("/", response_model=Game, status_code=status.HTTP_201_CREATED)
async def create_game(game: GameCreate, db: Session = Depends(get_db)):
    """Создание новой игры"""
    db_game = GameModel(
        name=game.name,
        max_players=game.max_players,
        status=GameStatus.WAITING
    )
    
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    
    return db_game


@router.get("/", response_model=List[Game])
async def get_games(
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу игры"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получение списка игр"""
    query = db.query(GameModel)
    
    if status_filter:
        try:
            game_status = GameStatus(status_filter)
            query = query.filter(GameModel.status == game_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Valid values: {[s.value for s in GameStatus]}"
            )
    
    games = query.offset(skip).limit(limit).all()
    return games


@router.get("/{game_id}", response_model=Game)
async def get_game(game_id: int, db: Session = Depends(get_db)):
    """Получение игры по ID"""
    game = db.query(GameModel).filter(GameModel.id == game_id).first()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    return game


@router.patch("/{game_id}", response_model=Game)
async def update_game(
    game_id: int,
    game_update: GameUpdate,
    db: Session = Depends(get_db)
):
    """Обновление игры"""
    db_game = db.query(GameModel).filter(GameModel.id == game_id).first()
    
    if not db_game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Обновление полей
    update_data = game_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_game, field, value)
    
    db.commit()
    db.refresh(db_game)
    
    return db_game


@router.post("/{game_id}/players/{player_id}", response_model=Game)
async def add_player_to_game(
    game_id: int,
    player_id: int,
    db: Session = Depends(get_db)
):
    """Добавление игрока в игру"""
    # Проверка существования игры
    game = db.query(GameModel).filter(GameModel.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Проверка существования пользователя
    user = db.query(UserModel).filter(UserModel.id == player_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверка, не добавлен ли уже игрок
    existing_player = db.query(GamePlayerModel).filter(
        GamePlayerModel.game_id == game_id,
        GamePlayerModel.player_id == player_id
    ).first()
    
    if existing_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player already in game"
        )
    
    # Проверка максимального количества игроков
    current_players_count = db.query(GamePlayerModel).filter(
        GamePlayerModel.game_id == game_id
    ).count()
    
    if current_players_count >= game.max_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is full"
        )
    
    # Добавление игрока
    new_player = GamePlayerModel(
        game_id=game_id,
        player_id=player_id,
        position=current_players_count + 1,
        victory_points=0
    )
    
    db.add(new_player)
    db.commit()
    db.refresh(game)
    
    return game

