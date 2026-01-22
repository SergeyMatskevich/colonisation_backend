"""
Геометрия игрового поля Catan
Точное определение координат гексов, вершин и ребер в гексагональной сетке
"""
from typing import List, Dict, Tuple, Set, Optional
import math


class CatanGeometry:
    """Геометрические вычисления для игрового поля Catan"""
    
    # Стандартная раскладка Catan - расположение гексов по слоям
    # Внешний слой: 6 гексов (номера 0-5)
    # Средний слой: 12 гексов (номера 6-17)
    # Внутренний слой: 1 гекс (номер 18 - пустыня в центре)
    
    HEX_LAYOUT = [
        # Внешний слой (6 гексов)
        (0, -2), (1, -2), (2, -1), (2, 0), (1, 1), (0, 1),
        # Средний слой (12 гексов)
        (-1, -2), (-1, -1), (0, -1), (1, -1), (2, 1), (1, 2),
        (0, 2), (-1, 1), (-2, 0), (-2, -1), (-1, -3), (0, -3),
        # Внутренний слой (1 гекс - центр)
        (0, 0)
    ]
    
    @staticmethod
    def hex_to_pixel(hex_coord: Tuple[int, int], hex_size: float = 50) -> Tuple[float, float]:
        """Преобразует координаты гекса в пиксельные координаты"""
        q, r = hex_coord
        x = hex_size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
        y = hex_size * (3 / 2 * r)
        return (x, y)
    
    @staticmethod
    def get_hex_vertices(hex_coord: Tuple[int, int], hex_size: float = 50) -> List[Tuple[float, float]]:
        """Получает координаты 6 вершин гекса"""
        q, r = hex_coord
        center_x, center_y = CatanGeometry.hex_to_pixel((q, r), hex_size)
        vertices = []
        
        for i in range(6):
            angle = math.pi / 3 * i
            x = center_x + hex_size * math.cos(angle)
            y = center_y + hex_size * math.sin(angle)
            vertices.append((round(x, 2), round(y, 2)))
        
        return vertices
    
    @staticmethod
    def get_hex_neighbors(hex_coord: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Получает соседние гексы для данного гекса"""
        q, r = hex_coord
        # Шесть направлений в гексагональной сетке
        directions = [
            (1, 0), (1, -1), (0, -1),
            (-1, 0), (-1, 1), (0, 1)
        ]
        return [(q + dq, r + dr) for dq, dr in directions]
    
    @staticmethod
    def get_vertex_key(vertex_coord: Tuple[float, float]) -> str:
        """Создает уникальный ключ для вершины (округленный до определенной точности)"""
        x, y = vertex_coord
        precision = 1
        return f"{round(x, precision)},{round(y, precision)}"
    
    @staticmethod
    def get_all_board_vertices(hex_layout: List[Tuple[int, int]], hex_size: float = 50) -> Dict[str, Dict]:
        """Получает все уникальные вершины игрового поля"""
        vertices = {}
        vertex_id_counter = 0
        
        for hex_idx, hex_coord in enumerate(hex_layout):
            hex_vertices = CatanGeometry.get_hex_vertices(hex_coord, hex_size)
            
            for vertex_coord in hex_vertices:
                vertex_key = CatanGeometry.get_vertex_key(vertex_coord)
                
                if vertex_key not in vertices:
                    vertices[vertex_key] = {
                        "vertex_id": vertex_id_counter,
                        "x": vertex_coord[0],
                        "y": vertex_coord[1],
                        "hex_coords": [],
                        "neighbors": []
                    }
                    vertex_id_counter += 1
                
                vertices[vertex_key]["hex_coords"].append(hex_coord)
        
        # Находим соседние вершины (вершины, принадлежащие тем же гексам)
        for vertex_key, vertex_data in vertices.items():
            neighbors = set()
            for hex_coord in vertex_data["hex_coords"]:
                hex_vertices = CatanGeometry.get_hex_vertices(hex_coord, hex_size)
                for v in hex_vertices:
                    v_key = CatanGeometry.get_vertex_key(v)
                    if v_key != vertex_key:
                        neighbors.add(v_key)
            vertex_data["neighbors"] = list(neighbors)
        
        return vertices
    
    @staticmethod
    def get_vertex_neighbors(vertex_id: int, all_vertices: Dict[str, Dict]) -> List[int]:
        """Получает ID соседних вершин для данной вершины"""
        for vertex_data in all_vertices.values():
            if vertex_data["vertex_id"] == vertex_id:
                neighbor_ids = []
                for neighbor_key in vertex_data["neighbors"]:
                    neighbor_id = all_vertices[neighbor_key]["vertex_id"]
                    neighbor_ids.append(neighbor_id)
                return neighbor_ids
        return []
    
    @staticmethod
    def get_vertices_for_hex(hex_coord: Tuple[int, int], all_vertices: Dict[str, Dict], hex_size: float = 50) -> List[int]:
        """Получает ID вершин, принадлежащих данному гексу"""
        hex_vertices_coords = CatanGeometry.get_hex_vertices(hex_coord, hex_size)
        vertex_ids = []
        
        for v_coord in hex_vertices_coords:
            v_key = CatanGeometry.get_vertex_key(v_coord)
            if v_key in all_vertices:
                vertex_ids.append(all_vertices[v_key]["vertex_id"])
        
        return vertex_ids
    
    @staticmethod
    def are_vertices_adjacent(vertex1_id: int, vertex2_id: int, all_vertices: Dict[str, Dict]) -> bool:
        """Проверяет, являются ли две вершины соседними"""
        neighbors = CatanGeometry.get_vertex_neighbors(vertex1_id, all_vertices)
        return vertex2_id in neighbors
    
    @staticmethod
    def get_edges_for_board(all_vertices: Dict[str, Dict]) -> List[Dict]:
        """Получает все ребра (дороги) игрового поля"""
        edges = []
        edge_id_counter = 0
        processed_pairs = set()
        
        for vertex_key, vertex_data in all_vertices.items():
            vertex_id = vertex_data["vertex_id"]
            for neighbor_key in vertex_data["neighbors"]:
                neighbor_id = all_vertices[neighbor_key]["vertex_id"]
                
                # Создаем уникальную пару (меньший ID всегда первый)
                pair = tuple(sorted([vertex_id, neighbor_id]))
                
                if pair not in processed_pairs:
                    edges.append({
                        "edge_id": edge_id_counter,
                        "vertex1_id": pair[0],
                        "vertex2_id": pair[1],
                        "owner_id": None
                    })
                    edge_id_counter += 1
                    processed_pairs.add(pair)
        
        return edges
    
    @staticmethod
    def check_settlement_distance(vertex_id: int, all_vertices: Dict[str, Dict], existing_settlements: List[int]) -> bool:
        """
        Проверяет правило расстояния: поселения должны быть минимум в 2 ребрах друг от друга
        Это означает, что между ними должна быть минимум одна свободная вершина
        """
        # Получаем соседние вершины (на расстоянии 1 ребра)
        immediate_neighbors = set(CatanGeometry.get_vertex_neighbors(vertex_id, all_vertices))
        
        # Проверяем, нет ли поселений на соседних вершинах
        for settlement_vertex_id in existing_settlements:
            if settlement_vertex_id in immediate_neighbors:
                return False
            
            # Проверяем также соседей существующих поселений
            settlement_neighbors = set(CatanGeometry.get_vertex_neighbors(settlement_vertex_id, all_vertices))
            if vertex_id in settlement_neighbors:
                return False
        
        return True
    
    @staticmethod
    def get_resources_for_vertex(vertex_id: int, all_vertices: Dict[str, Dict], hexes: List[Dict], hex_layout: List[Tuple[int, int]], hex_size: float = 50) -> List[Dict]:
        """Получает ресурсы, доступные для вершины (гексы, прилегающие к этой вершине)"""
        # Находим координаты вершины
        vertex_coord = None
        for v_data in all_vertices.values():
            if v_data["vertex_id"] == vertex_id:
                vertex_coord = (v_data["x"], v_data["y"])
                break
        
        if vertex_coord is None:
            return []
        
        # Находим гексы, к которым принадлежит эта вершина
        resources = []
        for hex_idx, hex_coord in enumerate(hex_layout):
            if hex_idx < len(hexes):
                hex_data = hexes[hex_idx]
                hex_vertices = CatanGeometry.get_hex_vertices(hex_coord, hex_size)
                
                # Проверяем, принадлежит ли вершина этому гексу
                vertex_key = CatanGeometry.get_vertex_key(vertex_coord)
                for v_coord in hex_vertices:
                    if CatanGeometry.get_vertex_key(v_coord) == vertex_key:
                        resources.append({
                            "hex_index": hex_idx,
                            "hex_type": hex_data.get("hex_type"),
                            "number": hex_data.get("number"),
                            "has_robber": hex_data.get("has_robber", False)
                        })
                        break
        
        return resources


class PortLocation:
    """Расположение портов на игровом поле Catan"""
    
    # Порты расположены на краю игрового поля
    # В стандартной игре 9 портов: 4 обычных (3:1), 5 специальных (2:1)
    PORT_TYPES = {
        "generic": "3:1",  # Обмен 3 любых ресурса на 1 любой
        "wood": "2:1",
        "brick": "2:1",
        "sheep": "2:1",
        "wheat": "2:1",
        "ore": "2:1"
    }
    
    @staticmethod
    def assign_ports_to_vertices(board_vertices: Dict[str, Dict], hex_layout: List[Tuple[int, int]]) -> Dict[int, Dict]:
        """
        Назначает порты вершинам на краю игрового поля
        В реальной игре порты расположены на краю, соединяя гексы с морем
        """
        port_vertices = {}
        edge_vertices = PortLocation._find_edge_vertices(board_vertices, hex_layout)
        
        # Список типов портов для назначения
        port_types = ["wood", "brick", "sheep", "wheat", "ore", "generic", "generic", "generic", "generic"]
        
        # Назначаем порты случайным образом (в реальной игре есть определенная схема)
        import random
        random.shuffle(port_types)
        
        # Выбираем 9 вершин на краю для портов
        selected_vertices = random.sample(edge_vertices, min(len(edge_vertices), 9))
        
        for i, vertex_id in enumerate(selected_vertices):
            if i < len(port_types):
                port_vertices[vertex_id] = {
                    "port_type": port_types[i],
                    "trade_ratio": PortLocation.PORT_TYPES.get(port_types[i], "3:1")
                }
        
        return port_vertices
    
    @staticmethod
    def _find_edge_vertices(board_vertices: Dict[str, Dict], hex_layout: List[Tuple[int, int]]) -> List[int]:
        """Находит вершины на краю игрового поля"""
        # Вершина на краю имеет меньше соседей (меньше 3)
        edge_vertices = []
        for vertex_data in board_vertices.values():
            if len(vertex_data["neighbors"]) < 3:
                edge_vertices.append(vertex_data["vertex_id"])
        return edge_vertices

