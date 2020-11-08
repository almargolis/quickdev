#!/usr/bin/python
"""
  Rdbms provides a standardized interface to accessing relational databases.
  It provides the following advantages vs. directly accessing the Python
  database libraries:
	- Automatcally hands RDBMS differences so the same code produces
		identical results accross all RDBMS engines. The
		differences that are handled include:
		- colation rules (esp. regarding case sensitive matches)
		- Unicode
		- schema formats
	- Integrates with TDict
	- Simplifed, RDBM is accessed via Python structures rather than SQL.
"""
#############################################
#
#  Rdbms Module
#
#
#  FEATURES
#
#  Automates common DB operations so that the client code stays simple.
#
#
#  WARNINGS
#
#	This is a MySql specific implementation, but the interface is
#	fairly generic.  If the need for other DBs arises, create a
#	base class with this interface and then DB specific descendants.
#	The client would then be DB-agnostic except for the actual
#	instance declaration.  Keep this in mind during enhancement and
#	keep the interface as generic as possible.
#
#
#  Copyright (C) 2001 by Albert B. Margolis - All Rights Reserved
#
#  2/28/2001:  Initial Release
#  5/12/2001:  Make RdbmsCursor a descendent of datastoreObject
#		and transform data into TupleObject objects.  This
#		is being done for bzgen so records can be indexed
#		by field name.  This is generally a more elegant
#		solution.
#  5/12/2001:  Move iterator logic and FldAsType action to
#		to datastoreObject and TupleObject because they generally
#		useful in record oriented applications.
#  5/12/2001:  Add convenence action Query to class Rdbms
#  1/19/2002:  Add host to Connect() to access remote databases.
#		Generalize test options to take all constants
#		from command line.
#  1/25/2002:  RdbmsCursor.__init__() failed if database invalid,
#		make db dependencies conditional.
#  2/15/2003:  Add Update()
#  2/22/2003:  Add Delete()
#  2/23/2003:  Add AutoId(), modify Update() with increment syntax
#  3/ 8/2003:  Add Select().  Fix Select() and Lookup() to support
#		numeric WHERE values instead of quoting everything
#		-- this needs to be replicated throughout. Fix
#		error in Update() increment syntax.  Add Lookup2()
#  3/22/2003:  Fix command line load option.  Add "l" to bzCmdArgs()
#		to get file name.  Add print line to verify file name.
#		Add "-s" to indicate that the load file is a simple
#		comma delimited file.  Move type-aware value list
#		code from Update() to MakeValueList().  Add call to
#		MakeValueList() to Insert() so it can properly handle
#		numeric fields.  Create GetFieldList() from Update()
#		and add to Insert().  Need to go through all methods
#		to replace ad-hoc code with updated actions.
#  3/29/2003:  Modify Select(), Update() and Delete() to use Where()
#  4/06/2003:  Add parmOrder to Select()
#  6/28/2003:  Add error checking to OpenTable() and LoadTables()
#  8/27/2005:  Add SelectKeyList() and LookupTuple()
#  4/14/2006:  Change Lookup() to use Select() instead of specific code.
# 10/25/2006:  Add JOIN capability to Select() and Where()
# 10/27/2006:  Change DB open to not open all tables when DB opens.
#		Change table open to capture all field description info
#		instead of just the field format.
#  3/30/2007:  Add UpdateCommonFields()
# 28 Sep 2009: Add FieldSpecs()
# 04 May 2011: There has been some intermediate maintenance, but nothing significant
#		for quite a while, till today.
#		- Change GetFieldList() to GetFieldsAndValues(), adding capability to use
#			a dict to supply both fields and values.
#		- Change MakeValueList() to MakeValueAssignments(), taking tuple from GetFieldsAndValue()
#		- Clean up code style in methods impacted by above.
# 29 Jul 2011: Major clean-up.
#		- Convert from TupleObject to bzComposition to integrate into Erd environment.
#		- structure to support multiple DBMS. Will eventually move away from MySql.
#			Right now need a memory only psuedo-DBMS.
#
#############################################

import MySQLdb
import os
import string
import sys
import sqlite3
from . import datastore
from . import tupledict
from . import tupledata

from . import commastr
from . import ertypes
from . import utils

DbTypeFiles						= 'F'
DbTypeMySql						= 'M'
DbTypeSqLite						= 'S'
DbTypeUnknown						= 'U'

WhereAllCode						= '**ALL**'

ParamStyleFormat					= 'format'
ParamStyleQmark						= 'qmark'

class MySqlFieldType(object):
  __slots__ = ('PhysicalType', 'name', 'typeNumber')
  def __init__(self, parmName, parmTypeNumber, parmType):
    self.PhysicalType	= parmType
    self.name			= parmName
    self.typeNumber		= parmTypeNumber

MySqlFieldTypes			= []
MySqlFieldTypes.append(MySqlFieldType('int',       3, ertypes.Core_IntegerTypeCode))
MySqlFieldTypes.append(MySqlFieldType('bigint',    8, ertypes.Core_IntegerTypeCode))
MySqlFieldTypes.append(MySqlFieldType('text',    252, ertypes.Core_StringTypeCode))
MySqlFieldTypes.append(MySqlFieldType('varchar', 253, ertypes.Core_StringTypeCode))
MySqlFieldTypes.append(MySqlFieldType('char',    254, ertypes.Core_StringTypeCode))

# https://hackage.haskell.org/package/mysql-0.1.1.4/docs/src/Database-MySQL-Base-Types.html
#               ((1), Tiny),
#               ((2), Short),
#               ((3), Long),
#               ((4), Float),
#               ((5), Double),
#               ((6), Null),
#               ((7), Timestamp),
#               ((8), LongLong),
#               ((10), Date),
#               ((11), Time),
#               ((12), DateTime),
#               ((13), Year),
#               ((14), NewDate),
#               ((15), VarChar),
#               ((16), Bit),
#               ((246), NewDecimal),
#               ((247), Enum),
#               ((248), Set),
#               ((249), TinyBlob),
#               ((250), MediumBlob),
#               ((251), LongBlob),
#               ((252), Blob),
#               ((253), VarString),
#               ((254), String),
#               ((255), Geometry)


#MySqlCharType			= "char"		# type 254
#MySqlMediumtextType		= "mediumtext"
#MySqlVarcharType		= "varchar"		# type 255
#MySqlTextType			= "text"		# type 252
#MySqlIntType			= "int"			# type 3

FieldNameKey			= 'FieldName'
FieldFormatKey			= 'Format'
FieldNullKey			= 'Null'
FieldKeyKey			= 'Key'
FieldDefaultKey			= 'Default'
FieldExtraKey			= 'Extra'
FieldPrivelegesKey		= 'Priveleges'

LEFTOUTERJOIN			= "LOJ"

def DumpStructure(parmCursor):
    print("************** Description ************")
    for fld in parmCurs.description:
        print("--> " + repr(fld) + " <--")

def PrintError(parmSource):
  wsExceptionInfo		= sys.exc_info()		# (type, value, traceback)
  print("%s failed: %s: %s !!!" % (parmSource, repr(wsExceptionInfo[0]), repr(wsExceptionInfo[1])))
  if wsExceptionInfo[2] is not None:
    print(wsExceptionInfo[2])


def TranslateErdPhysicalFieldTypeAndLenToMySqlFieldFormatAndType(parmDataTypes, parmErdPhysicalFieldType, parmFieldLen):
  wsMySqlFieldFormat		= None
  wsMySqlFieldType		= None
  if parmErdPhysicalFieldType == parmDataTypes.StringCode:
    wsMySqlFieldType		= MySqlCharType
    wsMySqlFieldFormat		= '%s(%d)' % (wsMySqlFieldType, utils.Int(parmFieldLen))
  if parmErdPhysicalFieldType == parmDataTypes.IntegerCode:
    wsMySqlFieldFormat = '%s(%d)'  % (wsMySqlFieldType, utils.Int(parmFieldLen))
  return (wsMySqlFieldFormat, wsMySqlFieldType)

