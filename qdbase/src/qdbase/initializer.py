"""
Initializer provides a mechanism for identifying how object
properties are initialized. This reduces boilerplate code and
supports serialization.


"""


class qdobject:
    __slots__ = ("qdi_debug",)

    def __init__(self, **kwargs):
        print(dir(self))
        print(self.__class__.__mro__)
        for this_ancestor in self.__class__.__mro__:
            print("-----------")
            try:
                slots = this_ancestor.__slots__
            except AttributeError:
                slots = None
            print(getattr(this_ancestor, "__name__"))
            print(slots)
            print(dir(this_ancestor))
            required_args = getattr(this_ancestor, "_required_args_", None)
            if required_args is not None:
                for this_arg in required_args:
                    if this_arg not in kwargs:
                        raise TypeError(f"Missing required argument '{this_arg}'")
                    setattr(self, this_arg, kwargs[this_arg])
            not_allowed_in_args = getattr(this_ancestor, "_not_allowed_in_args_", None)
            if not_allowed_in_args is not None:
                for this_attr_name, this_attr_value in not_allowed_in_args.items():
                    if this_attr_name in kwargs:
                        raise TypeError(
                            f"Exclude argument '{this_attr_name}' specified"
                        )
                    if isinstance(this_attr_value, type):
                        print("CLASS")
                        setattr(self, this_attr_name, this_attr_value())
                    else:
                        print("VALUE")
                        setattr(self, this_attr_name, this_attr_value)
