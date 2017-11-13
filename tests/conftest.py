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
    def __init__(self, tree):
        self.root = tree

    def __getattr__(self, attr):
        elem = self.root.find('.//*[@id="%s"]' % attr)
        if elem is None:
            raise AttributeError(attr)
        return elem


@pytest.fixture
def svg1():
    return XML(etree.fromstring(TEST_SVG))