def TableIsOpen(parmTable, Debug=0):
  if parmTable is None:
    if Debug >= 1: print("TableIsOpen(): No table object")
    return False
  if not isinstance(parmTable, RdbmsTable):
    if Debug >= 1: print("TableIsOpen(): Not a table object (%s) value: %s" % (
    				parmTable.__class__,  repr(parmTable)))
    return False
  if parmTable.rdbmsTDict is None:
    if Debug >= 1: print("TableIsOpen(): No fields object")
    return False
  if len(parmTable.rdbmsTDict.elements) > 0:
    if Debug >= 1: print("TableIsOpen(): table is open")
    return True
  if Debug >= 1: print("TableIsOpen(): default")
  return False

class Reference(object):
  def __init__(self, parmFieldName, Operator=None, Operand=None):
    self.fieldName					= parmFieldName
    self.operator					= Operator
    self.operand					= Operand
  def Expression(self, parmTable, parmValueParameters):
    # value is a field name optionally an oparation with a literal or another field.
    # This could easily be more complex, but handles most common needs.
    wsExpression					= self.fieldName
    if self.operator is not None:
      wsExpression					+= " %s " % (self.operator)
      if isinstance(self.operand, Reference):
        wsExpression					+= " %s" % (self.operand.fieldName)
      else:
        wsExpression					+= parmTable.db.paramcode
        parmValueParameters.append(self.operand)
    return wsExpression

