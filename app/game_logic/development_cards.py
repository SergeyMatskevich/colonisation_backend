"""
Развивающие карты в Catan
"""
from typing import Dict, Any, List, Optional, Tuple
import random

from app.models.catan import ResourceType


class DevelopmentCard:
    """Развивающие карты"""
    KNIGHT = "knight"  # Рыцарь
    VICTORY_POINT = "victory_point"  # Очко победы
    ROAD_BUILDING = "road_building"  # Строительство дорог
    YEAR_OF_PLENTY = "year_of_plenty"  # Год изобилия
    MONOPOLY = "monopoly"  # Монополия


class DevelopmentCardSystem:
    """Система развивающих карт"""
    
    COST = {
        ResourceType.SHEEP: 1,
        ResourceType.WHEAT: 1,
        ResourceType.ORE: 1
    }
    
    @staticmethod
    def create_deck() -> List[str]:
        """Создает колоду развивающих карт"""
        deck = []
        # 14 рыцарей
        deck.extend([DevelopmentCard.KNIGHT] * 14)
        # 5 карт очков победы
        deck.extend([DevelopmentCard.VICTORY_POINT] * 5)
        # 2 карты строительства дорог
        deck.extend([DevelopmentCard.ROAD_BUILDING] * 2)
        # 2 карты года изобилия
        deck.extend([DevelopmentCard.YEAR_OF_PLENTY] * 2)
        # 2 карты монополии
        deck.extend([DevelopmentCard.MONOPOLY] * 2)
        random.shuffle(deck)
        return deck
    
    @staticmethod
    def can_buy_card(player_resources: Dict[str, int]) -> Tuple[bool, str]:
        """Проверяет, может ли игрок купить развивающую карту"""
        if (player_resources.get(ResourceType.SHEEP.value, 0) >= 1 and
            player_resources.get(ResourceType.WHEAT.value, 0) >= 1 and
            player_resources.get(ResourceType.ORE.value, 0) >= 1):
            return True, "OK"
        return False, "Недостаточно ресурсов (нужны: 1 овца, 1 пшеница, 1 камень)"
    
    @staticmethod
    def buy_card(player_resources: Dict[str, int], deck: List[str]) -> Tuple[str, Dict[str, int]]:
        """Покупает развивающую карту"""
        can_buy, message = DevelopmentCardSystem.can_buy_card(player_resources)
        if not can_buy:
            raise ValueError(message)
        
        if not deck:
            raise ValueError("Колода развивающих карт пуста")
        
        # Списываем ресурсы
        player_resources[ResourceType.SHEEP.value] = player_resources.get(ResourceType.SHEEP.value, 0) - 1
        player_resources[ResourceType.WHEAT.value] = player_resources.get(ResourceType.WHEAT.value, 0) - 1
        player_resources[ResourceType.ORE.value] = player_resources.get(ResourceType.ORE.value, 0) - 1
        
        # Берем карту из колоды
        card = deck.pop(0)
        
        return card, player_resources
    
    @staticmethod
    def play_knight(player_id: int, player_played_knights: Dict[int, int]) -> Dict[str, Any]:
        """Играет карту Рыцарь (перемещает разбойника)"""
        # Увеличиваем счетчик рыцарей игрока
        current_count = player_played_knights.get(player_id, 0)
        player_played_knights[player_id] = current_count + 1
        
        # Проверяем, достиг ли игрок 3 рыцарей для самой большой армии
        has_largest_army = current_count + 1 >= 3
        
        return {
            "success": True,
            "message": "Карта Рыцарь сыграна",
            "knights_count": current_count + 1,
            "has_largest_army": has_largest_army
        }
    
    @staticmethod
    def play_road_building(player_resources: Dict[str, int]) -> Dict[str, Any]:
        """Играет карту Строительство дорог (2 бесплатные дороги)"""
        return {
            "success": True,
            "message": "Карта Строительство дорог: можно построить 2 дороги бесплатно",
            "free_roads": 2
        }
    
    @staticmethod
    def play_year_of_plenty(player_resources: Dict[str, int], resource1: str, resource2: str) -> Dict[str, Any]:
        """Играет карту Год изобилия (берет 2 любых ресурса)"""
        player_resources[resource1] = player_resources.get(resource1, 0) + 1
        player_resources[resource2] = player_resources.get(resource2, 0) + 1
        
        return {
            "success": True,
            "message": f"Получено 2 ресурса: {resource1}, {resource2}",
            "resources": player_resources
        }
    
    @staticmethod
    def play_monopoly(player_resources: Dict[str, int], all_players_resources: Dict[str, Dict[str, int]], resource_type: str) -> Dict[str, Any]:
        """Играет карту Монополия (забирает все карты указанного типа у всех игроков)"""
        total_stolen = 0
        
        for player_key, player_res in all_players_resources.items():
            if player_key != str(player_resources):  # Не берем у себя
                count = player_res.get(resource_type, 0)
                if count > 0:
                    player_res[resource_type] = 0
                    total_stolen += count
        
        player_resources[resource_type] = player_resources.get(resource_type, 0) + total_stolen
        
        return {
            "success": True,
            "message": f"Забрано {total_stolen} {resource_type} у всех игроков",
            "resources": player_resources,
            "stolen_amount": total_stolen
        }

