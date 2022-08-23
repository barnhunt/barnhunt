""" Helpers for dealing with inline CSS

"""
from __future__ import annotations

import logging
from typing import Iterable
from typing import Iterator
from typing import MutableMapping

from tinycss2 import ast
from tinycss2 import parse_component_value_list
from tinycss2 import parse_declaration_list
from tinycss2 import serialize

log = logging.getLogger()


def _warn_on_parse_errors(tokens: Iterable[ast.Node], input: str) -> None:
    for tok in tokens:
        if tok.type == "error":
            log.warning("Ignoring CSS parse error: %s, while parsing %r", tok, input)


def _parse_inline_css(input: str) -> list[ast.Node]:
    parsed = parse_declaration_list(input, skip_comments=True, skip_whitespace=True)
    _warn_on_parse_errors(parsed, input)
    if any(tok.type == "at-rule" for tok in parsed):
        log.warning("@ rules in CSS may not be handled correctly: %r", input)
    return parsed  # type: ignore[no-any-return]


class InlineCSS(MutableMapping[str, str]):
    def __init__(self, input: str | None = None):
        self._parsed = _parse_inline_css(input) if input else []

    def __getitem__(self, key: str) -> str:
        lower_key = ascii_lower(key)
        for tok in reversed(self._parsed):
            if tok.type == "declaration" and tok.lower_name == lower_key:
                # XXX: how to deal with tok.important?
                return serialize(tok.value)  # type: ignore[no-any-return]
        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        lower_key = ascii_lower(key)
        parsed_value = parse_component_value_list(value, skip_comments=True)
        _warn_on_parse_errors(parsed_value, value)

        self.__delitem__(key)
        tok = ast.Declaration(
            line=None,
            column=None,
            name=key,
            lower_name=lower_key,
            value=parsed_value,
            important=False,
        )
        self._parsed.append(tok)

    def __delitem__(self, key: str) -> None:
        lower_key = ascii_lower(key)
        self._parsed = [
            tok
            for tok in self._parsed
            if not (tok.type == "declaration" and tok.lower_name == lower_key)
        ]

    def __iter__(self) -> Iterator[str]:
        seen = set()
        for tok in self._parsed:
            if tok.type == "declaration":
                if tok.lower_name not in seen:
                    seen.add(tok.lower_name)
                    yield tok.name

    def __len__(self) -> int:
        return len(list(self.__iter__()))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._parsed!r}>"

    def serialize(self) -> str:
        return serialize(  # type: ignore[no-any-return]
            [tok for tok in self._parsed if tok.type != "error"]
        )

    __str__ = serialize


def ascii_lower(s: str) -> str:
    r"""Transform (only) ASCII letters to lower case.

    This is cribbed from webencodings.ascii_lower.
    """
    return s.encode("utf8").lower().decode("utf8")
