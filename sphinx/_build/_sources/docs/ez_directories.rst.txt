EzDev Directories
========================

Site: A directory which is the root of execution for an application on a particular server.
This will often be an Apache document root directory but that is not necessarily the case.
The Site directory will generally have a long life (the lifetime of that application on that server)
but it is considered a transient directory. It contains mainly symlinks to source data
and generated data and code.
Recreating a site directory is fast and easy.
It does not need to be directly backed up but all its data is backed up in othere ways
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