class RdbmsTable(datastore.DataStoreObject):
    __slots__ = ('cursor', 'db', '_lastRequest', 'modelTDict', 'tableName')
    def __init__(self, TableName=None, Db=None, ExeController=None, ModelTDict=None, Debug=None):
      # Db is a RdbmsConnector
      wsExeController					= ExeController
      if (wsExeController is None) and (Db is not None):
        wsExeController					= Db.exeController
      if (Debug is None) and (Db is not None):
        Debug						= Db.debug
      datastore.DataStoreObject.__init__(self, ExeController=wsExeController, IsTDictDynamic=False, Debug=Debug)
      self.db						= Db
      self.cursor						= None
      if (self.db is not None) and (self.db.db is not None):
        self.cursor					= self.db.db.cursor()
      self._lastQuery					= ""
      self.modelTDict					= ModelTDict
      self.tableName					= TableName
      self.rdbmsTDict					= None
      if (self.tableName is not None) and (self.tableName != ""):
        self.rdbmsTDict					= self.BuildTDictForTable()

    #
    # BuildTDictForQueryResult()
    #
    # self.cursor.description returns an array of tuples corresponding
    # to each field in the result. The tuple elements are:
    #	[0] Field Name
    #	[1] Field Type numeric code
    #		3 = int
    #		255 ? varchar
    #	[2]
    #	[3] max field lenght
    #	[4] max field length (seems to be a duplicate)
    #	[5]
    #	[6] 0 = Primary Key, 1 = Not
    #
    def BuildTDictForQueryResult(self):
      self._tdict						= tupledict.TupleDict(ExeController=self.exeController)
      for wsFld in self.cursor.description:
        #print "XYZ", `self.cursor.description`
        wsMySqlFieldName					= wsFld[0]
        wsMySqlMaxLength					= wsFld[3]
        wsElementPhysicalType				= None
        wsElementPhysicalType				= self.db.TranslateFieldType(Fld=wsFld, Table=self)
        wsElement						= self._tdict.AddScalarElement(wsMySqlFieldName,
								PhysicalType=wsElementPhysicalType,
								MaxLength=wsMySqlMaxLength)
        if wsFld[6] == 0:
          wsElement.ConfigureAsUnique()

    def QueryRecordsFound(self):
      if len(self) > 0:
        return True
      else:
        return False

    #
    # RunQuery() Executes a query
    #		It calls ClearData() even if no return dat is expected in order
    #			to avoid confusion regarding data left from prior RunDataQuery()
    #		Returns True if query executes. That just means that the database
    #			considered it valid SQl, not that it did what you want.
    #			False means it could not be exeucted.
    #
    def RunQuery(self, parmQuery, parmParms=()):
        if parmQuery[-1] != ";":
            parmQuery					+= ";"
        if self._debug > 0:
            print("Query: " + parmQuery)
        self.ClearData(Query=parmQuery)
        if self.cursor is None:
            self._lastErrorMsg = "RDBMS table cursor closed."
            return False
        try:
            #print "QQQ", parmQuery
            #print "ZZZ", parmParms
            if parmParms is None:
                # SqLite raises an exception is parms are None or ()
                self.cursor.execute(parmQuery)
            else:
                self.cursor.execute(parmQuery, parmParms)
            if self._debug > 0:
                print("Query successful")
            self._lastRequest				= parmQuery
            self._lastQuery				= self.db.GetLastQuery(Table=self, Query=parmQuery)
        except:
            if self._debug > 0:
                PrintError("Query")
            self._lastErrorMsg = "RDBMS query failed:"
            if self.exeController is not None:
                self.exeController.errs.AddDevCriticalMessage("RunQuery() exception for '%s' (%s)." % (parmQuery, repr(parmParms)))
                self.exeController.errs.AddTraceback()
                return False
            else:
                raise
        self.db.db.commit()
        return True

    #
    # RunDataQuery() Executes a query that returns data.
    #			It is execute() and fetchall into _tuples.
    # 		Returns None is the query causes an exception. It returns
    #		_tuples in the case of successful execution. That will be
    #		zero length if the query doesn't find data.
    #
    def RunDataQuery(self, parmQuery, parmParms=None):
      if not self.RunQuery(parmQuery, parmParms=parmParms):
        return None							# self._lastErrorMsg set by RunQuery()
      self.BuildTDictForQueryResult()
      wsQueryResult				= self.cursor.fetchall()
      if len(wsQueryResult) >= 1:
        for wsThisRow in wsQueryResult:
          self.AppendData(wsThisRow)
      return self._tuples

    def PrintList(self):
      wsQuery					= "SELECT * FROM " + self.tableName
      wsAnswer					= self.RunDataQuery(wsQuery)
      if wsAnswer:
        for wsRec in wsAnswer:
          print("--> " + repr(wsRec) + " <--")
      else:
        print("Query " + repr(wsQuery) + " failed")

    def QueryResultCt(self):
      return len(self.data)

    # RdbmsTable
    def BuildTDictForTable(self):
        wsTDict					= self.db.BuildTDictForTable(Table=self)
        self.ClearData()							# clear fields from record buffer
        return wsTDict

    def AutoId(self):
        #return self.cursor.insert_id()
        return self.cursor.lastrowid

    def create_database(self, database_name, if_not_exists=False,
                        character_set='utf8',
                        collation_name='utf8_general_ci'):
        """
        Create a datbase. This is specifically for MySql/MariaDb.
        Sqlite datbases are created instrinsically when a
        connection is established. It has a different mechanism
        to set default character sets and colation orders.

        MySql/MariaDb support "show character set;" and

        """
        sql = 'CREATE DATABASE '
        if if_not_exists:
            sql += 'IF NOT EXISTS '
        sql += database_name
        if character_set is not None:
            sql += ' CHARACTER SET ' + character_set
        if collation is not None:
            sql += ' COLLATE ' + collation_name
         sql += ';'

    def add_user(self):
        pass

        """
        CREATE USER 'newuser'@'localhost' IDENTIFIED BY 'password';
        GRANT ALL PRIVILEGES ON * . * TO 'newuser'@'localhost';
        FLUSH PRIVILEGES;

        related:
        mysqladmin -u root password NEWPASSWORD
        mysql_secure_connection
        """

    def backup_table(self):
        pass

        """
        mysqldump -u{backup_user} -p{backup_password}
        from_db_name table_to_backup > backup_file.sql
        """
        
    #
    # Utf8: Sqlite stores all text as UTF8. MySql has many options. I support ASCII for transitional
    # convenience. In the long run, everything should be stored as UTF8. I might want to use an
    # allowed characters editing parameter, but maybe its best to enforce any character restrictions
    # indirectly through dictionaries and code lists.
    #
    # Mysql UTF8 is not a complete implemention. Three bytes/code point max. UTF8MB4 added in 5.5.3
    # adds 4 byte support.
    #
    #
    # Case Sensitivity: Sqlite NOCASE only considers English letters (ASCII letters) which is good enough
    # for me know, but could be confusing if internationalization ever matters.
    #
    def CreateTableFromTDict(self, parmTDict, TableName=None):
      self.tableName				= TableName
      if self.tableName is None:
        self.tableName				= parmTDict._name
      if self.tableName is None:
        # Class names are typically hungarian notation with an app prefix.
        # If not specified, use the module name for the table name
        wsClassName				= parmTDict.__class__.__name__
        wsIx					= utils.FindFirstUpperCaseLetter(wsClassName)
        if wsIx >= 0:
          self.tableName				= wsClassName[wsIx:]
      wsFieldCt					= 0
      wsQuery					= "CREATE TABLE " + self.tableName + " ("
      for wsThisTDictElement in parmTDict.Elements():
        if wsThisTDictElement.roleType in ertypes.Core_VirtualRoleCodes:
          continue
        if wsThisTDictElement.roleType == ertypes.Core_PrimaryParticipantRoleCode:
          continue
        if wsThisTDictElement.roleType == ertypes.Core_SecondaryParticipantRoleCode:
          continue
        wsFieldCt					+= 1
        wsFieldSpec				= self.db.MakeColumnDefFromTDictElement(wsThisTDictElement)
        if wsFieldCt > 1:
          wsQuery					+= ', '
        wsQuery					+= wsFieldSpec
      wsQuery					+= ')'
      if self.RunQuery(wsQuery):
        self.rdbmsTDict				= self.BuildTDictForTable()
        return self
      else:
        self.rdbmsTDict				= None
        return None

    def Drop(self):
      self.RunQuery("DROP TABLE " + self.tableName)
      return None

    def AddField(self, parmTDictElement):
      wsFieldSpec					= self.MakeMySqlColumnDefFromTDictElement(parmTDictElement)
      wsQuery					= "alter table %s add column %s" % (self.tableName, wsFieldSpec)
      return self.RunQuery(wsQuery)

    def Post(self, parmValues):
      if self.modelTDict is None:
        self.modelTDict				= self.exeController.GetDbTableModel(self.tableName)
      if self.modelTDict is None:
        self._lastErrorMsg			= "Model TDict required for Post()."
        return False
      if not self.modelTDict.ValidateObject(parmValues, InstancePhysicalType=ertypes.Core_MapDictTypeCode):
        return False
      wsUdiFieldName				= self.rdbmsTDict.udi._name
      if wsUdiFieldName in parmValues:
        wsUdiValue				= parmValues[wsUdiFieldName]
      else:
        wsUdiValue				= 0
      if wsUdiValue > 0:
        wsPostAction				= "U"
        wsWhere					= (wsUdiFieldName, '=', wsUdiValue)
      else:
        wsPostAction				= "I"
        wsWhere					= None
      wsTimestamp					= utils.DateToYMDHMS()
      if self.modelTDict.updateTimestamp is not None:
        parmValues[self.modelTDict.updateTimestamp._name]	= wsTimestamp
      if wsPostAction == "I":
        if self.modelTDict.createTimestamp is not None:
          parmValues[self.modelTDict.createTimestamp._name]	= wsTimestamp
        wsResult					= self.Insert(parmValues)
        parmValues[wsUdiFieldName]		= self.AutoId()
      else:
        wsResult					= self.Update(parmValues, Where=wsWhere)
      return wsResult

    def Insert(self, parmValues, parmFieldList=None):
      # This is a relatively thin wrapper around the DBMS insert. It just takes a list of field names
      # names and values, constructs SQL and then lets the database do its thing.
      # Use Post() to add records with full TDict control logic.
      wsFieldsAndValues				= self.GetFieldsAndValues(parmValues, parmFieldList)
      if not wsFieldsAndValues:
        return None							# GetFieldsAndValues() sets self._lastErrorMsg
      (wsFieldsStr, wsValuesStr, wsValueParms)	= self.MakeValueAssignments(wsFieldsAndValues)
      if wsValuesStr is None:
        return False							# MakeValueAssignments() sets self._lastErrorMsg
      wsQuery					= "INSERT INTO {TableName} ({FieldNames}) VALUES ({FieldValues})".format(
							TableName=self.tableName,
							FieldNames=wsFieldsStr,
							FieldValues=wsValuesStr)
      return self.RunQuery(wsQuery, wsValueParms)

    def IsOpen(self):
      if self.rdbmsTDict is None:
        return False
      if len(self.rdbmsTDict) < 0:
        return False
      return True

    # RdbmsTable
    def MakeValueAssignments(self, parmFieldsAndValues, SetMode=False):
      # Make field list, value list and value parameters for insert.
      # This used to make a value string with quoted values, now it sets things up for
      # the python library to quote.
      #
      if not self.IsOpen():
        self._lastErrorMsg			= "Table Not Open"
        return (None, None)
      wsFieldsStr					= ""
      wsValuesStr					= ""
      wsValueParameters				= []

      for (wsFieldIx, wsThisValue) in enumerate(parmFieldsAndValues[1]):
        # In SetMode, field names and vailue go in one string.
        # Otherwise we create separate fieldn name and values strings
        wsFieldName				= parmFieldsAndValues[0][wsFieldIx]
        if wsFieldIx > 0:
          wsValuesStr				+= ", "
          if not SetMode:
            wsFieldsStr				+= ", "
        if SetMode:
          wsValuesStr				+= wsFieldName + ' = '
        else:
          wsFieldsStr				+= wsFieldName
        if isinstance(wsThisValue, Reference):
          wsValuesStr				+= wsThisValue.Expression(self, wsValueParameters)
        else:
          # value is a simple literal
          wsValuesStr				+= self.db.paramcode
          wsValueParameters.append(wsThisValue)
      return (wsFieldsStr, wsValuesStr, tuple(wsValueParameters))

    def FormatValue(self, parmFieldName, parmValue):
      return parmValue
      # This formats value per dictionary. May not be needed now that I am letting
      # the library do the quoting. Might still need to take care of some special cases.
      wsThisValue					= parmValue
      if not isinstance(wsThisValue, type("")):
        wsThisValue				= repr(wsThisValue)
      if not parmFieldName:
        self._lastErrorMsg			= "Missing field name"
        if self._debug > 0:
          print(self._lastErrorMsg)
        return None
      if self.rdbmsTDict.HasElement(parmFieldName):
        wsFieldSpec				= self.rdbmsTDict.Element(parmFieldName)
      else:
        self._lastErrorMsg			= "Undefined field name '%s'" % (parmFieldName)
        if self._debug > 0:
          print(self._lastErrorMsg)
        return None
      if wsFieldSpec.physicalType == ertypes.Core_IntegerTypeCode:
        if (wsThisValue is None) or (wsThisValue == '') or (wsThisValue == 'None'):
          wsThisValue				= "0"
        if wsThisValue[-1:] == "L":
          wsThisValue				= wsThisValue[:-1]
        wsDecPos					= string.find(wsThisValue, '.')
        if wsDecPos >= 0:
          wsThisValue				= wsThisValue[:wsDecPos] + wsThisValue[wsDecPos+1:]
      else:
        if (wsFieldSpec.maxLength > 0) and (len(wsThisValue) > wsFieldSpec.maxLength):
          # Truncate excess lenght of strings. At this point we want to write what we can,
          # not fail the update which is the native MySql behavior.
          wsThisValue				= wsThisValue[:wsFieldSpec.maxLength]
        wsThisValue				= wsThisValue.replace("'", "''")
        wsThisValue				= "'" + wsThisValue + "'"
      return wsThisValue

    # RdbmsTable
    def GetFieldsAndValues(self, parmValues, FieldList=None, OmitUdi=False):
        # This gets the field name and values parameters of Insert and Update and converts
        # them to corresponding arrays for use in creating the query in MakeValueAssignments().
        #
        if self.rdbmsTDict is None:
          self._lastErrorMsg			= "Table not open - no operations allowed."
          return None								# table is not open
        try:
          wsItemList				= list(parmValues.items())
        except:
          wsItemList				= None
        if wsItemList is not None:
          # It looks like we got a dict or tuple.
          wsValueList				= []
          wsFieldList				= []
          for (wsThisKey, wsThisValue) in wsItemList:
            # Only take valid field names. ignore extraneous fields.
            #
            wsElement				= self.rdbmsTDict.Element(wsThisKey)
            if wsElement is not None:
              # The field is defined.
              # OmitUdi logic needs to be duplicated below.
              if OmitUdi and wsElement.roleType == ertypes.Core_UdiRoleCode:
                pass
              else:
                wsValueList.append(wsThisValue)
                wsFieldList.append(wsThisKey)
        else:
          # Lets look at it some other ways
          if isinstance(parmValues, (list, tuple)):
            wsValueList				= parmValues
            wsFieldList				= FieldList
          else:
            # if its not a list assume its a single scalar value and put that in a list
            wsValueList				= [parmValues]
            if FieldList is None:
              wsFieldList				= None
            else:
              wsFieldList				= [FieldList]
        if wsFieldList is not None:
          if len(wsFieldList) < 1:
            self._lastErrorMsg			= "Field list lenght is zero. Nothing to update"
            return None
          # supplied field count must match supplied value count
          if len(wsFieldList) != len(wsValueList):
            self._lastErrorMsg			= "Value list ct %d does not match field parm ct %d %s %s" % (
  							len(wsFieldList), len(wsValueList), repr(wsFieldList), repr(wsValueList))
            if self._debug > 0:
              print(self._lastErrorMsg)
            return None
        else:
          wsFieldList				= []
          if len(self.rdbmsTDict) < len(wsValueList):
            self._lastErrorMsg			= "Value list ct %d does not match table field ct %d %s %s" % (
							len(self.rdbmsTDict), len(wsValueList), repr(self.rdbmsTDict), repr(wsValueList))
            if self._debug > 0:
              print(self._lastErrorMsg)
            return None
          for wsThisFieldSpec in self.rdbmsTDict.Elements():
            wsFieldList.append(wsThisFieldSpec._name)
        return (wsFieldList, wsValueList)

    def Delete(self, parmWhere=None):
        if not parmWhere:
          self._lastErrorMsg			= "Where clause required for Delete funtion."
          return None									# avoid accidental "delete all"
        if parmWhere == WhereAllCode:
          wsWhere					= ""
        else:
          wsWhere					= self.Where(parmWhere)
        wsQuery					= "DELETE FROM %s %s" % (self.tableName, wsWhere)
        return self.RunQuery(wsQuery)

    #
    # Select() Runs a database SELECT statement.
    #		Returns True for proper SQL or False for a bad statement.
    #		Proper SQL may not find data, use table.len() to check if anything was found.
    #
    def Select(self, FieldList=None, Where=None, Order=None, parmJoin=None, parmGroup=None,
				Limit=None,
				Messages=None, debug=0):
      wsJoinTableList				= []
      wsJoinClause				= ""
      if parmJoin:
        for wsThisJoinSpec in parmJoin:
          wsJoinType				= wsThisJoinSpec[0]
          wsJoinTable				= wsThisJoinSpec[1]
          wsJoinPrimaryFieldName			= wsThisJoinSpec[2]
          wsJoinSecondaryFieldName		= wsThisJoinSpec[3]
          wsJoinTableList.append(wsJoinTable)
          if wsJoinType == LEFTOUTERJOIN:
            wsJoinPhrase				= "LEFT OUTER JOIN"
          else:
            wsJoinPhrase				= "LEFT OUTER JOIN"
          wsJoinClause				+= " %s %s ON %s.%s = %s.%s" % (
				                                wsJoinPhrase,
								wsJoinTable.tableName,
								self.tableName, wsJoinPrimaryFieldName,
								wsJoinTable.tableName, wsJoinSecondaryFieldName)
      if FieldList:
        wsFieldNameList				= []
        for wsThisFieldName in FieldList:
          (wsFieldName, wsFieldType) = self.GetFieldNameAndType(wsThisFieldName, wsJoinTableList,
				Messages=Messages,  debug=debug)
          if not wsFieldName:
            self._lastErrorMsg			= "Blank found in fields list"
            return False
          wsFieldNameList.append(wsFieldName)
        wsFields					= commastr.ListToCommaStr(wsFieldNameList)
      else:
        wsFields					= "*"
      (wsWhere, wsWhereParams)			= self.Where(Where, JoinTableList=wsJoinTableList, debug=debug)
      #
      if Order is not None:
        if isinstance(Order, str):
          Order					= [Order]
        wsOrderFieldNameList			= []
        for wsThisOrderFieldSpec in Order:
          if wsThisOrderFieldSpec[0] == '-':
            wsThisOrderFieldName			= wsThisOrderFieldSpec[1:]
            wsDescending				= True
          else:
            wsThisOrderFieldName			= wsThisOrderFieldSpec
            wsDescending				= False
          (wsFieldName, wsFieldType)		= self.GetFieldNameAndType(wsThisOrderFieldName, wsJoinTableList,
							Messages=Messages, debug=debug)
          if wsDescending:
            wsFieldName				= wsFieldName + ' DESC'
          wsOrderFieldNameList.append(wsFieldName)
        wsOrderClause				= " ORDER BY " + commastr.ListToCommaStr(wsOrderFieldNameList, QuoteNever=True)
      else:
        wsOrderClause				= ""
      #
      if parmGroup:
        wsGroupFieldNameList			= []
        for wsThisGroupFieldName in parmGroup:
          (wsFieldName, wsFieldType)		= self.GetFieldNameAndType(wsThisGroupFieldName, wsJoinTableList,
									Messages=Messages, debug=debug)
          wsGroupFieldNameList.append(wsFieldName)
        wsGroupClause				= "GROUP BY " + commastr.ListToCommaStr(wsGroupFieldNameList)
      else:
        wsGroupClause = ""
      if Limit is None:
        wsLimitClause				= ""
      else:
        wsLimitClause				= " LIMIT " + utils.Str(Limit)

      wsQuery					= "SELECT {FieldNames} FROM {TableName}{JoinClause}{WhereClause}{GroupClause}{OrderClause}{LimitClause}".format(
							FieldNames=wsFields,
							TableName=self.tableName,
							JoinClause=wsJoinClause,
							WhereClause=wsWhere,
							GroupClause=wsGroupClause,
							OrderClause=wsOrderClause,
							LimitClause=wsLimitClause
						)
      wsResult					=  self.RunDataQuery(wsQuery, wsWhereParams)
      if wsResult is None:
        return False							# self._lastErrorMsg set by RunDataQuery()
      return True

    def SelectKeyList(self, parmFieldName, Where=None, Order=None, Limit=None):
      wsList					= []
      self.Select([parmFieldName], Where=Where, Order=Order, Limit=Limit)
      for wsThisRecord in self:
        wsList.append(wsThisRecord[parmFieldName])
      return wsList

    def Update(self, parmValues, FieldList=None, Where=None):
      if Where is None:
        if self.rdbmsTDict.udi is not None:
          wsUdiFieldName			= self.rdbmsTDict.udi._name
          wsUdiValue			= parmValues[wsUdiFieldName]
          if wsUdiValue is not None:
            Where				= (wsUdiFieldName, '=', wsUdiValue)
      if Where is None:
        self._lastErrorMsg		= "Where clause required for Update funtion."
        return None							# avoid accidental "change all"
      if Where == WhereAllCode:
        wsWhere				= ""
        wsWhereParams			= tuple()
      else:
        (wsWhere, wsWhereParams)		= self.Where(Where)
      wsFieldsAndValues			= self.GetFieldsAndValues(parmValues, FieldList, OmitUdi=True)
      if wsFieldsAndValues is None:
        return None							# GetFieldsAndValues() sets self._lastErrorMsg
      (wsNotUsed, wsAssignmentsStr, wsValueParms)	= self.MakeValueAssignments(wsFieldsAndValues, SetMode=True)
      if wsAssignmentsStr is None:
        return None							# MakeValueAssignments() sets self._lastErrorMsg

      wsQuery				= "UPDATE {TableName} SET {ValueAssignments}{WhereClause}".format(
						TableName=self.tableName,
						ValueAssignments=wsAssignmentsStr,
						WhereClause=wsWhere
					)
      wsResult				= self.RunQuery(wsQuery, wsValueParms+wsWhereParams)
      return wsResult

    def UpdateCommonFields(self, parmSource, Where, Prefix=""):
        if not Where:
          self._lastErrorMsg		= "Where clause required for UpdateCommonFields funtion."
          return None							# avoid accidental "change all"
        if Where == WhereAllCode:
          wsWhere				= ""
        else:
          wsWhere				= self.Where(Where)
        wsFieldNameList			= []
        wsFieldValueList			= []
        for (wsFieldName, wsFieldValue) in list(parmSource.items()):
          wsLocalFieldName		= Prefix + wsFieldName
          if wsLocalFieldName in self.rdbmsTDict.elements:
            wsFieldNameList.append(wsLocalFieldName)
            if not wsFieldValue:
              wsFieldValue		= ''				# convert None to string
            wsFieldValueList.append(wsFieldValue)
        if len(wsFieldNameList) < 0:
          self._lastErrorMsg		= "No common fields found for UpdateCommonFields funtion."
          return None
        wsFieldsAndValues			= self.GetFieldsAndValues(wsFieldValueList, wsFieldNameList)
        if not wsFieldsAndValues:
          return None							# GetFieldsAndValues() sets self._lastErrorMsg
        wsValueAssignments		= self.MakeValueAssignments(wsFieldsAndValues)
        if not wsValueAssignments:
          return None							# MakeValueAssignments() sets self._lastErrorMsg

        wsQuery				= "UPDATE %s SET %s %s" % (self.tableName, wsValueAssignments, wsWhere)
        wsResult				= self.RunQuery(wsQuery)
        return wsResult

    def GetFieldNameAction(self, parmFieldName):
        if parmFieldName[0] == "+":
          return ('sum', parmFieldName[1:])
        else:
          return ('', parmFieldName)

    #
    # GetFieldNameAndType()
    #
    def GetFieldNameAndType(self, parmFieldName, JoinTableList=[], Messages=None, debug=0):
      wsExpandedFieldName			= ""
      wsFieldType				= ""
      if isinstance(parmFieldName, type([])):
        if len(parmFieldName) == 3:
          wsFieldInfo1			= self.GetOneFieldNameTypeAndAction(
						parmFieldName[0], JoinTableList, Messages, debug=0)
          wsFieldInfo2			= self.GetOneFieldNameTypeAndAction(
						parmFieldName[2], JoinTableList, Messages, debug=0)
          wsOperator			= parmFieldName[1]
          if wsFieldInfo1[1] != wsFieldInfo2[1]:
            self._lastErrorMsg		= "Invalid expression %s type mismatch %s != %s" % (
						repr(parmFieldName), wsFieldInfo1[1], wsFieldInfo2[1])
            if Messages:
              Messages.AppendCriticalMessage(self._lastErrorMsg)
          wsExpandedFieldName		= wsFieldInfo1[0] + wsOperator + wsFieldInfo2[0]
          wsFieldType			= wsFieldInfo1[1]
          wsActionRefname			= wsFieldInfo1[2]
          if not wsActionRefname:
            wsActionRefname		= wsFieldInfo2[2]
        else:
          self._lastErrorMsg		= "Invalid number of parameters in expression %s" % (
						repr(parmFieldName))
          if Messages:
            Messages.AppendCriticalMessage(self._lastErrorMsg)
      else:
        (wsExpandedFieldName, wsFieldType, wsActionRefname) = self.GetOneFieldNameTypeAndAction(
				parmFieldName, JoinTableList, Messages, debug=0)
      if wsActionRefname:
        wsExpandedFieldName		= "%s(%s)" % (wsActionRefname, wsExpandedFieldName)
      return (wsExpandedFieldName, wsFieldType)

    def GetOneFieldNameTypeAndAction(self, parmFieldName, JoinTableList=[], Messages=None, debug=0):
      # Creates FQN of field (table.field)
      wsTableName				= ""
      wsFieldName				= ""
      wsFieldType				= ""
      wsFieldSpec				= None
      wsActionRefname			= ""
      if isinstance(parmFieldName, type (())):
        # parmFieldName is (tableobject, fieldnamestring)
        wsFieldTable			= parmFieldName[0]
        wsTableName			= wsFieldTable.tableName
        (wsActionRefname, wsFieldName)	= self.GetFieldNameAction(parmFieldName[1])
        if debug > 0:
          print("Get Field %s.%s from '%s'" % (wsTableName, wsFieldName, repr(parmFieldName)))
        wsFieldSpec			= wsFieldTable.rdbmsTDict[wsFieldName]
      else:
        (wsActionRefname, wsFieldName)	= self.GetFieldNameAction(parmFieldName)
        if wsFieldName in self.rdbmsTDict.elements:
          wsTableName			= self.tableName
          wsFieldSpec			= self.rdbmsTDict.elements[wsFieldName]
        else:
          for wsThisTable in JoinTableList:
            if wsFieldName in wsThisTable.rdbmsTDict.elements:
              wsTableName			= wsThisTable.tableName
              wsFieldSpec			= wsThisTable.rdbmsTDict.elements[wsFieldName]
      wsExpandedFieldName			= "%s.%s" % (wsTableName, wsFieldName)

      if wsFieldSpec:
        return (wsExpandedFieldName, wsFieldSpec.physicalType, wsActionRefname)
      else:
        self._lastErrorMsg = "Invalid field %s.%s" % (wsTableName, wsFieldName)
        if Messages:
          Messages.AddUserCriticalMessage(self._lastErrorMsg)
        return (None, None, None)

    def Where(self, parmWhereList, JoinTableList=[], debug=0):
        wsWhere				= ""
        wsWhereParams			= []
        if not parmWhereList:
          return ("", None)
        if not self.rdbmsTDict:
           return ("", None)
        if not isinstance(parmWhereList, type([])):
          parmWhereList			= [parmWhereList]
        for wsWhereSpec in parmWhereList:
          if not isinstance(wsWhereSpec, type(())):
            return (None, None)
          if len(wsWhereSpec) < 3:
            return (None, None)
          wsWhereData			= wsWhereSpec[2]
          (wsFieldName, wsFieldType)	= self.GetFieldNameAndType(wsWhereSpec[0], JoinTableList, debug=0)
          if wsWhere:
            if len(wsWhereSpec) > 3:
              wsConjunction 		= wsWhereSpec[3]
            else:
              wsConjunction		= "AND"
            wsWhere			+= " " + wsConjunction + " "
          if wsWhereSpec[1] in ['is', 'is not']:
            # the operand (wsWhereSpec[2] should be 'null' or None, but I'm not checking
            wsWhere			+= "%s %s %s" % (wsFieldName, wsWhereSpec[1], 'null')
          else:
            wsWhere			+= "%s %s " % (wsFieldName, wsWhereSpec[1])
            if isinstance(wsWhereData, Reference):
              wsWhere			+= wsWhereData.Expression(self, wsWhereParams)
            else:
              # The third parameter is a literal, so let the dbms libary quote the value
              wsWhere			+= self.db.paramcode
              wsWhereParams.append(wsWhereData)
        if wsWhere:
          wsWhere				= " WHERE " + wsWhere
        return (wsWhere, tuple(wsWhereParams))

