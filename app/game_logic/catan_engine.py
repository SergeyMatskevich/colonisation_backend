"""
Полная реализация игровой логики Catan
Включает геометрию, начальную фазу, торговлю, развивающие карты, порты, разбойника
"""
import random
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict

from app.models.catan import ResourceType, HexType, BuildingType, GamePhase
from app.game_logic.geometry import CatanGeometry, PortLocation
from app.game_logic.trading import TradingSystem
from app.game_logic.development_cards import DevelopmentCard, DevelopmentCardSystem


# Экспортируем DevelopmentCard для использования в других модулях
__all__ = ["CatanEngine", "DevelopmentCard"]


class CatanEngine:
    """Полный движок игровой логики Catan"""
    
    # Стандартное количество каждого типа ресурса
    RESOURCE_COUNTS = {
        HexType.FOREST: 4,
        HexType.HILLS: 3,
        HexType.PASTURE: 4,
        HexType.FIELDS: 4,
        HexType.MOUNTAINS: 3,
        HexType.DESERT: 1
    }
    
    # Номера на жетонах
    NUMBER_TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
    
    # Стоимость построек
    SETTLEMENT_COST = {
        ResourceType.WOOD: 1,
        ResourceType.BRICK: 1,
        ResourceType.SHEEP: 1,
        ResourceType.WHEAT: 1
    }
    
    CITY_COST = {
        ResourceType.ORE: 3,
        ResourceType.WHEAT: 2
    }
    
    ROAD_COST = {
        ResourceType.WOOD: 1,
        ResourceType.BRICK: 1
    }
    
    DEVELOPMENT_CARD_COST = {
        ResourceType.SHEEP: 1,
        ResourceType.WHEAT: 1,
        ResourceType.ORE: 1
    }
    
    def __init__(self, game_state: Dict[str, Any]):
        self.game_state = game_state
        self.players = game_state.get("players", [])
        self.hexes = game_state.get("hexes", [])
        self.hex_layout = game_state.get("hex_layout", CatanGeometry.HEX_LAYOUT)
        self.vertices = game_state.get("vertices", [])
        self.vertices_dict = game_state.get("vertices_dict", {})  # Для быстрого доступа
        self.edges = game_state.get("edges", [])
        self.player_resources = game_state.get("player_resources", {})
        self.player_dev_cards = game_state.get("player_dev_cards", {})
        self.player_played_knights = game_state.get("player_played_knights", {})
        self.current_player_index = game_state.get("current_player_index", 0)
        self.phase = GamePhase(game_state.get("phase", GamePhase.INITIAL_SETUP))
        self.setup_phase = game_state.get("setup_phase", {"round": 1, "player_index": 0, "actions": []})
        self.dice_roll = game_state.get("last_dice_roll", None)
        self.longest_road_player = game_state.get("longest_road_player", None)
        self.longest_road_length = game_state.get("longest_road_length", 0)
        self.largest_army_player = game_state.get("largest_army_player", None)
        self.robber_location = game_state.get("robber_location", None)  # hex_index где находится разбойник
        self.ports = game_state.get("ports", {})  # {vertex_id: {"port_type": "...", "trade_ratio": "..."}}
        self.dev_cards_deck = game_state.get("dev_cards_deck", [])
        self.pending_trades = game_state.get("pending_trades", [])  # Предложения торговли
    
    def generate_board(self) -> Dict[str, Any]:
        """Генерирует стандартное игровое поле Catan с правильной геометрией"""
        # Создаем типы гексов
        hex_types = []
        for hex_type, count in self.RESOURCE_COUNTS.items():
            hex_types.extend([hex_type] * count)
        
        resource_hexes = [h for h in hex_types if h != HexType.DESERT]
        random.shuffle(resource_hexes)
        resource_hexes.insert(9, HexType.DESERT)  # Пустыня в центре
        
        # Распределяем номера
        numbers = self.NUMBER_TOKENS.copy()
        random.shuffle(numbers)
        
        # Создаем гексы с правильными координатами
        hexes = []
        number_index = 0
        
        for i, hex_type in enumerate(resource_hexes):
            hex_coord = self.hex_layout[i] if i < len(self.hex_layout) else (0, 0)
            hex_data = {
                "hex_index": i,
                "hex_coord": hex_coord,  # (q, r) координаты
                "hex_type": hex_type.value,
                "number": None if hex_type == HexType.DESERT else numbers[number_index],
                "has_robber": hex_type == HexType.DESERT
            }
            if hex_type != HexType.DESERT:
                number_index += 1
            hexes.append(hex_data)
            
            # Начальная позиция разбойника
            if hex_type == HexType.DESERT:
                self.robber_location = i
        
        # Генерируем вершины с правильной геометрией
        all_vertices_dict = CatanGeometry.get_all_board_vertices(self.hex_layout)
        vertices_list = []
        
        for vertex_key, vertex_data in all_vertices_dict.items():
            vertices_list.append({
                "vertex_id": vertex_data["vertex_id"],
                "x": vertex_data["x"],
                "y": vertex_data["y"],
                "owner_id": None,
                "building_type": None,
                "has_port": False
            })
        
        # Генерируем ребра
        edges_list = CatanGeometry.get_edges_for_board(all_vertices_dict)
        
        # Назначаем порты
        ports = PortLocation.assign_ports_to_vertices(all_vertices_dict, self.hex_layout)
        for vertex_id, port_data in ports.items():
            vertex = next((v for v in vertices_list if v["vertex_id"] == vertex_id), None)
            if vertex:
                vertex["has_port"] = True
                vertex["port_type"] = port_data["port_type"]
                vertex["trade_ratio"] = port_data["trade_ratio"]
        
        # Создаем колоду развивающих карт
        dev_cards_deck = self._create_dev_cards_deck()
        random.shuffle(dev_cards_deck)
        
        return {
            "hexes": hexes,
            "hex_layout": self.hex_layout,
            "vertices": vertices_list,
            "vertices_dict": {v["vertex_id"]: v for v in vertices_list},  # Для быстрого доступа
            "edges": edges_list,
            "ports": ports,
            "dev_cards_deck": dev_cards_deck,
            "robber_location": self.robber_location
        }
    
    def _create_dev_cards_deck(self) -> List[str]:
        """Создает колоду развивающих карт"""
        return DevelopmentCardSystem.create_deck()
    
    def _update_vertices_dict(self):
        """Обновляет словарь вершин для быстрого доступа"""
        if not hasattr(self, 'vertices_dict') or not self.vertices_dict:
            self.vertices_dict = {}
        for v in self.vertices:
            self.vertices_dict[v["vertex_id"]] = v
    
    def roll_dice(self) -> int:
        """Бросает два кубика"""
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        self.dice_roll = total
        return total
    
    def handle_dice_roll_7(self, player_id: int):
        """Обрабатывает выпадение 7 (разбойник)"""
        # Шаг 1: Игроки с 7+ ресурсов сбрасывают половину
        for player_data in self.players:
            pid = player_data["player_id"]
            resources = self.player_resources.get(str(pid), {})
            total_resources = sum(resources.values())
            
            if total_resources >= 7:
                discard_count = total_resources // 2
                self._discard_resources(pid, discard_count)
        
        # Шаг 2: Игрок перемещает разбойника (делается через API)
        # Шаг 3: Игрок может украсть ресурс у игрока с постройкой на новом гексе
    
    def move_robber(self, player_id: int, new_hex_index: int, steal_from_player_id: Optional[int] = None) -> Dict[str, Any]:
        """Перемещает разбойника на новый гекс"""
        if new_hex_index < 0 or new_hex_index >= len(self.hexes):
            raise ValueError("Некорректный индекс гекса")
        
        # Убираем разбойника со старого гекса
        if self.robber_location is not None:
            old_hex = self.hexes[self.robber_location]
            old_hex["has_robber"] = False
        
        # Размещаем на новом гексе
        new_hex = self.hexes[new_hex_index]
        new_hex["has_robber"] = True
        self.robber_location = new_hex_index
        
        result = {"robber_moved": True, "new_location": new_hex_index}
        
        # Если указан игрок для кражи, крадем ресурс
        if steal_from_player_id:
            stolen_resource = self._steal_resource(player_id, steal_from_player_id, new_hex_index)
            result["stolen_resource"] = stolen_resource
        
        return result
    
    def _steal_resource(self, thief_id: int, victim_id: int, hex_index: int) -> Optional[str]:
        """Крадет случайный ресурс у жертвы"""
        # Проверяем, есть ли у жертвы постройка на этом гексе
        hex_data = self.hexes[hex_index] if hex_index < len(self.hexes) else None
        if not hex_data:
            return None
        
        hex_coord = hex_data.get("hex_coord")
        if not hex_coord:
            return None
        
        # Находим вершины на этом гексе с постройками жертвы
        vertices_on_hex = self._get_vertices_for_hex(hex_coord)
        victim_vertices = []
        
        for vertex_id in vertices_on_hex:
            vertex = self.vertices_dict.get(vertex_id)
            if vertex and vertex.get("owner_id") == victim_id and vertex.get("building_type"):
                victim_vertices.append(vertex)
        
        if not victim_vertices:
            return None  # Нет построек жертвы на этом гексе
        
        # Крадем случайный ресурс
        victim_resources = self.player_resources.get(str(victim_id), {})
        available_resources = [r for r, count in victim_resources.items() if count > 0]
        
        if not available_resources:
            return None
        
        stolen_resource = random.choice(available_resources)
        victim_resources[stolen_resource] = victim_resources.get(stolen_resource, 0) - 1
        
        # Добавляем украденный ресурс вору
        thief_resources = self.player_resources.setdefault(str(thief_id), {})
        thief_resources[stolen_resource] = thief_resources.get(stolen_resource, 0) + 1
        
        return stolen_resource
    
    def _get_vertex_hex_coords(self, vertex_id: int) -> List[Tuple[int, int]]:
        """Получает координаты гексов, к которым принадлежит вершина"""
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex:
            return []
        
        vertex_coord = (vertex["x"], vertex["y"])
        vertex_key = CatanGeometry.get_vertex_key(vertex_coord)
        hex_coords = []
        
        # Для каждого гекса проверяем, принадлежит ли ему вершина
        for hex_data in self.hexes:
            hex_coord = hex_data.get("hex_coord")
            if not hex_coord:
                continue
            
            # Получаем вершины этого гекса
            hex_vertices_coords = CatanGeometry.get_hex_vertices(hex_coord)
            
            # Проверяем, есть ли среди вершин гекса наша вершина
            for v_coord in hex_vertices_coords:
                v_key = CatanGeometry.get_vertex_key(v_coord)
                if v_key == vertex_key:
                    # Проверяем точное совпадение координат (с учетом погрешности округления)
                    if abs(v_coord[0] - vertex_coord[0]) < 0.5 and abs(v_coord[1] - vertex_coord[1]) < 0.5:
                        if hex_coord not in hex_coords:
                            hex_coords.append(hex_coord)
                        break
        
        return hex_coords
    
    def distribute_resources(self, dice_roll: int, current_player_id: int):
        """Распределяет ресурсы после броска кубиков (кроме 7)"""
        if dice_roll == 7:
            return
        
        # Находим гексы с выпавшим номером (без разбойника)
        for hex_data in self.hexes:
            if hex_data.get("number") == dice_roll and not hex_data.get("has_robber", False):
                hex_type = HexType(hex_data["hex_type"])
                resource_type = self._hex_type_to_resource(hex_type)
                
                if resource_type is None:
                    continue
                
                # Находим все постройки на вершинах этого гекса
                hex_coord = hex_data.get("hex_coord")
                if not hex_coord:
                    continue
                
                vertices_on_hex = self._get_vertices_for_hex(hex_coord)
                
                # Распределяем ресурсы игрокам с постройками
                for vertex_id in vertices_on_hex:
                    vertex = self.vertices_dict.get(vertex_id)
                    if vertex and vertex.get("owner_id"):
                        owner_id = vertex["owner_id"]
                        building_type = vertex.get("building_type")
                        
                        if building_type == BuildingType.SETTLEMENT.value:
                            amount = 1
                        elif building_type == BuildingType.CITY.value:
                            amount = 2
                        else:
                            amount = 0
                        
                        if amount > 0:
                            resources = self.player_resources.setdefault(str(owner_id), {})
                            resources[resource_type.value] = resources.get(resource_type.value, 0) + amount
    
    def _get_vertices_for_hex(self, hex_coord: Tuple[int, int]) -> List[int]:
        """Получает ID вершин, принадлежащих гексу"""
        vertex_ids = []
        hex_vertices_coords = CatanGeometry.get_hex_vertices(hex_coord)
        
        # Находим вершины, которые принадлежат этому гексу
        for v_coord in hex_vertices_coords:
            v_key = CatanGeometry.get_vertex_key(v_coord)
            # Ищем вершину с такой же координатой (с учетом погрешности)
            for vertex in self.vertices:
                vertex_coord = (vertex["x"], vertex["y"])
                vertex_key = CatanGeometry.get_vertex_key(vertex_coord)
                
                if vertex_key == v_key or (abs(vertex["x"] - v_coord[0]) < 0.5 and abs(vertex["y"] - v_coord[1]) < 0.5):
                    if vertex["vertex_id"] not in vertex_ids:
                        vertex_ids.append(vertex["vertex_id"])
                    break
        
        return vertex_ids
    
    def _hex_type_to_resource(self, hex_type: HexType) -> Optional[ResourceType]:
        """Преобразует тип гекса в тип ресурса"""
        mapping = {
            HexType.FOREST: ResourceType.WOOD,
            HexType.HILLS: ResourceType.BRICK,
            HexType.PASTURE: ResourceType.SHEEP,
            HexType.FIELDS: ResourceType.WHEAT,
            HexType.MOUNTAINS: ResourceType.ORE,
            HexType.DESERT: None
        }
        return mapping.get(hex_type)
    
    # ========== МЕТОДЫ СТРОИТЕЛЬСТВА С ПРАВИЛЬНОЙ ГЕОМЕТРИЕЙ ==========
    
    def can_build_settlement(self, player_id: int, vertex_id: int, initial_setup: bool = False) -> Tuple[bool, str]:
        """Проверяет, может ли игрок построить поселение"""
        # Проверка 1: У игрока достаточно ресурсов (если не начальная фаза)
        if not initial_setup:
            resources = self.player_resources.get(str(player_id), {})
            for resource, amount in self.SETTLEMENT_COST.items():
                if resources.get(resource.value, 0) < amount:
                    return False, f"Недостаточно ресурсов: нужно {resource.value}"
        
        # Проверка 2: Вершина существует
        vertex = self.vertices_dict.get(vertex_id)
        if vertex is None:
            return False, "Вершина не найдена"
        
        # Проверка 3: Вершина свободна
        if vertex.get("owner_id") is not None:
            return False, "Вершина уже занята"
        
        # Проверка 4: Расстояние между поселениями (минимум 2 ребра)
        existing_settlements = [
            v["vertex_id"] for v in self.vertices 
            if v.get("owner_id") is not None and v.get("building_type")
        ]
        
        if not self._check_settlement_distance_with_geometry(vertex_id, existing_settlements):
            return False, "Слишком близко к другому поселению"
        
        # Проверка 5: В обычной фазе нужно связать с дорогой игрока
        if not initial_setup and self.phase == GamePhase.TURN:
            if not self._check_settlement_connected_to_road(player_id, vertex_id):
                return False, "Поселение должно быть связано с вашей дорогой или постройкой"
        
        return True, "OK"
    
    def _check_settlement_distance_with_geometry(self, vertex_id: int, existing_settlements: List[int]) -> bool:
        """Проверяет расстояние с использованием геометрии"""
        if not existing_settlements:
            return True
        
        # Создаем словарь вершин для геометрии
        all_vertices_dict = {}
        for v in self.vertices:
            v_coord = (v["x"], v["y"])
            v_key = CatanGeometry.get_vertex_key(v_coord)
            all_vertices_dict[v_key] = {
                "vertex_id": v["vertex_id"],
                "x": v["x"],
                "y": v["y"],
                "neighbors": []
            }
        
        # Находим соседей для каждой вершины
        for v in self.vertices:
            v_coord = (v["x"], v["y"])
            v_key = CatanGeometry.get_vertex_key(v_coord)
            # Находим соседние вершины через геометрию
            for other_v in self.vertices:
                if other_v["vertex_id"] != v["vertex_id"]:
                    other_coord = (other_v["x"], other_v["y"])
                    # Проверяем, являются ли они соседями (через ребра)
                    for edge in self.edges:
                        if ((edge["vertex1_id"] == v["vertex_id"] and edge["vertex2_id"] == other_v["vertex_id"]) or
                            (edge["vertex1_id"] == other_v["vertex_id"] and edge["vertex2_id"] == v["vertex_id"])):
                            if other_v["vertex_id"] not in all_vertices_dict[v_key].get("neighbors", []):
                                if "neighbors" not in all_vertices_dict[v_key]:
                                    all_vertices_dict[v_key]["neighbors"] = []
                                all_vertices_dict[v_key]["neighbors"].append(other_v["vertex_id"])
        
        # Используем геометрию для проверки расстояния
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex:
            return False
        
        vertex_coord = (vertex["x"], vertex["y"])
        v_key = CatanGeometry.get_vertex_key(vertex_coord)
        
        # Получаем соседние вершины
        neighbors = all_vertices_dict.get(v_key, {}).get("neighbors", [])
        
        # Проверяем, нет ли поселений на соседних вершинах
        for settlement_id in existing_settlements:
            if settlement_id in neighbors:
                return False  # Слишком близко - на соседней вершине
        
        # Проверяем соседей существующих поселений
        for settlement_id in existing_settlements:
            settlement_v = self.vertices_dict.get(settlement_id)
            if settlement_v:
                settlement_coord = (settlement_v["x"], settlement_v["y"])
                settlement_key = CatanGeometry.get_vertex_key(settlement_coord)
                settlement_neighbors = all_vertices_dict.get(settlement_key, {}).get("neighbors", [])
                if vertex_id in settlement_neighbors:
                    return False  # Слишком близко - мы соседи существующего поселения
        
        return True
    
    def _check_settlement_connected_to_road(self, player_id: int, vertex_id: int) -> bool:
        """Проверяет, связана ли вершина с дорогой или постройкой игрока"""
        # Проверяем, есть ли на вершине постройка игрока (это разрешено)
        vertex = self.vertices_dict.get(vertex_id)
        if vertex and vertex.get("owner_id") == player_id:
            return True
        
        # Проверяем, есть ли дорога игрока к этой вершине
        for edge in self.edges:
            if edge.get("owner_id") == player_id:
                if edge["vertex1_id"] == vertex_id or edge["vertex2_id"] == vertex_id:
                    return True
        
        return False
    
    def build_settlement(self, player_id: int, vertex_id: int, initial_setup: bool = False, give_resources: bool = True) -> Dict[str, Any]:
        """Строит поселение"""
        can_build, message = self.can_build_settlement(player_id, vertex_id, initial_setup)
        if not can_build:
            raise ValueError(message)
        
        # Списываем ресурсы (если не начальная фаза)
        resources = self.player_resources.setdefault(str(player_id), {})
        if not initial_setup:
            for resource, amount in self.SETTLEMENT_COST.items():
                resources[resource.value] = resources.get(resource.value, 0) - amount
        
        # Строим поселение
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex:
            # Находим в списке вершин
            vertex = next((v for v in self.vertices if v.get("vertex_id") == vertex_id), None)
        
        if vertex:
            vertex["owner_id"] = player_id
            vertex["building_type"] = BuildingType.SETTLEMENT.value
            # Обновляем словарь
            self.vertices_dict[vertex_id] = vertex
        
        # В начальной фазе при втором поселении даем ресурсы
        if initial_setup and give_resources:
            self._give_initial_settlement_resources(player_id, vertex_id)
        
        # Обновляем очки победы
        self._update_victory_points(player_id)
        
        return {
            "success": True,
            "message": "Поселение построено",
            "resources": resources,
            "victory_points": self._get_victory_points(player_id)
        }
    
    def _give_initial_settlement_resources(self, player_id: int, vertex_id: int):
        """Выдает ресурсы при размещении второго поселения в начальной фазе"""
        # Находим все гексы, прилегающие к этой вершине через правильную геометрию
        hex_coords = self._get_vertex_hex_coords(vertex_id)
        
        for hex_coord in hex_coords:
            # Находим соответствующий гекс
            hex_data = next((h for h in self.hexes if h.get("hex_coord") == hex_coord), None)
            if not hex_data:
                continue
            
            # Даем ресурсы от этого гекса
            hex_type = HexType(hex_data["hex_type"])
            resource_type = self._hex_type_to_resource(hex_type)
            
            if resource_type:
                resources = self.player_resources.setdefault(str(player_id), {})
                resources[resource_type.value] = resources.get(resource_type.value, 0) + 1
    
    # ========== МЕТОДЫ ДЛЯ ГОРОДА И ДОРОГИ ==========
    
    def can_build_city(self, player_id: int, vertex_id: int) -> Tuple[bool, str]:
        """Проверяет, может ли игрок построить город"""
        resources = self.player_resources.get(str(player_id), {})
        for resource, amount in self.CITY_COST.items():
            if resources.get(resource.value, 0) < amount:
                return False, f"Недостаточно ресурсов: нужно {resource.value}"
        
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex:
            return False, "Вершина не найдена"
        
        if vertex.get("owner_id") != player_id:
            return False, "На этой вершине нет вашего поселения"
        
        if vertex.get("building_type") != BuildingType.SETTLEMENT.value:
            return False, "На этой вершине должно быть поселение"
        
        return True, "OK"
    
    def build_city(self, player_id: int, vertex_id: int) -> Dict[str, Any]:
        """Строит город"""
        can_build, message = self.can_build_city(player_id, vertex_id)
        if not can_build:
            raise ValueError(message)
        
        resources = self.player_resources.setdefault(str(player_id), {})
        for resource, amount in self.CITY_COST.items():
            resources[resource.value] = resources.get(resource.value, 0) - amount
        
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex:
            vertex = next((v for v in self.vertices if v.get("vertex_id") == vertex_id), None)
        
        if vertex:
            vertex["building_type"] = BuildingType.CITY.value
            # Обновляем словарь
            self.vertices_dict[vertex_id] = vertex
        
        self._update_victory_points(player_id)
        
        return {
            "success": True,
            "message": "Город построен",
            "resources": resources,
            "victory_points": self._get_victory_points(player_id)
        }
    
    def can_build_road(self, player_id: int, vertex1_id: int, vertex2_id: int, free_road: bool = False) -> Tuple[bool, str]:
        """Проверяет, может ли игрок построить дорогу"""
        if not free_road:
            resources = self.player_resources.get(str(player_id), {})
            for resource, amount in self.ROAD_COST.items():
                if resources.get(resource.value, 0) < amount:
                    return False, f"Недостаточно ресурсов: нужно {resource.value}"
        
        # Проверяем, что вершины соседние
        v1 = self.vertices_dict.get(vertex1_id)
        v2 = self.vertices_dict.get(vertex2_id)
        if not v1 or not v2:
            return False, "Одна из вершин не найдена"
        
        # Проверяем, есть ли ребро между вершинами
        edge_exists = any(
            (e.get("vertex1_id") == vertex1_id and e.get("vertex2_id") == vertex2_id) or
            (e.get("vertex1_id") == vertex2_id and e.get("vertex2_id") == vertex1_id)
            for e in self.edges
        )
        
        if not edge_exists:
            return False, "Нет ребра между этими вершинами"
        
        # Проверяем, свободно ли ребро
        edge = next((e for e in self.edges if 
                    (e.get("vertex1_id") == vertex1_id and e.get("vertex2_id") == vertex2_id) or
                    (e.get("vertex1_id") == vertex2_id and e.get("vertex2_id") == vertex1_id)), None)
        if edge and edge.get("owner_id") is not None:
            return False, "Ребро уже занято"
        
        # В обычной фазе проверяем связь с постройками/дорогами
        if self.phase == GamePhase.TURN and not free_road:
            if not self._check_road_connection(player_id, vertex1_id, vertex2_id):
                return False, "Дорога должна быть связана с вашими постройками или дорогами"
        
        return True, "OK"
    
    def _check_road_connection(self, player_id: int, vertex1_id: int, vertex2_id: int) -> bool:
        """Проверяет связь дороги с постройками/дорогами игрока"""
        # Проверяем постройки на вершинах
        v1 = self.vertices_dict.get(vertex1_id)
        v2 = self.vertices_dict.get(vertex2_id)
        
        if v1 and v1.get("owner_id") == player_id:
            return True
        if v2 and v2.get("owner_id") == player_id:
            return True
        
        # Проверяем соседние дороги игрока (поиск в ширину)
        visited = set()
        queue = [vertex1_id, vertex2_id]
        
        while queue:
            current_vertex = queue.pop(0)
            if current_vertex in visited:
                continue
            visited.add(current_vertex)
            
            # Находим все дороги игрока, связанные с этой вершиной
            for edge in self.edges:
                if edge.get("owner_id") == player_id:
                    if edge["vertex1_id"] == current_vertex and edge["vertex2_id"] not in visited:
                        queue.append(edge["vertex2_id"])
                    elif edge["vertex2_id"] == current_vertex and edge["vertex1_id"] not in visited:
                        queue.append(edge["vertex1_id"])
        
        # Если мы достигли постройки игрока, дорога связана
        for vertex_id in visited:
            vertex = self.vertices_dict.get(vertex_id)
            if vertex and vertex.get("owner_id") == player_id:
                return True
        
        return False
    
    def build_road(self, player_id: int, vertex1_id: int, vertex2_id: int, free_road: bool = False) -> Dict[str, Any]:
        """Строит дорогу"""
        can_build, message = self.can_build_road(player_id, vertex1_id, vertex2_id, free_road)
        if not can_build:
            raise ValueError(message)
        
        resources = self.player_resources.setdefault(str(player_id), {})
        if not free_road:
            for resource, amount in self.ROAD_COST.items():
                resources[resource.value] = resources.get(resource.value, 0) - amount
        
        # Находим или создаем ребро
        edge = next((e for e in self.edges if 
                    (e.get("vertex1_id") == vertex1_id and e.get("vertex2_id") == vertex2_id) or
                    (e.get("vertex1_id") == vertex2_id and e.get("vertex2_id") == vertex1_id)), None)
        
        if edge:
            edge["owner_id"] = player_id
        else:
            edge = {
                "edge_id": len(self.edges),
                "vertex1_id": vertex1_id,
                "vertex2_id": vertex2_id,
                "owner_id": player_id
            }
            self.edges.append(edge)
        
        # Обновляем самую длинную дорогу
        self._update_longest_road()
        
        return {
            "success": True,
            "message": "Дорога построена",
            "resources": resources
        }
    
    # ========== МЕТОДЫ ПОДСЧЕТА ОЧКОВ И ПОБЕДЫ ==========
    
    def _update_victory_points(self, player_id: int):
        """Обновляет очки победы игрока"""
        points = 0
        
        # Очки за постройки
        for vertex in self.vertices:
            if vertex.get("owner_id") == player_id:
                if vertex.get("building_type") == BuildingType.SETTLEMENT.value:
                    points += 1
                elif vertex.get("building_type") == BuildingType.CITY.value:
                    points += 2
        
        # Очки за самую длинную дорогу
        if self.longest_road_player == player_id:
            points += 2
        
        # Очки за самую большую армию
        if self.largest_army_player == player_id:
            points += 2
        
        # Очки за карты очков победы
        player_dev_cards = self.player_dev_cards.get(str(player_id), [])
        points += sum(1 for card in player_dev_cards if card == DevelopmentCard.VICTORY_POINT)
        
        # Обновляем в game_state
        for player in self.players:
            if player.get("player_id") == player_id:
                player["victory_points"] = points
                break
    
    def _get_victory_points(self, player_id: int) -> int:
        """Получает очки победы игрока"""
        for player in self.players:
            if player.get("player_id") == player_id:
                return player.get("victory_points", 0)
        return 0
    
    def _calculate_longest_road(self, player_id: int) -> int:
        """Вычисляет длину самой длинной непрерывной дороги игрока (граф)"""
        player_roads = [e for e in self.edges if e.get("owner_id") == player_id]
        if not player_roads:
            return 0
        
        # Строим граф дорог игрока
        road_graph = {}
        for edge in player_roads:
            v1, v2 = edge["vertex1_id"], edge["vertex2_id"]
            if v1 not in road_graph:
                road_graph[v1] = []
            if v2 not in road_graph:
                road_graph[v2] = []
            road_graph[v1].append(v2)
            road_graph[v2].append(v1)
        
        # Находим самую длинную цепь через поиск в глубину
        max_length = 0
        
        def dfs(current_vertex: int, visited_edges: set, current_length: int):
            nonlocal max_length
            max_length = max(max_length, current_length)
            
            for neighbor in road_graph.get(current_vertex, []):
                edge_key = tuple(sorted([current_vertex, neighbor]))
                if edge_key not in visited_edges:
                    visited_edges.add(edge_key)
                    dfs(neighbor, visited_edges, current_length + 1)
                    visited_edges.remove(edge_key)
        
        # Запускаем DFS из каждой вершины
        for start_vertex in road_graph.keys():
            dfs(start_vertex, set(), 0)
        
        return max_length
    
    def _update_longest_road(self):
        """Обновляет игрока с самой длинной дорогой"""
        road_lengths = {}
        
        for player in self.players:
            player_id = player.get("player_id")
            length = self._calculate_longest_road(player_id)
            road_lengths[player_id] = length
        
        max_length = max(road_lengths.values()) if road_lengths else 0
        
        if max_length >= 5:
            candidates = [pid for pid, length in road_lengths.items() if length == max_length]
            
            # Если текущий обладатель все еще в лидерах, сохраняем
            if self.longest_road_player in candidates:
                self.longest_road_length = max_length
                return
            
            # Новый обладатель
            self.longest_road_player = candidates[0] if candidates else None
            self.longest_road_length = max_length
            
            # Обновляем очки всех игроков
            for player in self.players:
                self._update_victory_points(player.get("player_id"))
    
    def _update_largest_army(self, player_id: int):
        """Обновляет игрока с самой большой армией"""
        played_knights = self.player_played_knights.get(player_id, 0)
        
        if played_knights >= 3:
            # Проверяем, не больше ли у других
            max_knights = max(
                (self.player_played_knights.get(p.get("player_id"), 0) for p in self.players),
                default=0
            )
            
            if played_knights >= max_knights:
                # Если текущий обладатель все еще лидер, сохраняем
                if self.largest_army_player == player_id:
                    return
                
                # Проверяем, нет ли ничьей
                candidates = [
                    p.get("player_id") for p in self.players
                    if self.player_played_knights.get(p.get("player_id"), 0) == max_knights
                ]
                
                if len(candidates) == 1 or player_id in candidates:
                    self.largest_army_player = player_id
                    # Обновляем очки всех игроков
                    for player in self.players:
                        self._update_victory_points(player.get("player_id"))
    
    def _discard_resources(self, player_id: int, discard_count: int):
        """Сбрасывает ресурсы игрока (при выпадении 7)"""
        resources = self.player_resources.get(str(player_id), {})
        total = sum(resources.values())
        
        if total < discard_count:
            return
        
        # Игрок должен выбрать, какие ресурсы сбросить
        # Упрощенно: сбрасываем случайно
        discarded = 0
        resource_list = [r for r, count in resources.items() for _ in range(count)]
        random.shuffle(resource_list)
        
        for resource in resource_list[:discard_count]:
            resources[resource] = resources.get(resource, 0) - 1
            discarded += 1
    
    def check_win(self, player_id: int) -> bool:
        """Проверяет, выиграл ли игрок (10+ очков)"""
        return self._get_victory_points(player_id) >= 10
    
    # ========== НАЧАЛЬНАЯ ФАЗА ==========
    
    def handle_initial_setup(self, player_id: int, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает действие в начальной фазе"""
        if action == "place_settlement":
            vertex_id = data.get("vertex_id")
            return self.build_settlement(player_id, vertex_id, initial_setup=True, give_resources=False)
        elif action == "place_road":
            vertex1_id = data.get("vertex1_id")
            vertex2_id = data.get("vertex2_id")
            return self.build_road(player_id, vertex1_id, vertex2_id, free_road=True)
        else:
            raise ValueError(f"Неизвестное действие: {action}")
    
    def advance_setup_phase(self):
        """Переходит к следующему игроку в начальной фазе"""
        setup_round = self.setup_phase.get("round", 1)
        current_idx = self.setup_phase.get("player_index", 0)
        
        # Первый раунд: по часовой стрелке, второй: против часовой
        if setup_round == 1:
            current_idx = (current_idx + 1) % len(self.players)
            if current_idx == 0:
                # Переходим ко второму раунду (против часовой)
                setup_round = 2
                current_idx = len(self.players) - 1
        else:
            current_idx = (current_idx - 1) % len(self.players)
            if current_idx == len(self.players) - 1:
                # Начальная фаза завершена
                self.phase = GamePhase.TURN
                self.current_player_index = 0
        
        self.setup_phase["round"] = setup_round
        self.setup_phase["player_index"] = current_idx
        self.current_player_index = current_idx
    
    # ========== ТОРГОВЛЯ ==========
    
    def trade_with_bank(self, player_id: int, give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Dict[str, Any]:
        """Торговля с банком (4:1)"""
        resources = self.player_resources.get(str(player_id), {})
        result = TradingSystem.trade_with_bank(resources, give_resource, give_amount, take_resource, take_amount)
        return result
    
    def trade_with_port(self, player_id: int, vertex_id: int, give_resource: str, give_amount: int, take_resource: str, take_amount: int) -> Dict[str, Any]:
        """Торговля через порт"""
        vertex = self.vertices_dict.get(vertex_id)
        if not vertex or not vertex.get("has_port"):
            raise ValueError("На этой вершине нет порта")
        
        port_type = vertex.get("port_type", "generic")
        resources = self.player_resources.get(str(player_id), {})
        result = TradingSystem.trade_with_port(resources, port_type, give_resource, give_amount, take_resource, take_amount)
        return result
    
    def create_trade_offer(self, player_id: int, give_resources: Dict[str, int], want_resources: Dict[str, int]) -> Dict[str, Any]:
        """Создает предложение торговли"""
        offer = TradingSystem.create_trade_offer(player_id, give_resources, want_resources)
        self.pending_trades.append(offer)
        return offer
    
    def accept_trade_offer(self, trade_offer_id: int, accepting_player_id: int) -> Dict[str, Any]:
        """Принимает предложение торговли"""
        offer = next((t for i, t in enumerate(self.pending_trades) if i == trade_offer_id), None)
        if not offer:
            raise ValueError("Предложение торговли не найдено")
        
        from_player_id = offer["from_player_id"]
        from_resources = self.player_resources.get(str(from_player_id), {})
        to_resources = self.player_resources.get(str(accepting_player_id), {})
        
        result = TradingSystem.accept_trade_offer(offer, from_resources, to_resources)
        
        # Удаляем предложение
        self.pending_trades = [t for i, t in enumerate(self.pending_trades) if i != trade_offer_id]
        
        return result
    
    # ========== РАЗВИВАЮЩИЕ КАРТЫ ==========
    
    def buy_development_card(self, player_id: int) -> Dict[str, Any]:
        """Покупает развивающую карту"""
        resources = self.player_resources.get(str(player_id), {})
        
        card, updated_resources = DevelopmentCardSystem.buy_card(resources, self.dev_cards_deck)
        
        # Добавляем карту игроку (если не карта очков победы - она вскрывается сразу)
        player_cards = self.player_dev_cards.setdefault(str(player_id), [])
        if card == DevelopmentCard.VICTORY_POINT:
            # Карта очков победы добавляется сразу
            player_cards.append(card)
            self._update_victory_points(player_id)
        else:
            # Другие карты добавляются в руку (скрыты)
            player_cards.append(card)
        
        return {
            "success": True,
            "message": f"Куплена карта: {card}",
            "card": card,
            "resources": updated_resources,
            "revealed": card == DevelopmentCard.VICTORY_POINT
        }
    
    def play_development_card(self, player_id: int, card_type: str, card_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Играет развивающую карту"""
        player_cards = self.player_dev_cards.get(str(player_id), [])
        
        if card_type not in player_cards:
            raise ValueError(f"У игрока нет карты {card_type}")
        
        # Удаляем карту из руки
        player_cards.remove(card_type)
        
        # Обрабатываем карту
        if card_type == DevelopmentCard.KNIGHT:
            result = DevelopmentCardSystem.play_knight(player_id, self.player_played_knights)
            if result.get("has_largest_army"):
                self._update_largest_army(player_id)
            return result
        
        elif card_type == DevelopmentCard.ROAD_BUILDING:
            result = DevelopmentCardSystem.play_road_building(self.player_resources.get(str(player_id), {}))
            # Карта дает возможность построить 2 дороги бесплатно
            # Это обрабатывается на уровне API (флаг free_road)
            return result
        
        elif card_type == DevelopmentCard.YEAR_OF_PLENTY:
            if not card_data or "resource1" not in card_data or "resource2" not in card_data:
                raise ValueError("Нужно указать resource1 и resource2")
            resources = self.player_resources.get(str(player_id), {})
            result = DevelopmentCardSystem.play_year_of_plenty(resources, card_data["resource1"], card_data["resource2"])
            return result
        
        elif card_type == DevelopmentCard.MONOPOLY:
            if not card_data or "resource_type" not in card_data:
                raise ValueError("Нужно указать resource_type")
            resources = self.player_resources.get(str(player_id), {})
            all_resources = self.player_resources
            result = DevelopmentCardSystem.play_monopoly(resources, all_resources, card_data["resource_type"])
            return result
        
        else:
            raise ValueError(f"Неизвестный тип карты: {card_type}")
    
    def get_game_state(self) -> Dict[str, Any]:
        """Возвращает текущее состояние игры"""
        return {
            "players": self.players,
            "hexes": self.hexes,
            "hex_layout": self.hex_layout,
            "vertices": self.vertices,
            "vertices_dict": self.vertices_dict,
            "edges": self.edges,
            "player_resources": self.player_resources,
            "player_dev_cards": self.player_dev_cards,
            "player_played_knights": self.player_played_knights,
            "current_player_index": self.current_player_index,
            "phase": self.phase.value,
            "setup_phase": self.setup_phase,
            "last_dice_roll": self.dice_roll,
            "longest_road_player": self.longest_road_player,
            "longest_road_length": self.longest_road_length,
            "largest_army_player": self.largest_army_player,
            "robber_location": self.robber_location,
            "ports": self.ports,
            "dev_cards_deck": self.dev_cards_deck,
            "pending_trades": self.pending_trades
        }

