"""
Indexed Priority Queue (Min-Heap) implementation.

Supports O(log N) push, pop, decrease_key, and update operations,
with O(1) membership check and priority lookup.
Essential for high-performance Dijkstra, A*, and Contraction Hierarchies.
"""
from typing import Any, Dict, List, Optional, Tuple


class IndexedPriorityQueue:
    def __init__(self):
        # Heap array storing tuples: [key, priority, data]
        self._heap: List[List[Any]] = []
        # Mapping from key -> index in self._heap
        self._pos: Dict[Any, int] = {}

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def contains(self, key: Any) -> bool:
        return key in self._pos

    def get_priority(self, key: Any) -> Optional[float]:
        idx = self._pos.get(key)
        if idx is not None:
            return self._heap[idx][1]
        return None

    def peek(self) -> Optional[Tuple[Any, float, Any]]:
        if not self._heap:
            return None
        item = self._heap[0]
        return item[0], item[1], item[2]

    def push(self, key: Any, priority: float, data: Any = None) -> None:
        if key in self._pos:
            self.update(key, priority, data)
            return
        entry = [key, priority, data]
        idx = len(self._heap)
        self._heap.append(entry)
        self._pos[key] = idx
        self._sift_up(idx)

    def pop(self) -> Tuple[Any, float, Any]:
        if not self._heap:
            raise IndexError("pop from empty priority queue")
        root = self._heap[0]
        key, priority, data = root[0], root[1], root[2]
        del self._pos[key]

        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._pos[last[0]] = 0
            self._sift_down(0)

        return key, priority, data

    def decrease_key(self, key: Any, new_priority: float, data: Any = None) -> None:
        idx = self._pos.get(key)
        if idx is None:
            self.push(key, new_priority, data)
            return
        curr_priority = self._heap[idx][1]
        if new_priority < curr_priority:
            self._heap[idx][1] = new_priority
            if data is not None:
                self._heap[idx][2] = data
            self._sift_up(idx)

    def update(self, key: Any, new_priority: float, data: Any = None) -> None:
        idx = self._pos.get(key)
        if idx is None:
            self.push(key, new_priority, data)
            return
        old_priority = self._heap[idx][1]
        self._heap[idx][1] = new_priority
        if data is not None:
            self._heap[idx][2] = data
        if new_priority < old_priority:
            self._sift_up(idx)
        elif new_priority > old_priority:
            self._sift_down(idx)

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._pos[self._heap[i][0]] = i
        self._pos[self._heap[j][0]] = j

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) >> 1
            if self._heap[idx][1] < self._heap[parent][1]:
                self._swap(idx, parent)
                idx = parent
            else:
                break

    def _sift_down(self, idx: int) -> None:
        n = len(self._heap)
        while True:
            smallest = idx
            left = (idx << 1) + 1
            right = left + 1

            if left < n and self._heap[left][1] < self._heap[smallest][1]:
                smallest = left
            if right < n and self._heap[right][1] < self._heap[smallest][1]:
                smallest = right

            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break
