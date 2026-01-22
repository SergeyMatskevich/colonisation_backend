"""
Торговля в Catan
"""
from typing import Dict, Any, List, Optional, Tuple
from app.models.catan import ResourceType


class TradingSystem:
    """Система торговли в Catan"""
    
    @staticmethod
    def can_trade_with_bank(player_resources: Dict[str, int], give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Tuple[bool, str]:
        """Проверяет возможность торговли с банком (стандартная: 4:1)"""
        if give_amount < 4 or take_amount != 1:
            return False, "Стандартная торговля с банком: 4:1"
        
        if player_resources.get(give_resource, 0) < give_amount:
            return False, f"Недостаточно ресурсов {give_resource}"
        
        return True, "OK"
    
    @staticmethod
    def can_trade_with_port(player_resources: Dict[str, int], port_type: str, give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Tuple[bool, str]:
        """Проверяет возможность торговли через порт"""
        if port_type == "generic":
            # Общий порт: 3:1
            if give_amount < 3 or take_amount != 1:
                return False, "Общий порт: 3:1"
        else:
            # Специальный порт: 2:1 для конкретного ресурса
            if give_resource != port_type:
                return False, f"Порт {port_type} принимает только {port_type}"
            if give_amount < 2 or take_amount != 1:
                return False, f"Специальный порт {port_type}: 2:1"
        
        if player_resources.get(give_resource, 0) < give_amount:
            return False, f"Недостаточно ресурсов {give_resource}"
        
        return True, "OK"
    
    @staticmethod
    def trade_with_bank(player_resources: Dict[str, int], give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Dict[str, Any]:
        """Торговля с банком"""
        can_trade, message = TradingSystem.can_trade_with_bank(
            player_resources, give_resource, give_amount, take_resource, take_amount
        )
        
        if not can_trade:
            raise ValueError(message)
        
        # Списываем отдаваемые ресурсы
        player_resources[give_resource] = player_resources.get(give_resource, 0) - give_amount
        
        # Добавляем получаемые ресурсы
        player_resources[take_resource] = player_resources.get(take_resource, 0) + take_amount
        
        return {
            "success": True,
            "message": f"Обменено {give_amount} {give_resource} на {take_amount} {take_resource}",
            "resources": player_resources
        }
    
    @staticmethod
    def trade_with_port(player_resources: Dict[str, int], port_type: str, give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Dict[str, Any]:
        """Торговля через порт"""
        can_trade, message = TradingSystem.can_trade_with_port(
            player_resources, port_type, give_resource, give_amount, take_resource, take_amount
        )
        
        if not can_trade:
            raise ValueError(message)
        
        # Списываем отдаваемые ресурсы
        player_resources[give_resource] = player_resources.get(give_resource, 0) - give_amount
        
        # Добавляем получаемые ресурсы
        player_resources[take_resource] = player_resources.get(take_resource, 0) + take_amount
        
        return {
            "success": True,
            "message": f"Обменено {give_amount} {give_resource} на {take_amount} {take_resource} через порт",
            "resources": player_resources
        }
    
    @staticmethod
    def create_trade_offer(player_id: int, give_resources: Dict[str, int], want_resources: Dict[str, int]) -> Dict[str, Any]:
        """Создает предложение торговли между игроками"""
        return {
            "from_player_id": player_id,
            "give_resources": give_resources,
            "want_resources": want_resources,
            "accepted": False
        }
    
    @staticmethod
    def accept_trade_offer(trade_offer: Dict[str, Any], from_player_resources: Dict[str, int], to_player_resources: Dict[str, int]) -> Dict[str, Any]:
        """Принимает предложение торговли"""
        # Проверяем, что у обоих игроков достаточно ресурсов
        for resource, amount in trade_offer["give_resources"].items():
            if from_player_resources.get(resource, 0) < amount:
                raise ValueError(f"У игрока {trade_offer['from_player_id']} недостаточно {resource}")
        
        for resource, amount in trade_offer["want_resources"].items():
            if to_player_resources.get(resource, 0) < amount:
                raise ValueError(f"У принимающего игрока недостаточно {resource}")
        
        # Обмениваем ресурсы
        for resource, amount in trade_offer["give_resources"].items():
            from_player_resources[resource] = from_player_resources.get(resource, 0) - amount
            to_player_resources[resource] = to_player_resources.get(resource, 0) + amount
        
        for resource, amount in trade_offer["want_resources"].items():
            from_player_resources[resource] = from_player_resources.get(resource, 0) + amount
            to_player_resources[resource] = to_player_resources.get(resource, 0) - amount
        
        trade_offer["accepted"] = True
        
        return {
            "success": True,
            "message": "Торговля завершена",
            "from_resources": from_player_resources,
            "to_resources": to_player_resources
        }

