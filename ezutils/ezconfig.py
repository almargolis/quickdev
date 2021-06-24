#!python
"""
EzConfig completes the bootstrap process for an EzDev project.

It creates program stubs and ???. It is run after EzStart creates
the basic directory structure and Xpython processes xpy source
code and builds the project configuration database.
"""
import os

from ezcore import ezconst
from ezcore import ezsqlite
from ezcore import exe
from ezcore import xsource

PROG_STUB = []
PROG_STUB.append("import $xlocal.this_module$")
PROG_STUB.append("from ezcore import exe")
PROG_STUB.append("")
PROG_STUB.append("ez_env = exe.EzEnv()")
PROG_STUB.append("p = $xlocal.this_module$.$xlocal.action$(ez_env=ez_env)")
PROG_STUB.append("p.run()")

class EzConfig(exe.EzAction):
    __slots__ = ('db', 'project_db_path')

    def __init__(self, ez_env):
        super().__init__(ez_env=ez_env)
        self.project_db_path = os.path.join(self.ez_env.conf_dir_path,
                                            ezconst.PROJECT_DB_FN)
        self.db = ezsqlite.EzSqlite(self.project_db_path, debug=0)

    def gen_program_stubs(self):
        for this_row in self.db.select('progs', '*'):
            action_name = this_row['action_name']
            action_spec = self.db.lookup(xsource.XDB_ACTIONS,
                                         where={'action_name': action_name})
            xlocal = {}
            xlocal['this_module'] action_spec['module']
            xlocal['action'] = action_name
            gen = xsource.XSource(module_name=this_row['prog_name'],
                                  db=self.db, source_lines=PROG_STUB)

if __name__ == '__main__':
    ez_env = exe.EzEnv()
    p = EzConfig(ez_env=ez_env)
