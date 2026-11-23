"""
Unit tests for IndexedPriorityQueue.
"""
import pytest
from app.core.priority_queue import IndexedPriorityQueue


def test_ipq_basic_push_and_pop():
    ipq = IndexedPriorityQueue()
    assert ipq.is_empty()
    assert len(ipq) == 0

    ipq.push("A", 10.0)
    ipq.push("B", 5.0)
    ipq.push("C", 20.0)

    assert len(ipq) == 3
    assert ipq.contains("B")
    assert ipq.get_priority("B") == 5.0

    key, prio, _ = ipq.pop()
    assert key == "B"
    assert prio == 5.0

    key, prio, _ = ipq.pop()
    assert key == "A"
    assert prio == 10.0

    key, prio, _ = ipq.pop()
    assert key == "C"
    assert prio == 20.0
    assert ipq.is_empty()


def test_ipq_decrease_key():
    ipq = IndexedPriorityQueue()
    ipq.push("node_1", 50.0)
    ipq.push("node_2", 40.0)
    ipq.push("node_3", 30.0)

    # Decrease node_1 priority to 10.0
    ipq.decrease_key("node_1", 10.0)
    assert ipq.get_priority("node_1") == 10.0

    key, prio, _ = ipq.pop()
    assert key == "node_1"
    assert prio == 10.0


def test_ipq_update():
    ipq = IndexedPriorityQueue()
    ipq.push("X", 15.0)
    ipq.push("Y", 25.0)

    # Increase priority
    ipq.update("X", 35.0)
    assert ipq.peek()[0] == "Y"

    # Decrease priority back down
    ipq.update("X", 5.0)
    assert ipq.peek()[0] == "X"
