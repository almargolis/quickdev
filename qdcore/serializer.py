"""
Serializer provides common classes and functions for
handling serialized data such as ini, xml, json, etc.

Specific handling of each type is in specifc modules.

Common file formats are also supported by standard python
modules. The advantage of these CommerceNode modules is
support for error handling and convenience idioms.
"""

from . import textfile
from . import tupledata


"""
#!/usr/bin/python
#
# DEPRECATED - move to separate files per type.
# maybe keep this for common functions or base class if needed.
#
#############################################
#
#  bafSerializer - A family of libraries to load / unload
#			objects as XML, JSON, CSV, etc.
#
#  3/11/2007:  Initial Release.

#
# Don't import bzCompositions because it is the main user of this module, causing circular references
# Don't import bafEr because it descends from bzCompositions
# LoadXmlText() needs to create compositions. It just asssumes the necessary factory functions exist,
#		protected by try/except. Also uses __class__ to create a new composition -- there
#		ought to be a better way of doing that.
#
#
# This module is essential for site bootstraping so it should have
# the minimal number of dependencies and none outside the development
# directory.
#

from . import bafErTypes
from . import bafNv
from . import bafDataStore

from . import bzTextFile
from . import bzUtil

XmlATTRIBUTENAMECHARS		= bzUtil.LETTERS + bzUtil.NUMBERS
XmlWHITESPACECHARS		= "\x20\x09\x0a\x0d"				# Space / tab / LF / CR
XmlAMP				= ("&", "&amp;")				# ampersand
XmlGT				= (">", "&gt;")					# > greater than
XmlLT				= ("<", "&lt;")					# < less than
XmlQUOT				= ('"', "&quot;")				# quote
XmlAPOS				= ("'", "&apos;")				# apostraphe

# This is a list of all the XML entities.
# XmlAmp is first so we don't inadvertently encode the ampersands of other substituted entities.
# When decoding XML, traverse the list in reverse order in case any of the actual ampersands in
# the text happen to be in a string that looks like an entity.
XmlEntities			= (XmlAMP, XmlGT, XmlLT, XmlQUOT, XmlAPOS)
XmlEntitiesUnicode		= []
for wsThis in XmlEntities:
  wsEntity			= (str(wsThis[0]), str(wsThis[1]))
  XmlEntitiesUnicode.append(wsEntity)

def GetContainerPathStr(parmContainer):
  wsContainerTree		= ""
  wsContainerTreeObject		= parmContainer
  wsDepth			= 0
  while wsContainerTreeObject is not None:
    wsContainerTree		+= repr(wsContainerTreeObject._name) + " > "
    wsContainerTreeObject	= wsContainerTreeObject._parent
    wsDepth			+= 1
    if wsDepth > 10:
      wsContainerTree		+= ' > ...'
      break
  return wsContainerTree

def SubstAll(parmText, parmTarget, parmReplacement):
  wsTargetIx			= parmText.find(parmTarget)
  while wsTargetIx >= 0:
    parmText			= parmText[:wsTargetIx] + parmReplacement + parmText[wsTargetIx+len(parmTarget):]
    wsNextIx			= wsTargetIx + len(parmReplacement)
    wsTargetIx			= parmText.find(parmTarget, wsNextIx)
  return parmText

def AsXmlQuoted(parmText):
  for wsThisEntity in XmlEntities:
    parmText			= SubstAll(parmText, wsThisEntity[0], wsThisEntity[1])
  return parmText

def AsXmlUnquoted(parmText):
  if parmText == "":
    return parmText
  for wsThisEntity in XmlEntities[::-1]:
    parmText			= SubstAll(parmText, wsThisEntity[1], wsThisEntity[0])
  return parmText

class DataClassifier(object):
  def __init__(self, Data=None):
    if Data is not None:
      self.Classify(Data)

  def __repr__(self):
    if self.isClassified:
      wsStr			= '<'
    else:
      wsStr			= '< NotClassified'
    if self.isIterable:
      wsStr			+= ' Iter'
    if self.isMapping:
      wsStr			+= ' Map'
    if self.isScalar:
      wsStr			+= ' Scalar'
    wsStr			+= ' >'
    return wsStr

  def Classify(self, parmData):
    self.isAnonymous		= False
    self.isScalar		= False
    self.isClassified		= True
    self.isIterable		= False
    self.isMapping		= False
    self.tDict			= None
    if isinstance(parmData, bafDataStore.bafDataStoreObject):
      self.isIterable		= True
      self.isAnonymous		= True
      return
    if isinstance(parmData, (bafDataStore.bafTupleObject, dict)):
      self.isMapping		= True
      return
    if hasattr(parmData, '_tdict'):
      self.tDict		= parmData._tdict
      return
    if type(parmData) in (type(""), type(1), type(1)):
      self.isScalar		= True
      return
    self.isClassified		= False

def AsXmlText(parmData,
			EntityName=None,
			IsHtml=False,
			NoUnclassified=False):
    if IsHtml:
      wsLT			= '&lt;'
      wsGT			= '&gt;'
    else:
      wsLT			= '<'
      wsGT			= '>'
    wsXml			= ""
    wsXmlAttributes		= []
    wsClassifier		= DataClassifier(parmData)
    if hasattr(parmData, 'attributes'):
      if hasattr(parmData.attributes, 'items'):
        for (wsDataAttributeKey, wsDataAttributeValue) in list(parmData.attributes.items()):
          wsXmlAttributes.append((wsDataAttributeKey, wsDataAttributeValue))
    #
    # XML does not explicitly identify arrays as an element, so an array does not have
    # a tag for itself. It is anonymous.  Instead write a series of
    # identically named records.  Use IX attribute to resolve
    # ambiguity xxxxx empty and single items are a problem.
    #
    if EntityName is None:
      wsEntityName		= 'Entity'
      if hasattr(parmData, '_name'):
        wsEntityName		= parmData._name
    else:
      wsEntityName		= EntityName
    if not wsClassifier.isAnonymous:
      #
      # Write the opening tag, including attributes
      #
      wsXml			+= "%s%s" % (wsLT, wsEntityName)
      for wsThisAttribute in wsXmlAttributes:
        wsXml			+= ' %s="%s"' % wsThisAttribute
      wsXml			+= wsGT
    #
    # Write the data
    #
    if wsClassifier.isMapping:
      for (wsChildName, wsChildData) in list(parmData.items()):
        if wsClassifier.isAnonymous:
          wsChildName		= parmEntityName
        wsXml			+= AsXmlText(wsChildData, EntityName=wsChildName, IsHtml=IsHtml)
    elif wsClassifier.isIterable:
      for wsChildEntity in parmData:
        wsXml			+= AsXmlText(wsChildEntity, IsHtml=IsHtml)
    elif wsClassifier.tDict is not None:
      wsTdict			= parmData._baf_tdict
      for wsThisElement in wsClassifier.tDict.ElementsByName():
        wsChildName		= wsThisElement.name
        wsChildData		= getattr(parmData, wsChildName)
        wsXml			+= AsXmlText(wsChildData, EntityName=wsChildName, IsHtml=IsHtml)
    else:
      # This should be a simple, atomic data type but may catch unclassified objects
      wsData			= bzUtil.Str(parmData)
      wsXml			+= AsXmlQuoted(wsData)
    if not wsClassifier.isAnonymous:
      #
      # Write the closing tag
      #
      wsXml			+= "%s/%s%s" % (wsLT, wsEntityName, wsGT)
    return wsXml

#
#
#

def PrintTree(parmName, parmValue, Container=None, Level=0, TabWidth=5):
  try:
    wsContainerItems = list(parmValue.items())
    try:
      wsDisplayValue = parmValue.QuickInfo()
    except:
      wsDisplayValue = ''
    if not wsDisplayValue: wsDisplayValue = ">>>>>>"
    wsIsContainer = True
  except:
    wsContainerItems = None
    wsDisplayValue = repr(parmValue)
    wsIsContainer = False
  wsType = bafErTypes.GetPythonClassAsStr(parmValue)				# This really get the python object class

  wsErdText = "no dtd"
  wsErd = None
  try:
    wsErd = parmValue.dtd
  except:
    try:
      wsContainerErd = Container.dtd
    except:
      wsContainerErd = None
      wsErdText = "no container dtd"
    if wsContainerErd is not None:
      if parmName in wsContainerErd:
        wsErd = wsContainerErd[parmName]
      else:
        "no dtd in container"
  if (wsErd is not None) and (wsDataTypes is not None):
    wsErdText			= ""
    if wsErd._tdict is not None:
      if wsErd._tdict.exeController is not None:
        wsDataTypes		= wsErd._tdict.exeController.GetCodeObject(bafErTypes.ErdDataTypesName)
        wsErdText		= wsDataTypes.LookupCodeName(wsErd.physicalType)
    if wsErdText == "":
      wsErdText			= repr(wsErd.physicalType)

  print("%s%s: %s [%s] [%s]" % (bzUtil.Repl(" ", Level*TabWidth),
				parmName, wsDisplayValue, wsType, wsErdText))
  if wsIsContainer:
    for (wsItemName, wsItemValue) in wsContainerItems:
      PrintTree(wsItemName, wsItemValue,
				Container=parmValue,  Level=Level+1, TabWidth=TabWidth)

class bzXmlTag(object):
  __slots__ = ('name', 'attributes', 'lastParseErr', 'lastParseErrLoc', 'openIx', 'closeIx', 'EOF',
			'isCommentTag', 'isCloseTag', 'isOpenTag', 'isXmlDeclarationTag')

  def __init__(self, parmXmlText, parmIx):
    self.name					= ""
    self.attributes				= bafNv.bafNvTuple()
    self.lastParseErr				= 0
    self.lastParseErrLoc			= 0
    self.openIx					= -1
    self.closeIx				= -1
    self.EOF					= False
    self.isCloseTag				= False
    self.isOpenTag				= False
    self.isCommentTag				= False
    self.isXmlDeclarationTag			= False
    if not isinstance(parmXmlText, str):
      self.lastParseErr				= 1
      return
    self.openIx					= parmXmlText.find("<", parmIx)
    if self.openIx < 0:
      self.EOF					= True
      return
    self.closeIx				= parmXmlText.find(">", self.openIx+1)
    if self.closeIx < 0:
      self.lastParseErr				= 3
      self.lastParseErrLoc			= self.openIx
      return
    wsElement					= parmXmlText[self.openIx+1:self.closeIx]
    wsSpaceIx					= wsElement.find(" ")
    if wsSpaceIx < 0:
      self.name					= wsElement
    else:
      self.name					= wsElement[:wsSpaceIx]
      self.ParseAttributes(wsElement[wsSpaceIx+1:])
    if self.name == "":
      pass 								# should be a parse error
      self.isOpenTag				= True
    else:
      if self.name[0] == "/":
        self.isCloseTag				= True
        self.name				= self.name[1:]
      elif self.name[0] == "?":
        # Should check that this is the first tag, otherwise its an error.
        # Should also check that the last character is "?" too
        # <?xml version="1.0"?>
        self.isOpenTag				= True
        self.isCloseTag				= True
        self.isXmlDeclarationTag		= True
      elif self.name[0] == "-":
        # Should check that next character is also a dash and that the end is "-->" with no "--"
        # within the comment, but then we'd have to figure out what to do with those parse errors.
        # Since dash isn't a valid starting character for a tag name, this is at worst mis-handling
        # an error rather than doing the wrong thing to valid XML.
        self.isOpenTag				= True
        self.isCloseTag				= True
        self.isCommentTag			= True
      else:
        # Should be checking for valid name format.
        self.isOpenTag				= True
        if self.name[:-1] == "/":
          # this is the special case open/close tag
          self.isCloseTag			= True
          self.name				= self.name[:-1]

  def __repr__(self):
    return "%s: %d %d" % (self.name, self.openIx, self.closeIx)

  def ParseAttributes(self, parmText):
    wsState = 0
    wsAttributeName = ""
    wsAttributeValue = ""
    for wsC in parmText:
      if wsState == 0:			# collect name
        if wsC == "=":
          wsState = 1			# look for opening quote
        else:
          if wsC in XmlATTRIBUTENAMECHARS: wsAttributeName += wsC
      elif wsState == 1:
        if wsC == '"': wsState = 2
      elif wsState == 2:
        if wsC == '"':
          wsState = 0
          self.attributes[wsAttributeName] = wsAttributeValue
          wsAttributeName = ""
          wsAttributeValue = ""
        else:
          wsAttributeValue += wsC

class bzXmlParser(object):
  __slots__ = (
					'debug',
					'exeController',
					'EOF',
					'lastParseErr', 'lastParseErrLoc', 'lastParseTagName',
					'mergeAttributes',
					'parseIx', 'target', 'xmlText')

  def __init__(self, XmlText="", Target=None, ExeController=None, MergeAttributes=True, Debug=0):
    self.exeController		= ExeController
    self.debug			= Debug
    self.mergeAttributes	= MergeAttributes
    self.target			= Target
    self.xmlText		= XmlText
    self.InitParsingState()					# clear all variables for neatness
    if (self.target is not None) and (self.xmlText != ""):
      self.LoadXmlText()

  def InitParsingState(self):
    self.EOF			= False
    self.lastParseErr		= 0
    self.lastParseErrLoc	= 0
    self.lastParseTagName	= ""
    self.parseIx		= 0

  def PrintStatus(self):
    err_sample = self.xmlText[self.lastParseErrLoc:self.lastParseErrLoc+20]
    print("XML Status Err: %d Loc: %d '%s' Ix: %d" % (self.lastParseErr, self.lastParseErrLoc, err_sample, self.parseIx))

  def GetNextXmlTag(self):
    wsTag				= bzXmlTag(self.xmlText, self.parseIx)
    while wsTag.isCommentTag and (wsTag.lastParseErr == 0) and (not wsTag.EOF):
      # Ignore comments unless we have a reason to stop
      wsTag				= bzXmlTag(self.xmlText, self.parseIx)
    if (wsTag.lastParseErr > 0) or wsTag.EOF:
      self.lastParseErr			= wsTag.lastParseErr
      self.lastParseErrLoc		= wsTag.openIx
      self.EOF				= True
      self.parseIx			= len(self.xmlText) + 1
    else:
      self.parseIx			= wsTag.closeIx + 1
    if self.debug > 0:
      print("XML Tag %s @ %d Err: %d" % (wsTag.name, wsTag.openIx, wsTag.lastParseErr))
    return wsTag

  def GetXmlData(self, parmTag1, parmTag2):
    if parmTag1.closeIx < 0:
      return None
    return bzXmlData(self.xmlText[parmTag1.closeIx+1:parmTag2.openIx])

  def StoreData(self, Container=None, DataKey=None, DataValue=None, DataAttributes=None, Element=None):
    if Element is None:
      wsFormattedData			= DataValue
    else:
      if Element.physicalType == bafErTypes.Core_BooleanTypeCode:
        wsFormattedData			= bzUtil.Bool(DataValue)
      elif Element.physicalType == bafErTypes.Core_IntegerTypeCode:
        wsFormattedData			= bzUtil.Int(DataValue)
      else:
        wsFormattedData			= DataValue
    wsDatum				= wsFormattedData
    if DataAttributes is not None:
      if len(DataAttributes) > 0:
        wsDatum				= bafDataStore.bafDatumWithAttribs(wsFormattedData, DataAttributes)
    Container[DataKey]			= wsDatum

  def LoadXmlText(self, XmlText="", Target=None):
    if self.exeController:
      wsDataTypes			= self.exeController.GetCodeObject(bafErTypes.ErLogicalDataTypesName)
    else:
      wsDataTypes			= None
    if XmlText != "":
      self.xmlText			= XmlText
    if self.xmlText == "":
      self.lastParseErr			= 1
      self.lastParseErrLoc		= 0
      return False
    if Target is not None:
      self.target			= Target
    if self.target is None:
      self.target			= bafDataStore.bafTupleObject(ExeController=self.exeController)
      self.lastParseErr			= 2
      self.lastParseErrLoc		= 0
    self.target.ClearAll()							# clear target data area
    self.InitParsingState()							# clear these in case we are re-loading
    #
    # Process the first tag. Assume it is a container. Rename the target to match.
    #
    wsThisTag				= self.GetNextXmlTag()			# This is the first tag
    if wsThisTag.isXmlDeclarationTag:						# The declaration is not required
      # We should probably check the version and options at some point.
      wsThisTag				= self.GetNextXmlTag()
    if not wsThisTag.isOpenTag:
      self.lastParseErr			= 11
      self.lastParseErrLoc		= wsThisTag.openIx
      return False
    self.target._name			= wsThisTag.name			# The first tag names the XML object
    if not self.target._name:
      self.target._name			= "XML"
    if not self.target._tdict._name:
      self.target._tdict._name		= self.target._name
    wsContainerTags			= []
    wsContainerTags.append(wsThisTag)
    #
    # Start looping through the tags, starting with the second
    #
    wsThisTag				= self.GetNextXmlTag()
    if not wsThisTag.isOpenTag:
      self.lastParseErr			= 12
      self.lastParseErrLoc		= wsThisTag.openIx
      return False
    wsNextTag				= self.GetNextXmlTag()
    wsThisData				= self.GetXmlData(wsThisTag, wsNextTag)
    wsContainer				= self.target
    while not wsThisTag.EOF:
      if self.debug > 0:
        print("^^^^^^^^^^^^^")
        print(self.lastParseErr, self.EOF, self.parseIx, wsThisTag.name, wsThisData.data)
      if self.debug > 1:
        print("Container Names: " + repr(wsContainerTags))
        print("Container Path: " + GetContainerPathStr(wsContainer))
      self.lastParseTagName		= wsThisTag.name
      if 'type' in wsThisTag.attributes:
        wsDataType			= wsThisTag.attributes['type']
      else:
        wsDataType			= ''
      wsNextTagProcessed		= False
      wsDataProcessed			= False
      if wsThisTag.isOpenTag:
        if wsContainer._tdict is None:
          wsTDictElement		= None
        else:
          wsTDictElement		= wsContainer._tdict.Element(wsThisTag.name)
      if wsThisTag.isOpenTag and wsThisTag.isCloseTag:
        #
        # This is Null Element
        #
        if wsTDictElement is None:
          if wsDataType == 'dict':
            wsContainer[wsThisTag.name] = self.target.__class__()	# usually creates bzCompositionObject()
          if wsDataType == 'str':
            wsContainer[wsThisTag.name] = ""
          else:
            wsContainer[wsThisTag.name] = None
        else:
          if wsTDictElement.logicalType == wsDataTpes.AssociationSecondaryCode:
            wsContainer.MakeChildTuple(Name=wsThisTag.name)
          elif wsTDictElement.logicalType == wsDataTpes.AssociationPrimaryCode:
            wsContainer.MakeChildArray(Name=wsThisTag.name)
          else:
            wsContainer[wsThisTag.name] = wsTDictElement.defaultValue
      elif wsThisTag.isOpenTag and wsNextTag.isCloseTag:
        #
        # This is a simple data element
        #
        if wsThisTag.name != wsNextTag.name:
          self.lastParseErr		= 14
          self.lastParseErrLoc		= wsThisTag.openIx
          return False
        if wsDataType == 'dict':
          if wsThisData.data:
            # we should only get here for an empty container
            self.lastParseErr		= 20
            self.lastParseErrLoc	= wsThisTag.openIx
            return False
          else:
            wsContainer.MakeChildTuple(Name=wsThisTag.name)
        else:
          self.StoreData(Container=wsContainer, DataKey=wsThisTag.name,
						DataValue=wsThisData.data,
						DataAttributes=wsThisTag.attributes,
						Element=wsTDictElement)
        wsDataProcessed			= True
        wsNextTagProcessed		= True
      elif wsThisTag.isOpenTag and wsNextTag.isOpenTag:
        #
        # wsThisTag marks the start of a container
        #
        wsNewContainerTDict		= None
        wsContainerParent		= wsContainer		# save parent of container we are creating
        wsNewContainerElement		= wsContainerParent._tdict.Element(wsThisTag.name)
        if wsNewContainerElement is not None:
          wsNewContainerTDict		= wsNewContainerElement.collectionItemTDict
        if wsThisTag.name in wsContainer:
          # we already have seen one of these
          wsExistingItem		= wsContainer[wsThisTag.name]
          if isinstance(wsExistingItem, bafDataStore.bafDataStoreObject):
            # We already have an array of these tags
            wsContainer			= wsExistingItem.MakeChildTuple(Name=wsThisTag.name)
          elif isinstance(wsExistingItem, bafDataStore.bafTupleObject):
            # Turn the existing tupple into an array
              wsNewArray		= wsExistingItem.MakeInheritedDataStore(
								Name=wsThisTag.name,
								Parent=wsExistingItem._parent,
								TDict=wsExistingItem._tdict)
              wsNewArray.AppendData(wsExistingItem)
              wsExistingItem._parent	= wsNewArray
              wsContainer[wsThisTag.name]	= wsNewArray
              wsContainer		= wsNewArray.MakeChildTuple(Name=wsThisTag.name)
          else:
            # unexpected duplicate entity name or class implementation problem
            self.lastParseErr		= 15
            self.lastParseErrLoc	= wsThisTag.openIx
            return False
        else:
          wsContainer			= wsContainer.MakeChildTuple(Name=wsThisTag.name, TDict=wsNewContainerTDict)
        #
        # Common container wrap-up processing
        #
        wsContainerTags.append(wsThisTag)
        wsNewContainerElement		= wsContainerParent._tdict.Element(wsThisTag.name)
        if wsNewContainerElement.collectionItemTDict is None:
          # if this is the first time we have seen this collection, remember the TDict
          wsNewContainerElement.collectionItemTDict	= wsContainer._tdict
      elif wsThisTag.isCloseTag:
        #
        # This closes the current container
        #
        if self.debug > 2:
          self.DebugContainer("CLO", wsThisTag, wsContainer)
        if wsThisTag.name != wsContainer._name:
          if self.debug > 2:
            print("ERR:", wsThisTag.name, wsContainer._name, wsContainer.__class__.__name__)
          self.lastParseErr		= 16
          self.lastParseErrLoc		= wsThisTag.openIx
          return False
        wsContainerOpenTag		= wsContainerTags.pop()
        if self.mergeAttributes:
          for (wsThisKey, wsThisValue) in list(wsContainerOpenTag.attributes.items()):
            self.StoreData(Container=wsContainer, DataKey=wsThisKey, DataValue=wsThisValue)
        wsContainer			= wsContainer._parent
        if isinstance(wsContainer, bafDataStore.bafDataStoreObject):
          # XML arrays of records are anonymous. We just have to recognize them by finding
          # what might otherwise be interpreted as a duplicate. Since the XML doesn't tell
          # tell us that an array is ending, we just skip over them magically. We also
          # have some magic above to step into them.
          wsContainer			= wsContainer._parent
          if self.debug > 2:
            self.DebugContainer("POP", wsThisTag, wsContainer)
      else:
        #
        # Undefine tag sequence
        #
        self.lastParseErr		= 18
        self.lastParseErrLoc		= wsThisTag.openIx
        return False
      #
      # Common parse loop processing
      #
      if not wsDataProcessed:
        if not wsThisData.isAllWhiteSpace:
          self.lastParseErr		= 17
          self.lastParseErrLoc		= wsThisTag.openIx
          return False
      if wsNextTagProcessed:
        wsThisTag			= self.GetNextXmlTag()
      else:
        wsThisTag			= wsNextTag
      wsNextTag				= self.GetNextXmlTag()
      if self.debug >= 2:
        print(repr(wsThisTag))
        print(repr(wsThisData))
        print(repr(wsNextTag))
      wsThisData			= self.GetXmlData(wsThisTag, wsNextTag)
    #
    # Finis
    #
    return True

  def DebugContainer(self, parmID, parmTag, parmContainer):
    wsThisContainer			= parmContainer
    wsContainerStr			= ""
    wsDepth				= 0
    while wsThisContainer is not None:
      wsContainerStr			+= "(%s %s) " % (
						wsThisContainer._name, wsThisContainer.__class__.__name__,
						)
      wsThisContainer			= wsThisContainer._parent
      wsDepth				+= 1
      if wsDepth > 5:
        wsContainerStr			+= "LOOP"
        break
    print("%s: %s %s" % (parmID, parmTag.name, wsContainerStr))

class bzXmlData(object):
  __slots__ = ('rawData', 'data', 'isAllWhiteSpace')

  def __init__(self, parmRawData):
    self.rawData			= parmRawData
    self.data				= AsXmlUnquoted(self.rawData)
    self.isAllWhiteSpace		= True
    for wsC in self.rawData:
      if not (wsC in XmlWHITESPACECHARS):
        self.isAllWhiteSpace		= False
  """
