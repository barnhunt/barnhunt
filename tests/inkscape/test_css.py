import logging

import pytest

from barnhunt.inkscape.css import InlineCSS


class TestInlineCSS:
    def test_setitem(self):
        css = InlineCSS()
        css["display"] = "none"
        assert css.serialize() == "display:none;"

        css = InlineCSS("display: inline; Display: block")
        css["display"] = "none"
        assert css.serialize() == "display:none;"

        css = InlineCSS("text-align:center")
        css["display"] = "none"
        assert css.serialize() == "text-align:center;display:none;"

    def test_getitem(self):
        css = InlineCSS("display: inline; text-align:center; Display:block")
        assert css["display"] == "block"
        with pytest.raises(KeyError):
            css["missing"]

    def test_delitem(self):
        css = InlineCSS("display: inline; text-align:center; Display: block")
        del css["display"]
        assert css.serialize() == "text-align:center;"

    def test_iter(self):
        css = InlineCSS("DISPLAY: inline; text-align:center; Display:block")
        assert list(css) == ["DISPLAY", "text-align"]

    def test_len(self):
        css = InlineCSS("DISPLAY: inline; text-align:center; Display:block")
        assert len(css) == 2

    def test_repr(self):
        css = InlineCSS()
        assert repr(css) == "<InlineCSS []>"

    def test_parse_error(self, caplog):
        css = InlineCSS("display:inline; mistake;text-align:center")
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "mistake" in warnings[0].getMessage()
        assert css.serialize() == "display:inline;text-align:center;"

    def test_warns_on_at_rule(self, caplog):
        style = "display:inline;@display print {display:block}"
        css = InlineCSS(style)
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "@ rules" in warnings[0].getMessage()
        assert css.serialize() == style

    def test_str(self):
        css = InlineCSS("x: fü")
        assert str(css) == "x: fü;"
