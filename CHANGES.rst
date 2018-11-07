*******
Changes
*******

Release 0.1 (2018-11-07)
========================

- Python 3.7 is now supported.

- The template for the output filename has been generalized to work
  sensibly in the case where overlays are nested more than two deep.

Templating
----------

- Added new attributes to layers:

  layer.is_overlay
      Boolean.  True if layer is an overlay.

  layer.lineage
      Sequence starting with layer and including each parent layer in
      turn.

  layer.overlay
      Returns the nearest overlay layer.  If the layer is an overlay,
      ``layer.overlay`` returns ``layer``, otherwise it returns the
      nearest parent layer which is an overlay.  If the layer is not
      contained within an overlay, returns ``None``.

- Added new values to context when expanding text in SVG:

  overlays
      A list of all overlay layers in the lineage of the text
      element, in order from outermost to innermost.

  course
      The outermost overlay layer.  (Equivalent to ``overlays[0]``.)
      This value already existed in the context used for filename expansion.

  overlay
      If the element is at least two overlays deep, this is the
      innermost overlay.  Otherwise it is unset.  This value already
      existed in the context used for filename expansion.

- Added new values to context when expanding output filenames:

  overlays
      A list of all overlay layers in the lineage of the overlay
      being expanded.


Bugs
----

- Templating: the ``safepath`` filter would fail with a ``TypeError``
  if applied to anything but a string.  Now it coerces its argument to
  text.

- Templating: (New style) layer flags in parent layers were not being
  removed from the layer labels.  (E.g. ``"{{ layer.parent.label }}"``
  was expanding to ``"[o] Some Overlay"``, when it should expand to
  ``"Some Overlay"``.)

- Pexpect==4.4.0 appears to have a subtle brokenness when
  ``searchwindowsize`` is set to something other than ``None``.  The
  problem seems to be in `pexpect.expect.py`__, and is triggered when
  multiple chunks of output are read before a match is found.

__ https://github.com/pexpect/pexpect/blob/master/pexpect/expect.py#L22

Bit-Rot
-------

- Use ``log.warning``, rather than the deprecated ``log.warn``.

Release 0.1a12 (2017-02-09)
===========================

- Remove tags from layer.label when expanding templated text in SVG file.

Release 0.1a11 (2017-02-01)
===========================

- Add ``--version`` command line option

Pager for ``coords``
--------------------

- A fancy pager (poor man's ``less``) has been added for viewing the
  output of the ``barnhunt coords`` subcommand.  If any of ``sys.stdin``
  or ``sys.stdout`` is not a tty, then the pager will be disabled.

- Since there is now a fancy pager, the default for ``--number-of-rows``
  has been increased to 1000.

Release 0.1a10 (2017-01-30)
===========================

Things still to be fixed
------------------------

Things still to be fixed: I'm pretty sure things are direly broken if
a drawing contains no overlays, and somewhat broken if a drawing
contains more than two layers of overlays.  The problems have to do
with how the output PDF filenames are determined...

New layer flag scheme
---------------------
New scheme for marking overlay and hidden layers.  One can now set
bit-flags on layers by including the flags in square brackets at the
beginning of the layer label.  I.e. a label like ``"[o] Master Trial
1"`` marks the layer as an overlay layer, while ``"[h] Prototypes"``
marks a hidden layer.

If no layers have any flags, ``barnhunt pdfs`` will fall back to the
old name-based heuristics for determing hidden and overlay layers.


Release 0.1a9 (2017-01-03)
==========================

* When exporting PDFs, run ``inkscape`` with ``--export-area-page``.

Packaging
---------

* Fix MANIFEST.in. Tests were not being included in sdist.

* Add ``url`` to package metadata.

Release 0.1a8 (2018-01-03)
==========================

* Ignore *ring* layers when identifying *course* layers.  (Now a layer
  labelled “C8 Ring” will not be treated as a course layer.)

* ``pdfs``: default ``--output-directory`` to ``.`` (avoiding exception when no
  explicit output directory is specified.)

Release 0.1a7 (2017-11-18)
==========================

* Change ``barnhunt coords`` so that it omits duplicate coordinates in its output.
  Also inrease the default for ``--number-of-rows`` to 50 and
  add the ``--group-size`` paramter to separate output into groups.

Release 0.1a6 (2017-11-15)
==========================

* Templating: ``LabelAdapter`` now stringifies to the layer label, and
  ``FileAdapter`` now stringifies to the file name.
* More refactoring, more tests
* Run several inkscapes in parallel.  This results in a major speedup.

Release 0.1a5 (2017-11-13)
==========================

* Expand text in SVG file.
* Add tests.
* Major code refactor.

Release 0.1a4 (2017-11-10)
==========================

PDFS
----

* Log unexpected output from inkscape.

* Add --no-shell-mode-inkscape option to control whether shell-mode inkscape
  optimization is used.

Release 0.1a3.post1 (2017-11-10)
================================

PDFS
----

* Reverse order that layers are considered.  (Layers are listed from
  bottom to top in the SVG file.)

Release 0.1a3 (2017-11-10)
==========================

PDFS
----

Replace spaces and other shell-unfriendly characters with underscores
in output file names.

Release 0.1a2 (2017-11-09)
==========================

Add subcommands for generating random numbers.

Release 0.1a1 (2017-11-07)
==========================

Initial release.
