"""
夜巡農場 (Nightwatch Farm) - BFS 網格尋路系統
負責敵人（小偷、野豬）與看門狗在有障礙物（圍欄、大型景觀）的網格地圖中尋找最短路徑。
"""

from collections import deque
from typing import List, Tuple, Optional, Set, Callable


class GridBFS:
    """
    2D 網格廣度優先搜尋 (Breadth-First Search, BFS) 尋路器
    保證在無權重網格圖中找到最短路徑。
    """
    
    # 上、下、左、右 四方向移動向量
    DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def in_bounds(self, x: int, y: int) -> bool:
        """檢查座標是否在地圖邊界內"""
        return 0 <= x < self.width and 0 <= y < self.height

    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        is_walkable_fn: Callable[[int, int], bool],
        target_can_be_obstacle: bool = False
    ) -> List[Tuple[int, int]]:
        """
        尋找從 start 到 goal 的最短路徑。
        
        :param start: 起點 (x, y)
        :param goal: 終點 (x, y)
        :param is_walkable_fn: 判定特定座標 (x, y) 是否可通行的回呼函數
        :param target_can_be_obstacle: 若目標本身是障礙物（如野豬鎖定攻擊的噴泉），
                                       設為 True 則會尋找抵達目標相鄰格的最短路徑。
        :return: 路徑座標串列 [(x1, y1), (x2, y2), ...]，若無路徑則回傳空串列 []
        """
        start_x, start_y = start
        goal_x, goal_y = goal

        if not self.in_bounds(start_x, start_y) or not self.in_bounds(goal_x, goal_y):
            return []
            
        if start == goal:
            return [start]

        # 若目標本身不可走，但不是以相鄰格為目標，則直接無路徑
        if not target_can_be_obstacle and not is_walkable_fn(goal_x, goal_y):
            return []

        queue = deque([start])
        came_from: dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        reached_target = False
        final_tile = goal

        while queue:
            current = queue.popleft()
            cx, cy = current

            # 檢查是否到達目的地
            if target_can_be_obstacle:
                # 若目標是障礙物，只要走到與目標相鄰 (曼哈頓距離為 1) 就算抵達
                if abs(cx - goal_x) + abs(cy - goal_y) == 1:
                    reached_target = True
                    final_tile = current
                    break
            else:
                if current == goal:
                    reached_target = True
                    final_tile = current
                    break

            for dx, dy in self.DIRECTIONS:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)

                if self.in_bounds(nx, ny) and neighbor not in came_from:
                    # 如果 neighbor 是目標且 target_can_be_obstacle=False，即使正常 walkable 也能走
                    if neighbor == goal and not target_can_be_obstacle:
                        came_from[neighbor] = current
                        reached_target = True
                        final_tile = neighbor
                        queue.clear()
                        break
                    elif is_walkable_fn(nx, ny):
                        came_from[neighbor] = current
                        queue.append(neighbor)

        if not reached_target:
            return []

        # 重構路徑 (從終點回溯到起點)
        path = []
        curr: Optional[Tuple[int, int]] = final_tile
        while curr is not None:
            path.append(curr)
            curr = came_from.get(curr)

        path.reverse()
        return path
