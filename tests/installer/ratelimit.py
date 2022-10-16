from functools import wraps
from typing import Any
from typing import Callable

import pytest
from requests import HTTPError


class MaybeRateLimited:
    def __init__(self) -> None:
        self.ratelimited = False

    def __call__(self, test: Callable[..., None]) -> Callable[..., None]:
        @wraps(test)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            if self.ratelimited:
                pytest.xfail("GitHub API rate limit exceeded")
            try:
                test(*args, **kwargs)
            except HTTPError as exc:
                if exc.response is not None:
                    if exc.response.headers.get("x-ratelimit-remaining") == "0":
                        self.ratelimited = True
                        pytest.xfail("GitHub API rate limit exceeded")
                raise

        return wrapper


mayberatelimited = MaybeRateLimited()