#
# Lookup creates and executes a query that is expected to
# return exactly one record.  It is most often used to verify
# referential integrity or for code translation.
#
    def Lookup(self, parmFld, parmValue, FieldList=None):
      wsResult				= self.Select(FieldList=FieldList, Where=[(parmFld, '=', parmValue)])
      if not wsResult:
        return False
      if len(self._tuples) != 1:
        return False
      return True

    def LookupTuple(self, parmFld, parmValue, FieldList=None):
      if self.Lookup(parmFld, parmValue, FieldList=FieldList):
        wsTuple				= datastore.TupleObject(IsCaseSensitive=self._isCaseSensitive)
        for (wsKey, wsValue) in list(self._tuples[0].items()):
          wsTuple[wsKey]			= wsValue
        return wsTuple
      else:
        return None

    def Lookup2(self, Where=None, FieldList=None):
      wsResult				= self.Select(FieldList=FieldList, Where=Where)
      if not wsResult:
        return False
      if len(self._tuples) != 1:
        return False
      return True

    def Lookup2Tuple(self, Where=None, FieldList=None):
      if self.Lookup2(Where=Where, FieldList=FieldList):
        wsTuple				= datastore.TupleObject(IsCaseSensitive=self._isCaseSensitive)
        for (wsKey, wsValue) in list(self._tuples[0].items()):
          wsTuple[wsKey]			= wsValue
        return wsTuple
      else:
        return None

