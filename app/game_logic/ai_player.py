"""
AI игрок для Catan
"""
import random
from typing import Dict, Any, List, Optional, Tuple

from app.game_logic.catan_engine import CatanEngine
from app.models.catan import BuildingType, ResourceType


class AIPlayer:
    """Простой AI игрок для Catan"""
    
    def __init__(self, player_id: int, engine: CatanEngine):
        self.player_id = player_id
        self.engine = engine
    
    def make_move(self) -> Dict[str, Any]:
        """Выполняет ход AI игрока"""
        moves = []
        
        # Фаза 1: Бросок кубиков (автоматически в начале хода)
        
        # Фаза 2: Торговля (пока пропускаем)
        
        # Фаза 3: Строительство
        build_move = self._decide_building()
        if build_move:
            moves.append(build_move)
        
        # Фаза 4: Торговля с банком (если нужно и возможно)
        trade_move = self._decide_bank_trade()
        if trade_move:
            moves.append(trade_move)
        
        return {
            "player_id": self.player_id,
            "moves": moves
        }
    
    def _decide_building(self) -> Optional[Dict[str, Any]]:
        """Решает, что строить"""
        resources = self.engine.player_resources.get(str(self.player_id), {})
        
        # Приоритет 1: Город (если есть поселение и достаточно ресурсов)
        if self._can_afford_city(resources):
            city_vertex = self._find_settlement_to_upgrade()
            if city_vertex:
                return {
                    "action": "build_city",
                    "vertex_id": city_vertex
                }
        
        # Приоритет 2: Поселение (если достаточно ресурсов и есть место)
        if self._can_afford_settlement(resources):
            settlement_vertex = self._find_best_settlement_location()
            if settlement_vertex:
                return {
                    "action": "build_settlement",
                    "vertex_id": settlement_vertex
                }
        
        # Приоритет 3: Дорога (если достаточно ресурсов и нужно)
        if self._can_afford_road(resources):
            road_location = self._find_best_road_location()
            if road_location:
                return {
                    "action": "build_road",
                    "vertex1_id": road_location[0],
                    "vertex2_id": road_location[1]
                }
        
        return None
    
    def _can_afford_city(self, resources: Dict[str, int]) -> bool:
        """Проверяет, может ли игрок построить город"""
        return (resources.get(ResourceType.ORE.value, 0) >= 3 and
                resources.get(ResourceType.WHEAT.value, 0) >= 2)
    
    def _can_afford_settlement(self, resources: Dict[str, int]) -> bool:
        """Проверяет, может ли игрок построить поселение"""
        return (resources.get(ResourceType.WOOD.value, 0) >= 1 and
                resources.get(ResourceType.BRICK.value, 0) >= 1 and
                resources.get(ResourceType.SHEEP.value, 0) >= 1 and
                resources.get(ResourceType.WHEAT.value, 0) >= 1)
    
    def _can_afford_road(self, resources: Dict[str, int]) -> bool:
        """Проверяет, может ли игрок построить дорогу"""
        return (resources.get(ResourceType.WOOD.value, 0) >= 1 and
                resources.get(ResourceType.BRICK.value, 0) >= 1)
    
    def _find_settlement_to_upgrade(self) -> Optional[int]:
        """Находит поселение для улучшения до города"""
        player_settlements = [
            v for v in self.engine.vertices
            if v.get("owner_id") == self.player_id and
            v.get("building_type") == BuildingType.SETTLEMENT.value
        ]
        
        if player_settlements:
            # Выбираем случайное поселение (можно улучшить логику)
            return random.choice(player_settlements).get("vertex_id")
        
        return None
    
    def _find_best_settlement_location(self) -> Optional[int]:
        """Находит лучшее место для поселения"""
        # Ищем свободные вершины
        free_vertices = [
            v for v in self.engine.vertices
            if v.get("owner_id") is None
        ]
        
        if not free_vertices:
            return None
        
        # Простая эвристика: выбираем случайную вершину
        # (в реальной игре нужно учитывать доступные ресурсы)
        return random.choice(free_vertices).get("vertex_id")
    
    def _find_best_road_location(self) -> Optional[Tuple[int, int]]:
        """Находит лучшее место для дороги"""
        # Простая логика: строим дорогу от существующих построек
        player_vertices = [
            v for v in self.engine.vertices
            if v.get("owner_id") == self.player_id
        ]
        
        if not player_vertices:
            return None
        
        # Выбираем случайную вершину игрока
        vertex = random.choice(player_vertices)
        vertex_id = vertex.get("vertex_id")
        
        # Находим соседнюю свободную вершину (упрощенно)
        # В реальной игре нужно проверять реальные связи
        for v in self.engine.vertices:
            if v.get("vertex_id") != vertex_id and v.get("owner_id") is None:
                return (vertex_id, v.get("vertex_id"))
        
        return None
    
    def _decide_bank_trade(self) -> Optional[Dict[str, Any]]:
        """Решает, нужно ли торговать с банком (4:1)"""
        # Упрощенная логика: если есть 4+ одинаковых ресурса, меняем на нужный
        resources = self.engine.player_resources.get(str(self.player_id), {})
        
        for resource_type in [ResourceType.WOOD, ResourceType.BRICK, ResourceType.SHEEP, ResourceType.WHEAT, ResourceType.ORE]:
            count = resources.get(resource_type.value, 0)
            if count >= 4:
                # Меняем на самый нужный ресурс
                needed_resource = self._get_needed_resource(resources)
                if needed_resource:
                    return {
                        "action": "trade_bank",
                        "give": resource_type.value,
                        "give_amount": 4,
                        "take": needed_resource,
                        "take_amount": 1
                    }
        
        return None
    
    def _get_needed_resource(self, resources: Dict[str, int]) -> Optional[str]:
        """Определяет, какой ресурс нужнее всего"""
        # Простая логика: нужен тот, которого меньше всего
        resource_types = [ResourceType.WOOD, ResourceType.BRICK, ResourceType.SHEEP, ResourceType.WHEAT, ResourceType.ORE]
        min_resource = None
        min_count = float('inf')
        
        for resource_type in resource_types:
            count = resources.get(resource_type.value, 0)
            if count < min_count:
                min_count = count
                min_resource = resource_type.value
        
        return min_resource

