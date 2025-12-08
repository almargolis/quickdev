from qdbase import initializer


class cls_1(initializer.qdobject):
    __slots__ = ("aa", "ab", "ac")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class cls_2(cls_1):
    __slots__ = ("ba", "bb", "bc")

    _required_args_ = ("bb",)
    _not_allowed_in_args_ = {"ba": 2, "bc": list}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


if __name__ == "__main__":
    # this stuff was to help during development
    o = cls_2(bb=None)