#
# RdbmsConnector() is the  database object.
#
#

class RdbmsConnector(object):
  __slots__ = ('exeController', 'db', 'dbPath', 'dbType', 'tables', 'hostName', 'dbName', 'refname', 'userName', 'paramcode', 'paramstyle', 'password', 'debug')
  def __init__(self, Refname="DB", Path=None, DbType=DbTypeUnknown, Host=None, Db=None, User=None, Password=None, Debug=0, ExeController=None):
    self.exeController				= ExeController
    self.db			      			= None
    self.dbPath						= Path
    self.dbType						= DbType
    self.tables						= tupledata.TupleData()
    self.hostName					= Host
    self.dbName						= Db
    self.userName					= User
    self.password					= Password
    self.paramstyle					= None
    self.paramcode					= None
    self.refname					= Refname
    self.debug						= Debug
    self.OpenDb()

  def BuildTableListSql(self, parmQuery):
    wsQuery				     		= RdbmsTable(Db=self)
    wsTables						= wsQuery.RunDataQuery(parmQuery)
    if self.debug > 0:
      print(("Tables: " + repr(wsTables)))
    if wsTables is not None:
      if self.debug > 0:
        print("create self.tables")
      for wsThisTable in wsTables:
        wsTableName					= wsThisTable._GetByIx(0)	# ['Name']
        self.tables[wsTableName]			= None
    else:
      # No table names found. Either a new database or an error
      self.db						= None			# disconnect since something is wrong
      if self.debug > 0:
        print(wsQuery._lastQuery)
        print(wsQuery._lastErrorMsg)
        PrintError("Unable to get table list")
      return False
    return True

  def Connect(self, Host=None, Db=None, User=None, Passwordd=None, Path=None):
    if Host is not None:
      self.hostName					= Host
    if Db is not None:
       self.dbName					= Db
    if User is not None:
      self.userName					= User
    if Password is not None:
      self.password					= Password
    if Path is not None:
      self.dbPath					= Path
    return self.OpenDb()

  def OpenDb(self):
    self.tables						= tupledata.TupleData()	# clear since we are reconnecting
    if self.debug > 0:
      print(("Connect(%s, %s, %s, %s)" % (
			repr(self.hostName), repr(self.dbName),
			repr(self.userName), repr(self.password) )))
    try:
      self.DoConnect()
    except:
      self.db						= None
      if self.exeController is not None:
        self.exeController.errs.AddTraceback()
      else:
        raise

    if self.db is None:
      if self.debug > 0:
        PrintError("Connect")
      return False

    if self.debug > 0:
      print("Connect successful")

    if self.paramstyle == ParamStyleFormat:
      self.paramcode					= '%s'
    elif self.paramstyle == ParamStyleQmark:
      self.paramcode					= '?'
    else:
      raise Exception("Undefined paramstyle '%s' for database %s." % (self.paramstyle, self.dbName))

    self.BuildTableList()

  def CloseDb(self):
    self.db.close()
    self.db						= None

  def CreateTable(self, TDict=None, TableName=None, Debug=0):
    wsTable						= RdbmsTable(Db=self, Debug=Debug)
    wsResult						= wsTable.CreateTableFromTDict(TDict, TableName=TableName)
    return wsTable						# return table to inspect errors or use

  def DropTable(self, parmTableName):
    wsTable						= self.OpenTable(parmTableName)
    wsTable.Drop()
    del self.tables[parmTableName]

  def IsOpen(self):
    if self.db is None:
      return False
    else:
      return True

  def OpenTable(self, parmTableName, ModelTDict=None, Debug=0):
    if not self.db:
      return None
    if parmTableName not in self.tables:
      if self.debug > 0:
        print(("Table not in database: " + parmTableName))
      return None
    if self.tables[parmTableName] is None:
      wsTable						= RdbmsTable(TableName=parmTableName,
								Db=self,
								ModelTDict=ModelTDict,
								Debug=Debug)
      if self.debug > 0:
        print(("Table opened: " + parmTableName))
      wsTable._debug					= self.debug
      self.tables[parmTableName]			= wsTable
      return wsTable
    else:
      if self.debug > 0:
        print(("Table already opened: " + parmTableName))
      return self.tables[parmTableName]

  def Query(self, parmSql):
    if self.db:
      wsQuery						= RdbmsTable(Db=self)
      wsQuery.RunDataQuery(parmSql)
    else:
      wsQuery						= None		# Connect() failed or not called
    return wsQuery

