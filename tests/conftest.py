from io import BytesIO

from lxml import etree

import pytest

TEST_SVG = b"""<?xml version="1.0" encoding="ascii" standalone="no"?>
<svg id="root"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="layer"
     inkscape:groupmode="layer"
     inkscape:label="Level 1">
    <g id="sublayer"
       inkscape:groupmode="layer"
       inkscape:label="Level 2">
      <text>
        <tspan id="leaf">Layer: {{ layer.label }}</tspan>
      </text>
    </g>
  </g>
  <g id="layer2"
     inkscape:groupmode="layer"
     inkscape:label="Level 1, Second Layer">
  </g>
</svg>
"""


class XML(object):
    def __init__(self, raw_bytes):
        self.tree = etree.parse(BytesIO(raw_bytes))

    @property
    def root(self):
        return self.tree.getroot()

    def __getattr__(self, attr):
        elem = self.tree.find('.//*[@id="%s"]' % attr)
        if elem is None:
            raise AttributeError(attr)
        return elem


@pytest.fixture
def svg1():
    return XML(TEST_SVG)
