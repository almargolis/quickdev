#!python
"""
    Create or repair a CommerceNode site.
"""

import argparse
import os

import cli
import const

class CnStart():
    """Create or repair a CommerceNode site. """
    __slots__ = ('err_ct', 'quiet', 'site_path')

    def __init__(self, args):
        self.err_ct = 0
        self.quiet = args.quiet
        if args.site_path is None:
            self.site_path = os.getcwd()
        else:
            self.site_path = args.site_path
        self.site_path = os.path.abspath(self.site_path)
        if not self.check_site_path():
            return
        if not self.check_conf_path():
            return

    def check_directory(self, name, path):
        """Create a directory if it doesn't exist. """
        if os.path.exists(path):
            if not os.path.isdir(path):
                self.error("'{}' is not a directory.".format(path))
                return False
        else:
            if cli.cli_input_yn("Create directory '{}'?".format(path)):
                os.mkdir(path)
            else:
                return False
        if not self.quiet:
            print("{} directory: {}.".format(name, path))
        return True

    def check_site_path(self):
        """Create site directory if it doesn't exist. """
        return self.check_directory('Site', self.site_path)

    def check_conf_path(self):
        """Create site conf directory if it doesn't exist. """
        path = os.path.join(self.site_path, const.SITE_CONF_DIR_NAME)
        return self.check_directory('Conf', path)

    def error(self, msg):
        """Print an error message."""
        self.err_ct += 1
        print(msg)

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('site_path',
                            action='store',
                            nargs='?',
                            default=None,
                            help='Path of site root directory.')
    arg_parser.add_argument('-q',
                            action='store_true',
                            dest='quiet',
                            help='Display as few messages as possible.')
    run_args = arg_parser.parse_args()
    cn = CnStart(run_args)
