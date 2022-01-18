"""
SimpleLex is a simple lexical scanner. It scans one source line and returns
a list of tokens.

This is used by the XSource code generator. Because it is
use for bootstraping the QuickDev environment, it cannot use any XSource
features.

"""

SEP_WHITE_SPACE = " \t"
SEP_GRAMMAR = "()[]:#,@"
SEP_ALL = SEP_WHITE_SPACE + SEP_GRAMMAR
LEX_STATE_SCAN_LINE = 0
LEX_STATE_SCAN_TOKEN = 1


class SimpleLex:
    """
    Lexical analyzer.
    """

    __slots__ = ("debug", "start_ixs", "state", "token", "token_ix", "tokens")

    def __init__(self, debug=0):
        self.debug = debug
        self.state = LEX_STATE_SCAN_LINE
        self.token = ""
        self.token_ix = -1
        self.tokens = []
        self.start_ixs = []

    def save_token(self):
        """
        Add a token symbol to the analyzer.
        """
        self.tokens.append(self.token)
        self.start_ixs.append(self.token_ix)
        self.token = ""
        self.token_ix = -1

    def save_c(self, src_char, ix):
        """
        Save a token character to the analyzer.
        """
        self.tokens.append(src_char)
        self.start_ixs.append(ix)

    def lex(self, src_line):
        """
        Analyze a source file line.
        """
        if self.debug >= 1:
            print("LEX Line", src_line)
        self.tokens = []
        self.start_ixs = []
        self.token = ""
        self.token_ix = 0
        self.state = LEX_STATE_SCAN_LINE
        for ix, src_char in enumerate(src_line):
            if self.debug >= 1:
                print(f"'{self.token}', {self.state}, {ix} '{src_char}'")
            if self.state == LEX_STATE_SCAN_LINE:
                if src_char in SEP_WHITE_SPACE:
                    continue
                if src_char in SEP_GRAMMAR:
                    self.save_c(src_char, ix)
                    continue
                self.token = src_char
                self.token_ix = ix
                self.state = LEX_STATE_SCAN_TOKEN
            elif self.state == LEX_STATE_SCAN_TOKEN:
                if src_char in SEP_ALL:
                    self.save_token()
                    if src_char in SEP_GRAMMAR:
                        self.save_c(src_char, ix)
                    self.state = LEX_STATE_SCAN_LINE
                else:
                    self.token += src_char
        if self.state == LEX_STATE_SCAN_TOKEN:
            self.save_token()
