QuickDev Coding Style
========================

General
-----------

*Git:* All code and documentation is maintained in a git repository.

*PEP-8:* Code formatting and naming conforms to PEP-8 to a high degree.
This is enforced using pylint.

*PyLint:* Code is validated with pylint with a goal of getting a 10.0 score
using very few overrides of the default configuration.

Pylintrc and suggested in-line overrides should be docuemnted here.

*PyTest:*  Pytest modules should be created for every module.

*Sphinx:* is used for documentation. Modules use docstrings for module
usage documentation. This is encouraged by pylint which complains about
missing docstrings. Higher level documentation is provided in
document files using restructured text (rst) formatting.

File Handling Methods
------------------------

Methods which reference files should generally have parameters of
file_name and dir. If both are provided, they are joined with
os.path.join(dir, file_name). file_name can include a full or
partial path. There is nothing to prevent dir from including a
file name but that could be confusing.

The variable or attribute *path* should be a fully qualified
path to a file, including expansion of tilde and dots using
os.path.abspath().

Applications should be able to provide file_name and dir in a manner
that is natural to users and QuickDev should just do the right thing.

Exe_Controller / Err_Message
---------------------------------
EzCore modules should be usable as stand-alone utility functions
as well as integrate into QuickDev applications.

Exe_Controller provides a suite of services to QuickDev applications.
Whenever possible exe_controller should be an optional parameter for
ezcore modules. If provided, it should be used but teh module
should be useful without it.