class RdbmsMySql(RdbmsConnector):
  def __init__(self, *args, **kwargs):
    kwargs['DbType']					= DbTypeMySql
    super(RdbmsMySql, self).__init__(*args, **kwargs)

  def DoConnect(self):
    self.db						= MySQLdb.Connect(host=self.hostName, db=self.dbName,
								user=self.userName, passwd=self.password,
								use_unicode=True,
								charset='utf8')
    self.paramstyle					= MySQLdb.paramstyle

  def BuildTableList(self):
    return self.BuildTableListSql("SHOW TABLES")

  def GetLastQuery(self, Table, Query):
    return Table.cursor._last_executed

  def TranslateFieldType(self, Fld=None, Table=None):
    wsMySqlFieldTypeNumber				= Fld[1]
    wsElementPhysicalType				= None
    for wsThisMySqlType in MySqlFieldTypes:
      if wsThisMySqlType.typeNumber == wsMySqlFieldTypeNumber:
        wsElementPhysicalType				= wsThisMySqlType.PhysicalType
        break
    if wsElementPhysicalType is None:
      if self.exeController is not None:
        self.exeController.errs.AddUserCriticalMessage("Unexpected MySql field type '%s' for %s.%s." % (
								wsMySqlFieldTypeNumber, Table.tableName, Fld[0]))
    return wsElementPhysicalType

  def BuildTDictForTable(self, Table):
    # with show full fields:  Field | Type | Collation | Null | Key | Default | Extra | Privileges | Comment |
    wsQuery					= "SHOW FULL FIELDS FROM " + Table.tableName
    wsShowFields				= Table.RunDataQuery(wsQuery)
    if wsShowFields is None:
      return None									# no fields, table not created yet ?

    wsTDict					= tupledict.TupleDict(
							Name=Table.tableName,
							ExeController=self.exeController)
    wsTableUdiFound				= False
    for wsThisFieldSpec in wsShowFields:
      #print "FFF", wsThisFieldSpec
      wsElementName				= wsThisFieldSpec['Field']
      wsMySqlMaxLength				= None
      wsDbmsFieldType				= wsThisFieldSpec['Type']
      wsDbmsDefaultValue			= wsThisFieldSpec['Default']
      wsDefaultValue				= utils.Str(wsDbmsDefaultValue)	# Need to deal with Null
      if wsDbmsFieldType[:3] == "int":
        wsElementPhysicalType			= ertypes.Core_IntegerTypeCode
      else:
        wsElementPhysicalType			= ertypes.Core_StringTypeCode
        if wsDbmsFieldType[:5] == "char(":
          wsMySqlMaxLength			= utils.Int(wsDbmsFieldType[5:-1])
        elif wsDbmsFieldType[:8] == "varchar(":
          wsMySqlMaxLength			= utils.Int(wsDbmsFieldType[8:-1])
      wsCollation				= wsThisFieldSpec['Collation']
      if (wsCollation is not None) and (wsCollation[:4] == 'utf8'):
        wsEncoding				= ertypes.Encoding_Utf8
      else:
        wsEncoding				= ertypes.Encoding_Ascii
      #
      if (wsCollation is not None) and (wsCollation[-3:] == 'bin'):
        wsIsCaseSensitive			= True
      else:
        wsIsCaseSensitive			= False
      #
      wsElement					= wsTDict.AddScalarElement(wsElementName,
							Encoding=wsEncoding,
							IsCaseSensitive=wsIsCaseSensitive,
							PhysicalType=wsElementPhysicalType,
							MaxLength=wsMySqlMaxLength)
      wsElement.AssignDefaultValue(wsDefaultValue)
      wsElement.SaveDbmsSpecs(
							DbmsFieldType	= wsDbmsFieldType,
							Null		= wsThisFieldSpec['Null'],
							Key		= wsThisFieldSpec['Key'],
							DefaultValue	= wsDbmsDefaultValue,
							Extra		= wsThisFieldSpec['Extra']
							)
      if wsElement.dbmsExtra == "auto_increment":
        wsElement.isAutoIncrement		= True
      if wsElement.dbmsNull == "YES":
        wsElement.isBlankAllowed		= True
      else:
        wsElement.isBlankAllowed		= False
      if wsElement.dbmsKey == "PRI":
        if wsTableUdiFound:
          self.exeController.errs.AddUserCriticalMessage("Duplicate UDI %s in %s." % (wsElement.name, wsTableName))
        wsTableUdiFound				= True
        wsElement.isIndex			= True
        wsElement.ConfigureAsUdiRole()
      elif wsElement.dbmsKey == "UNI":
        wsElement.isIndex			= True
        wsElement.isUnique			= True
      elif wsElement.dbmsKey == "MUL":
        wsElement.isIndex			= True
      elif wsElement.dbmsKey != "":
        self.exeController.errs.AddUserCriticalMessage("Unexpected key type %s for %s in %s." % (
							wsMySqlSchemaKeyType, wsElement.name, wsTableName))
    return wsTDict

  # RdbmsMySql
  def MakeColumnDefFromTDictElement(self, parmTDictElement):
    if parmTDictElement.physicalType == ertypes.Core_IntegerTypeCode:
      wsColumnType				= 'int'
    else:
      wsMaxLen					= parmTDictElement.maxLength
      if wsMaxLen < 1:
        wsMaxLen				= 10
      if wsMaxLen <= 10:
        wsTypeName				= 'CHAR'
      else:
        wsTypeName				= 'VARCHAR'
      wsColumnType				= '%s(%d)' % (wsTypeName, wsMaxLen)
      if parmTDictElement.encoding == ertypes.Encoding_Utf8:
        wsColumnType				+= " CHARACTER SET 'utf8'"
        if parmTDictElement.isCaseSensitive:
          wsColumnType				+= " COLLATE 'utf8_bin'"
        else:
          wsColumnType				+= " COLLATE 'utf8_general_ci'"
      else:
        wsColumnType				+= " CHARACTER SET 'latin1'"
        if parmTDictElement.isCaseSensitive:
          wsColumnType				+= " COLLATE 'latin1_bin'"
        else:
          wsColumnType				+= " COLLATE 'latin1_swedish_ci'"
    if parmTDictElement.roleType == ertypes.Core_UdiRoleCode:
      wsColumnType				+= ' PRIMARY KEY'
      if parmTDictElement.isAutoIncrement:
        wsColumnType				+= ' AUTO_INCREMENT'
    if not parmTDictElement.isBlankAllowed:
      wsColumnType				+= ' NOT NULL'
    wsColumnDef					= parmTDictElement.dbmsFieldName + ' ' + wsColumnType
    return wsColumnDef
