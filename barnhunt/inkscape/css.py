""" Helpers for dealing with inline CSS

"""
from collections import MutableMapping
import logging

from six import python_2_unicode_compatible
from tinycss2 import (
    ast,
    parse_component_value_list,
    parse_declaration_list,
    serialize,
    )
from webencodings import ascii_lower


log = logging.getLogger()


def _warn_on_parse_errors(tokens, input):
    for tok in tokens:
        if tok.type == 'error':
            log.warning(
                "Ignoring CSS parse error: %s, while parsing %r",
                tok, input)


def _parse_inline_css(input):
    parsed = parse_declaration_list(input,
                                    skip_comments=True,
                                    skip_whitespace=True)
    _warn_on_parse_errors(parsed, input)
    if any(tok.type == 'at-rule' for tok in parsed):
        log.warning(
            "@ rules in CSS may not be handled correctly: %r",
            input)
    return parsed


@python_2_unicode_compatible
class InlineCSS(MutableMapping):
    def __init__(self, input=None):
        self._parsed = _parse_inline_css(input) if input else []

    def __getitem__(self, key):
        lower_key = ascii_lower(key)
        for tok in reversed(self._parsed):
            if tok.type == 'declaration' and tok.lower_name == lower_key:
                # XXX: how to deal with tok.important?
                return serialize(tok.value)
        raise KeyError(key)

    def __setitem__(self, key, value):
        lower_key = ascii_lower(key)
        parsed_value = parse_component_value_list(value,
                                                  skip_comments=True)
        _warn_on_parse_errors(parsed_value, value)

        self.__delitem__(key)
        tok = ast.Declaration(line=None, column=None,
                              name=key, lower_name=lower_key,
                              value=parsed_value,
                              important=False)
        self._parsed.append(tok)

    def __delitem__(self, key):
        lower_key = ascii_lower(key)
        self._parsed = [tok for tok in self._parsed
                        if not (tok.type == 'declaration'
                                and tok.lower_name == lower_key)]

    def __iter__(self):
        seen = set()
        for tok in self._parsed:
            if tok.type == 'declaration':
                if tok.lower_name not in seen:
                    seen.add(tok.lower_name)
                    yield tok.name

    def __len__(self):
        return len(list(self.__iter__()))

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self._parsed)

    def serialize(self):
        return serialize([tok for tok in self._parsed if tok.type != 'error'])

    __str__ = serialize
