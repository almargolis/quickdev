#!python
"""
    explicit is a preprocessor for python3 that adds language features that are desired
    for commercenode development.

    explicit supports python3 only, with at least verion 3.6. explicit expects to run
    in a venv environment.
"""

import sys

def explicit():
    """explicit main processing function."""
    for _ix, this in enumerate(sys.argv):
        print(_ix, this)

if __name__ == '__main__':
    explicit()