#
# RdbmsSqLite
#
class RdbmsSqLite(RdbmsConnector):
  def __init__(self, **kwargs):
    super(RdbmsSqLite, self).__init__(DbType=DbTypeSqLite, **kwargs)

  def DoConnect(self):
    self.db						= sqlite3.connect(self.dbPath)
    self.db.text_factory				= sqlite3.OptimizedUnicode
    self.paramstyle					= sqlite3.paramstyle

  def BuildTableList(self):
    self.db.text_factory = sqlite3.OptimizedUnicode
    return self.BuildTableListSql("select name from sqlite_master where type = 'table';")

  def GetLastQuery(self, Table, Query):
    return Query

  def TranslateFieldType(self, Fld=None, Table=None):
    # SqLite seems to provide None for everything in parmFld but name. Probably because its weakly typed so
    # you have to be ready to deal with any kind of data.
    return ertypes.Core_StringTypeCode

  def BuildTDictForTable(self, Table):
    wsQuery					= "PRAGMA table_info(%s);" % (Table.tableName)
    wsShowFields				= Table.RunDataQuery(wsQuery)
    if wsShowFields is None:
      return None									# no fields, table not created yet ?

    wsTDict					= tupledict.TupleDict(
							Name=Table.tableName,
							ExeController=self.exeController)
    wsTableUdiFound				= False
    for wsThisFieldSpec in wsShowFields:
      # SqLite seems to leave the case of field type as entered so you can't count on them
      # being upper case, lower case or even consistent.
      # Need to get case sensitivity and character set. All SqLite fields are utf8.
      # Need to do the show create string and parse that to find collation for
      # case sensitivity.

      wsFieldId					= wsThisFieldSpec['cid']		# a sequential number
      wsElementName				= wsThisFieldSpec['name']
      wsDbmsFieldType				= utils.Upper(wsThisFieldSpec['type'])
      wsDbmsNotNull				= wsThisFieldSpec['notnull']
      wsDefaultValue				= wsThisFieldSpec['dflt_value']
      wsIsPrimaryKey				= wsThisFieldSpec['pk']
      if wsDbmsFieldType[:3] == "INT":
        wsElementPhysicalType			= ertypes.Core_IntegerTypeCode
      else:
        wsElementPhysicalType			= ertypes.Core_StringTypeCode
      #
      wsElement					= wsTDict.AddScalarElement(wsElementName,
							PhysicalType=wsElementPhysicalType)
      if wsIsPrimaryKey == 1:
        wsElement.ConfigureAsUdiRole()
      if wsDbmsNotNull == 1:
        wsElement.ConfigureAsNotBlank()
      if wsDefaultValue is not None:
        wsElement.AssignDefaultValue(wsDefaultValue)
      wsElement.SaveDbmsSpecs(
							DbmsFieldType	= wsDbmsFieldType,
							Null		= wsDbmsNotNull,
							Key		= None,
							DefaultValue	= wsDefaultValue,
							Extra		= None,
							Privileges	= None)
    return wsTDict

  # RdbmsSqLite
  def MakeColumnDefFromTDictElement(self, parmTDictElement):
    if parmTDictElement.physicalType == ertypes.Core_IntegerTypeCode:
      wsColumnType				= 'INTEGER'
    else:
      wsColumnType				= 'TEXT'
      if parmTDictElement.isCaseSensitive:
        wsColumnType				+= ' COLLATE BINARY'
      else:
        wsColumnType				+= ' COLLATE NOCASE'
    if parmTDictElement.roleType == ertypes.Core_UdiRoleCode:
      wsColumnType				+= ' PRIMARY KEY'
      if parmTDictElement.isAutoIncrement:
        wsColumnType				+= ' AUTOINCREMENT'
    else:
      if parmTDictElement.isUnique:
        wsColumnType				+= ' UNIQUE'
    if not parmTDictElement.isBlankAllowed:
      wsColumnType				+= ' NOT NULL'
    wsColumnDef					= parmTDictElement.dbmsFieldName + ' ' + wsColumnType
    return wsColumnDef

