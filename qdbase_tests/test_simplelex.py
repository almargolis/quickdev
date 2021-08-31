import qdbase.simplelex as simplelex

def test_lex():
    lex = simplelex.SimpleLex()
    lex.lex('class thing:')
    assert lex.tokens == ['class', 'thing', ':']
