from __future__ import annotations

import enum
import logging
import re
from typing import Callable
from typing import Collection
from typing import NamedTuple
from typing import Sequence

from .inkscape import svg

log = logging.getLogger()


class LayerFlags(enum.Flag):
    HIDDEN = enum.auto()
    OVERLAY = enum.auto()

    @property
    def flag_char(self) -> str:
        assert self.name
        return self.name[0].lower()

    def __str__(self) -> str:
        return "".join(flag.flag_char for flag in self.__class__ if self & flag)

    @classmethod
    def parse(cls, s: str) -> LayerFlags:
        value = cls(0)
        lookup = {flag.flag_char: flag for flag in cls}
        for c in set(s):
            flag = lookup.get(c)
            if flag is not None:
                value |= flag
            else:
                log.warning("unknown character '%s' in flags %r", c, s)
        return value


class LayerInfo(NamedTuple):
    flags: LayerFlags
    label: str
    output_basenames: Sequence[str] = ()
    exclude_from: Collection[str] = ()
    include_in: Collection[str] = ()


def parse_flagged_layer_info(elem: svg.LayerElement) -> LayerInfo:
    label = svg.layer_label(elem)

    exclude_from = set()
    include_in = set()
    m = re.match(
        r"\["
        r"  (?P<flags>\w*)"
        r"  (?:\|*(?P<output_basenames>(?:,*\w[-\w\d]*)*))?"
        r"  (?P<exclusions>(?:,*[!=]\w[-\w\d]*)*)"
        r"\]\s*",
        label,
        re.X,
    )
    if m:
        flags = LayerFlags.parse(m.group("flags"))
        output_basenames = [
            basename for basename in m.group("output_basenames").split(",") if basename
        ]
        for exclusion in m.group("exclusions").split(","):
            if exclusion.startswith("!"):
                exclude_from.add(exclusion[1:])
            elif exclusion.startswith("="):
                include_in.add(exclusion[1:])
            else:
                assert exclusion == ""
        label = label[m.end() :]
    else:
        flags = LayerFlags(0)
        output_basenames = []
    return LayerInfo(flags, label, output_basenames, exclude_from, include_in)


def _is_top_level(layer: svg.LayerElement) -> bool:
    """Is layer a top-level layer."""
    return svg.parent_layer(layer) is None


def _label_matches(layer: svg.LayerElement, pat: str | re.Pattern[str]) -> bool:
    return re.search(pat, svg.layer_label(layer)) is not None


def obs_is_ring(layer: svg.LayerElement) -> bool:
    """Match the top-level "Ring" layer.

    This layer is always displayed.
    """
    assert svg.is_layer(layer)
    return _is_top_level(layer) and _label_matches(layer, r"(?i)\bring\b")


def obs_is_course(layer: svg.LayerElement) -> bool:
    """Match the top-level "Course" layers

    These layers are displayed, one per coursemap.
    """
    assert svg.is_layer(layer)
    return (
        _is_top_level(layer)
        and not obs_is_ring(layer)
        and _label_matches(
            layer, r"(?i)\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b"
        )
    )


def obs_is_cruft(layer: svg.LayerElement) -> bool:
    assert svg.is_layer(layer)
    return _is_top_level(layer) and not obs_is_course(layer) and not obs_is_ring(layer)


def obs_is_overlay(layer: svg.LayerElement) -> bool:
    assert svg.is_layer(layer)
    parent = svg.parent_layer(layer)
    if parent is None:
        return False
    return svg.layer_label(parent) == "Overlays" and any(
        obs_is_course(ancestor) for ancestor in svg.ancestor_layers(parent)
    )


def parse_obs_layer_info(elem: svg.LayerElement) -> LayerInfo:
    """This is the old "heuristic" scheme of determining which layers are
    overlays and and cruft.

    This scheme is obsolete. It has not been used for drawing course
    maps since 2018.

    """
    if obs_is_cruft(elem):
        flags = LayerFlags.HIDDEN
    elif obs_is_course(elem) or obs_is_overlay(elem):
        flags = LayerFlags.OVERLAY
    else:
        flags = LayerFlags(0)
    return LayerInfo(flags, svg.layer_label(elem))


LayerInfoParser = Callable[[svg.LayerElement], LayerInfo]


def dwim_layer_info(tree: svg.ElementTree) -> LayerInfoParser:
    """Deduce layout type."""

    def has_flags(elem: svg.LayerElement) -> bool:
        return parse_flagged_layer_info(elem).flags != LayerFlags(0)

    if not any(has_flags(elem) for elem in svg.walk_layers(tree.getroot())):
        # Old style with overlays and hidden layers identified by
        # matching layer labels against various regexps.
        return parse_obs_layer_info
    else:
        # New style with flags in layer labels.
        # E.g. "[o] Overlay Layer Label", "[h] Hidden Layer"
        return parse_flagged_layer_info
