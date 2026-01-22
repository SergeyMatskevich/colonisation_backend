from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.models.game import GameStatus


class GamePlayerBase(BaseModel):
    player_id: int
    position: int
    victory_points: int = 0


class GamePlayer(GamePlayerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GameBase(BaseModel):
    name: str
    max_players: int = 4


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[GameStatus] = None
    current_player_id: Optional[int] = None
    game_state: Optional[Dict[str, Any]] = None


class Game(GameBase):
    id: int
    status: GameStatus
    current_player_id: Optional[int]
    game_state: Optional[Dict[str, Any]]
    players: List[GamePlayer] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

