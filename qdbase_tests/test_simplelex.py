"""
test simplelex.py
"""

from qdbase import simplelex


def test_lex():
    """Test SimpleLex() basics."""
    lex = simplelex.SimpleLex()
    lex.lex("class thing:")
    assert lex.tokens == ["class", "thing", ":"]
