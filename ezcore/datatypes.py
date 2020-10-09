# definition of data types for use with MDDL
#
# terminology aquired from:
#	https://www.adducation.info/how-to-improve-your-knowledge/units-of-measurement/
#	https://en.wikipedia.org/wiki/Unit_of_measurement
#
class SystemOfMeasurement(object):
    __slots__ = ('abreviation', 'name')
    def __init__(self, abreviation: str, name: str):
        self.abreviation = abreviation
        self.name = name

