# definition of data types for use with MDDL
#
# terminology aquired from:
#	https://www.adducation.info/how-to-improve-your-knowledge/units-of-measurement/
#	https://en.wikipedia.org/wiki/Unit_of_measurement
#
class SystemOfMeasurement():
    __slots__ = ('abreviation', 'name')
    def __init__(self, abreviation: str, name: str):
        self.abreviation = abreviation
        self.name = name

SystemOfMeasurement('SI', 'Metric SI Units')

Semantics

Genus = ('number', 'character')

class Property():
    __slots__ = ('abbrev', 'description', 'name')

class UnitOfMeasurement():
    __slots__ = ('abbrev', 'description', 'uom')

class DataType():
    def __init__(self):

class Restful()
    """
        Restful is a generic action that implements a restful resource.
    """


class DataTypeNumber(DataType):
    __slots__ = ('uom')
        def __init__(self):

class DataTypeCharacter(DataType):
        def __init__(self):
