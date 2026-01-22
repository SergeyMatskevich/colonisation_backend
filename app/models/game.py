from sqlalchemy import Column, String, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class GameStatus(str, enum.Enum):
    """Статусы игры"""
    WAITING = "waiting"  # Ожидание игроков
    IN_PROGRESS = "in_progress"  # Игра идет
    FINISHED = "finished"  # Игра завершена
    ABANDONED = "abandoned"  # Игра брошена


class Game(BaseModel):
    """Модель игры"""
    __tablename__ = "games"
    
    name = Column(String(100), nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.WAITING, nullable=False)
    max_players = Column(Integer, default=4, nullable=False)
    current_player_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Игровое состояние в JSON (будет структурировано позже)
    game_state = Column(JSON, nullable=True)
    
    # Relationships
    players = relationship("GamePlayer", back_populates="game", cascade="all, delete-orphan")


class GamePlayer(BaseModel):
    """Связь игрока с игрой"""
    __tablename__ = "game_players"
    
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Позиция игрока (для определения порядка хода)
    position = Column(Integer, nullable=False)
    
    # Статистика игрока в этой игре
    victory_points = Column(Integer, default=0, nullable=False)
    
    # Relationships
    game = relationship("Game", back_populates="players")
    player = relationship("User", back_populates="games_as_player")

