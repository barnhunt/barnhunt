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
    <g id="sublayer2"
       inkscape:groupmode="layer"
       inkscape:label="Level 2, Second Layer">
    </g>
  </g>
</svg>
"""

COURSEMAP1 = b"""<?xml version="1.0" encoding="ascii" standalone="no"?>
<svg id="root"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="cruft"
     inkscape:groupmode="layer"
     inkscape:label="Cruft">
  </g>
  <g id="ring"
     style="display:none"
     inkscape:groupmode="layer"
     inkscape:label="Ring">
    <text>
      <tspan id="ring_leaf">Ring</tspan>
    </text>
  </g>
  <g id="t1master"
     inkscape:groupmode="layer"
     inkscape:label="T1 Master">
    <g id="overlays"
       inkscape:groupmode="layer"
       inkscape:label="Overlays">
      <g id="blind1"
         inkscape:groupmode="layer"
         inkscape:label="Blind 1">
      </g>
      <g id="build"
         inkscape:groupmode="layer"
         inkscape:label="Build Notes">
      </g>
    </g>
  </g>
  <g id="t1novice"
     inkscape:groupmode="layer"
     inkscape:label="T1 Novice">
  </g>
</svg>
"""

COURSEMAP2 = b"""<?xml version="1.0" encoding="ascii" standalone="no"?>
<svg id="root"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
  <g id="cruft"
     inkscape:groupmode="layer"
     inkscape:label="[h] Junk">
  </g>
  <g id="ring"
     style="display:none"
     inkscape:groupmode="layer"
     inkscape:label="Outline">
    <text>
      <tspan id="ring_leaf">Ring</tspan>
    </text>
  </g>
  <g id="t1master"
     inkscape:groupmode="layer"
     inkscape:label="[o] T1 Master">
    <g id="overlays"
       inkscape:groupmode="layer"
       inkscape:label="Overlays">
      <g id="blind1"
         inkscape:groupmode="layer"
         inkscape:label="[o|blinds] Blind 1">
        <text>
          <tspan id="blind1_title"
            >{{ course.label }} - {{ overlay.label }}</tspan>
        </text>
      </g>
      <g id="build"
         inkscape:groupmode="layer"
         inkscape:label="[o|build_notes] Build Notes">
      </g>
    </g>
  </g>
  <g id="t1novice"
     inkscape:groupmode="layer"
     inkscape:label="[o] T1 Novice">
    <text>
      <tspan id="novice_title">{{ course.label }}</tspan>
    </text>
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


@pytest.fixture
def coursemap1():
    return XML(COURSEMAP1)


@pytest.fixture
def coursemap2():
    return XML(COURSEMAP2)
