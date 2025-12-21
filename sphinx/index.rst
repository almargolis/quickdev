.. QuickDev documentation master file, created by
   sphinx-quickstart on Mon Oct  5 09:54:34 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to QuickDev's documentation!
========================================

QuickDev is a metaprogramming toolkit and collection of DRY idioms that eliminates
boilerplate in Python applications. Rather than being a framework that competes with
Flask or Django, QuickDev works alongside them - generating the repetitive code you'd
otherwise write by hand.

**Core Capabilities:**

- **XSynth Preprocessor**: Transforms `.xpy` files into Python, using dictionaries and
  introspection to generate data models, classes, and patterns from high-level declarations
- **Reusable Idioms**: Pre-built packages like qdflask (authentication) and qdimages
  (image management) that integrate with Flask applications
- **Code Generation**: Extends DRY principles beyond runtime reuse into compile-time
  code generation

QuickDev captures decades of refined patterns, allowing you to reduce boilerplate while
maintaining readable, standard Python output. Use as much or as little as you need -
it complements your existing development workflow.


.. toctree::
   :maxdepth: 2

   docs/coding_style
   docs/ez_directories
   docs/ezstart
   docs/xpython



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
