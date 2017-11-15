from multiprocessing import TimeoutError
import time

import pytest

from barnhunt.parallel import ParallelUnorderedStarmap


def test():
    def add(x, y):
        return x + y

    starmap = ParallelUnorderedStarmap(timeout=0.1)
    assert set(starmap(add, [(1, 2), (3, 4)])) == {3, 7}


def test_timeout():
    def slow_add(x, y):
        time.sleep(5)
        return x + y

    starmap = ParallelUnorderedStarmap(timeout=0.1)
    with pytest.raises(TimeoutError):
        list(starmap(slow_add, [(1, 2), (3, 4)]))