class RdbmsFiles(RdbmsConnector):
  """
    RdbmsFiles is a Rdbms database where the tables are
    filesystem directories and the data is stored in one or more individual
    files per row.

    The scalar data for each row is stored in a single files which can be in
    JSON, XML or INF format. Blob attributes are stored as individual files
    with an appropriate file name extension that can be directly accessed
    by a webserver.

  """

  def __init__(self, **kwargs):
    self.multiTable					= kwargs.pop('MultiTable', False)
    super(RdbmsFiles, self).__init__(DbType=DbTypeFiles, **kwargs)

  def DoConnect(self):
    self.db						= self
    self.paramstyle					= ParamStyleFormat

  def BuildTableList(self):
    if self.multiTable:
      # Not implemented. This is a do-nothing action
      return []
    else:
      return [os.path.basename(self.dbPath)]

def BasicTest(parmArgs):
        wsDebug = parmArgs.data['d']
        wsDb = Rdbms(parmArgs.data['h'], parmArgs.data['b'],
		parmArgs.data['u'], parmArgs.data['p'], debug=wsDebug)
        wsCmd = parmArgs.data['c']
        if wsCmd == "d":
          wsDb.DropTable(parmArgs.data['t'])
	# wsTable = wsDb.CreateTable("junk", ["id char(5)", "name char(30)"])
	# wsTable.Insert(["1", "Joe"])
	# wsTable.Insert(["2", "Fred"])
        elif wsCmd == "l":
          wsTable = wsDb.OpenTable(parmArgs.data['t'])
          wsTable.PrintList()
        else:
          print("Unknown test command '" + repr(wsCmd) + "'")
#
# LoadTables() is a powerful (and somewhat dangerous) database creator
# and loader.  The source file is a comma delimited file where the
# first charater is a record code.  Each line can be either meta data
# or actual data.  One file can contain multiple table definitions and
# contents.
#
def LoadTables(parmCmdArgs):
# MS Excel provides inconsistent treatment of trailing blank fiels
# when exporting CSV files.  ListStripTrailingBlanks() to minimize errors.
  from . import bzTextFile
  if "d" in parmCmdArgs.switches: wsDebug = int(parmCmdArgs.data['d'])
  else: wsDebug = 0
  wsSource = bzTextFile.open(parmCmdArgs.data['l'], "r")
  if not wsSource:
    print('Unable to source text file -- nothing loaded')
    sys.exit(-1)
  if "s" in parmCmdArgs.switches:
    wsFieldList = wsSource.readcma()
    wsFieldList = utils.ListStripTrailingBlanks(wsFieldList)
    wsFieldListLen = len(wsFieldList)
    wsDb = Rdbms(host=parmCmdArgs.data['h'], db=parmCmdArgs.data['b'],
			user=parmCmdArgs.data['u'],
			passwd=parmCmdArgs.data['p'], debug=wsDebug)
    print(repr(wsDb.tables))
    if (not wsDb) or (not wsDb.db):
      print('Unable to open database -- nothing loaded')
      sys.exit(-1)
    wsTable = wsDb.OpenTable(parmCmdArgs.data['t'], debug=wsDebug)
    if not wsTable:
      print('Unable to open database table -- nothing loaded')
      sys.exit(-1)
  else:
    # expect database info in file
    wsSource.recCodeFlag = True
    wsDb = None
    wsTable = None
    wsFieldList = None
    wsFieldListLen = 0

  while not wsSource.EOF:
    wsRec = wsSource.readcma()
    if not wsSource.recCodeFlag: wsSource.recCode = "D"
    print("%s: %s" % (wsSource.recCode, wsRec))
    if wsSource.recCode == "L":			# login
      print("Logging in '%s', '%s', '%s', '%s' " % (
			wsRec[0], wsRec[1], wsRec[2], wsRec[3]))
      wsDb = Rdbms(wsRec[0], wsRec[1], wsRec[2], wsRec[3])
    elif wsSource.recCode == "C":		# table specs to create
      print("Create Table")
      if not wsTable:
        print("Table creation record type '" \
			+ wsSource.recCode + "' at record " \
			+ repr(wsSource.recno) + " found before T record")
        sys.exit(1)
      wsTable.Drop()
      if not wsTable.Create(wsRec):
        print("Table creation error for '" + wsTable.tableName \
			+ "' at line " + repr(wsSource.recno))
        sys.exit(1)
    elif wsSource.recCode == "T":		# table to open
      print("Opening Table '%s'" % (wsRec[0]))
      if not wsDb:
        wsTable = None
        print("Table processing record type '" \
			+ wsSource.recCode + "' at record " \
			+ repr(wsSource.recno) + " found before L record")
        sys.exit(1)
      wsTable = wsDb.OpenTable(wsRec[0])
      wsFieldList = None
      wsFieldListLen = 0
    elif wsSource.recCode == "F":		# field order for Ds
      print("Field List")
      wsFieldList = utils.ListStripTrailingBlanks(wsRec)
      wsFieldListLen = len(wsFieldList)
    elif wsSource.recCode == "D":		# data to insert
      print("Data Record")
      wsRec = utils.ListStripTrailingBlanks(wsRec, wsFieldListLen)
      if not wsTable.Insert(wsRec, wsFieldList):
        print("Table insert error for '" + wsTable.tableName \
			+ "' at line " + repr(wsSource.recno))
        sys.exit(1)
    elif wsSource.recCode == "X":
      print("X Record")
      wsSource.recCodeFlag = False
    else:
      print("Unknown record type '" + wsSource.recCode \
			+ "' for record " + repr(wsSource.recno))

if __name__ == "__main__":
	from . import bzCmdArgs

	# Command line switches
	#	-c cmd		test mode
	#	-d lvl		debug mode
	#	-i filename	import from comma delimited file
	#	-l filename	load table
	#	-s 		filename is a simple comma delimited file
	#	-h host
	#	-b db
	#	-u user
	#	-p passwd
	#	-t table
	wsArgs = bzCmdArgs.bzCmdArgs("bcdhptul")
	if "c" in wsArgs.switches:
	    BasicTest(wsArgs.parameters['c'])
	    sys.exit(0)
	elif "l" in wsArgs.switches:
            print("Loading '%s'" % (wsArgs.parameters['l']))
            LoadTables(wsArgs)
            sys.exit(0)
	else:
	    print("usage xxxx")
