#!/usr/bin/python
#############################################
#
#  bfsExeController Module
#
#
#  FEATURES
#
#  Collects all global program information in one place:
#
#  The main purpose is to centralize security and logging so it gets done
#  consistenly and properly with as little work as possible.
#
#  It also normailizes the process execution state regardless of how the program
#  is launched. This includes the ability to take a snapshot of the initial
#  environment and to restore that snapshot for subsequent execution.
#  The inital use for this is to test cgi programs at a normal command prompt.
#  The cgi environment, including forms data, can be initialized from either a
#  specifically created text file or a snapshot captured during normal operation.
#
#  It also eliminates the need for several imports of environment modules
#  in applications because that's all handled here.
#
#  WARNINGS
#
#
#  Copyright (C) 2009 by Albert B. Margolis - All Rights Reserved
#
#  06/10/2009: Start development
#  16 Aug 2009: rename from bafExeController to bfsExeController in BFS V2 to more appropriately
# 		contain application data.  Merge in table names from deleted bcsDb.py
# 		and bcsSecurity.py


#
# This module is part of the BFS Configuration system.
# It must only call other BFS modules that are part of the
# configuration system and must have as few hard
# dependencies as possible.
#
# This needs to be callable from all BFS System program and cgi modules
# so it it cannot import them. It can import some BFS System support modules.
#
try:
    from . import bfsGenProduct
    from . import bfsHtml
    from . import bfsSpecFile
except:
    bfsGenProduct = None
    bfsHtml = None
    bfsSpecFile = None

try:
    import pathInfo
    import sitelib.siteControls as siteControls
    import sitelib.siteFormats as siteFormats
except:
    pathInfo = None
    siteControls = None
    siteFormats = None

import pylib.bzContent as bzContent
import pylib.bzHtml as bzHtml
import pylib.bzLex as bzLex
import pylib.bafExeController as bafExeController
import pylib.bzUtil as bzUtil

import os
import sys
import time


#
# This is the global runtime environment for running programs.
# 	This environmewnt should be kept as lean as possible for all
# 	the reasonas that make globals generally undesirable.
#
# cgi is the old-school console device. It should go away once everything
# 	is converted to the new document format method.
#
# catMarkup / CatHtml are the catalog output device. It may be either the
# 	console or a file depending on the operation. This is also old-school
# 	and should be converted to the new document format method. It will
# 	still be kept distict from the console to allow catalog printing
# 	to be directed either to the console or a file or printer.
#
# As programs are converted to bafActionDef format they should also be converted
# 	to the new document format if at all practical.
#
class bfsExeController(bafExeController.bafExeController):
    #
    # This class should probably go away and get handled by site/app
    # configuration.
    #
    def __init__(self):
        bafExeController.bafExeController.__init__(self)
        # fill in variables that define this application
        self.pathInfo = pathInfo
        if bfsHtml is None:
            self.htmlDriverClass = None
        else:
            self.htmlDriverClass = bfsHtml.bfsHtml
        self.siteControls = siteControls
        self.siteFormats = siteFormats
        self.OpenDb()
        self.lastLoginError = 0
        self.runActionCode = ""
        self.runActionSwitch = ""
        self.progInfo = None
        ConfigureOldStyleCgi(self)


def ConfigureTransitionalExeAction(ExeAction):
    # We need to update run for transitional code because it get imported in
    # multiple places which causes side effects if there are two active
    # controllers. This was added because bfsGenProduct grabbed run so
    # there were two html instances competing to manage the html state.
    #
    global run
    ConfigureOldStyleCgi(ExeAction.exeController)
    run = ExeAction


def ConfigureOldStyleCgi(ExeController):
    if bfsHtml is None:
        ExeController.cgi = None
    else:
        ExeController.cgi = bfsHtml.bfsHtml(
            bzHtml.MODECGI,
            ExeController,
            ConversationId=ExeController.cgiGetData[bzHtml.CONVERSATIONKEY],
        )
    ExeController.errs.SetHtmlWriter(ExeController.cgi)
    #
    if bfsSpecFile is None:
        ExeController.catMarkup = None
        ExeController.catHtml = None
    else:
        ExeController.catMarkup = bfsSpecFile.bfsSpecFile()
        ExeController.catMarkup.clientSubstituteAndWriteTextFunction = (
            bfsGenProduct.WriteDesc
        )
        ExeController.catMarkup.clientProductFunction = bfsGenProduct.WriteProductEntry
        ExeController.catHtml = bfsHtml.bfsHtml(
            bzHtml.MODEFILE,
            ExeController,
            ConversationId=ExeController.cgiGetData[bzHtml.CONVERSATIONKEY],
        )
        ExeController.catMarkup.html = ExeController.catHtml


#
# Set Application Time Zone
#
if pathInfo is not None:
    os.environ["TZ"] = pathInfo.TimeZone
    time.tzset()

#
# Set Application Global ExeController Object
# This is deprecated. All new code runs in actions which inherit
# from the exeController.
#
ctlr = bfsExeController()
run = bafExeController.bafActionDef()
run.Init("Generic BFS Action", ExeController=ctlr)
