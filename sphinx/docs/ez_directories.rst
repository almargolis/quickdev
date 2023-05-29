EzDev Directories
========================

**Site:** A directory which is the root of execution for an application on a particular server.
This will often be an Apache document root directory but that is not necessarily the case.
The Site directory will generally have a long life (the lifetime of that application on that server)
but it is considered a transient directory. It contains mainly symlinks to source data
and generated data and code.
Recreating a site directory is fast and easy.
It does not need to be directly backed up but all its data is backed up in other ways
or can be generated.

CnPure: A collection of utilities needed to initialize a site for development or operations.
The code is this directory is pure Python that is not dependent on other CommerceNode
directories. This is required because much of the other CommerceNode code is generated --
by the utilities in CnPure.

CnCore: A collection of fundamental services that could be useful
for a broad range of applications.
These services mainly implement operating and network operations
as idioms with consistent data sources.

CnFramework: An application framework that can be used to build a variety of
online and command line applications.
CnFramework integrates a rich data modeling language
and DRY (Don’t Repeat Yourself) principles.

CnHosting: A set of utilities to assist in hosting of CommerceNode applications.
CnHosting supports multi-tenant hosts and multi-server applications

Site Types
------------

**Operations Site:** A site used to run an application in production.
Most operations sites reference critical operational data.
Operations sites have a minimum of development tools available.

**Development Site:** A site used to develop an EzDev application.
Most dev sites reference test data.
Development sites have access to a full set of development tools.
EzDev automatically creates basic configuration files for primary
development tools.

**PIP Site:** A development site for a PIP installable python package.
EzDev has utilities to assist with the boilerplate required for PIP.


Site Directory Content
------------------------

Every EzDev site directory contains a menu of content
which varies with the site type and application
requirements.

+-----------------+------+------------------------------------+
| Contents        | Site | Description                        |
|                 | Type |                                    |
+=================+======+====================================+
| conf/           | all  | configuration subdirectory.        |
+-----------------+------|------------------------------------+
| conf/site.conf  | all  | Ini file defining site function.   |
+-----------------+------+------------------------------------+
| [acronym].venv/ | most | Python virtual environment.        |
|                 |      | Potentially omitted for non-Python |
|                 |      | applications, but may be required  |
|                 |      | for EzDev utilities.               |
+-----------------+------+------------------------------------+
| pip/            | pip  | this is the root directory for     |
|                 |      | the pip upload    
+-----------------+------+------------------------------------+
| sphinx/         | dev  | Documentation development using    |
|                 |      | sphinx-doc.org.                    |
+-----------------+------+------------------------------------+
| pylintrc        | dev  | pylint configuration file.         |
+-----------------+------+------------------------------------+
+ .gitignore      | dev  | git exclusion list.                |
+-----------------+------+------------------------------------+
