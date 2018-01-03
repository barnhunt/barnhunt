*******
Changes
*******

Next Release
============

* Ignore *ring* layers when identifying *course* layers.  (Now a layer
  labelled “C8 Ring” will not be treated as a course layer.)

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
