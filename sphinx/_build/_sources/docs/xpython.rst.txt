XPython
=======

XPython is a pre-processor that helps maximize production code
consistency and maximize DRY (Don't Repeat Yourself) implementation.

An 'xpy' is a source file that XPython translates into a standard
'py' python file. XPython uses an simple parsing defininition
inspired by the C preprocessor. An 'xpy' file contains lines of
XPython code and python code. XPython code lines begin with '#$' in the first
two characters of the line. All other lines are Python code lines.

XPython Code
-------------

**#$define name value**:

* name is a symbolic reference name. It consists of a sequence of
  letters, numbers and underscores. Name must be unique within the
  source file and cannot be redefined or undefined.
* value is a substitution value. It begins with the first non-space
  characters after name and ends with the last non-space character on
  the line. If quotation characters are included, they are substituted
  just like any other character. The substition syntax provides a
  method of adding quotes at the point of insertion so the value can be
  used as either quoted or not at various points of the generated code.

Python Code
-------------

Python code lines are processed for character substitions.
Substitutions can include any valid python code. The
substitution identifier format is '$[quote]name$'.

* The entire identifier must be on one line of python code.
  The substituted characters can be multi-line.
* The option [quote] is the single character "'" or '"'
  which is used to enclose the substition.
* The name can be a simple reference, not containing a '.'
  which is defined in the current source file or a module
  reference in the format module.name.
* The named substition must exist or the pre-processor
  reports an error.

XPython.py Documentation
---------------------------

.. automodule:: xpython
   :members:
