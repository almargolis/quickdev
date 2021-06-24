"""
SimpleLex is a simple lexical scanner. It scans one source line and returns
a list of tokens.

This is used by the XSource code generator. Because it is
use for bootstraping the EzDev environment, it cannot use any XPython
features.

"""

SEP_WHITE_SPACE = " \t"
SEP_GRAMMAR = "()[]:#,@"
SEP_ALL = SEP_WHITE_SPACE + SEP_GRAMMAR
LEX_STATE_SCAN_LINE = 0
LEX_STATE_SCAN_TOKEN = 1

class SimpleLex:
    __slots__ = ('debug', 'start_ixs', 'state', 'token', 'token_ix', 'tokens')

    def __init__(self, debug=0):
        self.debug = debug
        self.state = LEX_STATE_SCAN_LINE

    def save_token(self):
        self.tokens.append(self.token)
        self.start_ixs.append(self.token_ix)
        self.token = ''
        self.token_ix = -1

    def save_c(self, c, ix):
        self.tokens.append(c)
        self.start_ixs.append(ix)

    def lex(self, src_line):
        if self.debug >= 1:
            print('LEX Line', src_line)
        self.tokens = []
        self.start_ixs = []
        self.token = ''
        self.token_ix = 0
        self.state = LEX_STATE_SCAN_LINE
        for ix, c in enumerate(src_line):
            if self.debug >= 1:
                print("'{}', {}, {} '{}'".format(self.token, self.state, ix, c))
            if self.state == LEX_STATE_SCAN_LINE:
                if c in SEP_WHITE_SPACE:
                    continue
                if c in SEP_GRAMMAR:
                    self.save_c(c, ix)
                    continue
                self.token = c
                self.token_ix = ix
                self.state = LEX_STATE_SCAN_TOKEN
            elif self.state == LEX_STATE_SCAN_TOKEN:
                if c in SEP_ALL:
                    self.save_token()
                    if c in SEP_GRAMMAR:
                        self.save_c(c, ix)
                    self.state = LEX_STATE_SCAN_LINE
                else:
                    self.token += c
        if self.state == LEX_STATE_SCAN_TOKEN:
            self.save_token()
