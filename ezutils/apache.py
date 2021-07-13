import os
import sys

import ezstart

from ezcore import cli
from ezcore import exenv
from ezcore import filedriver
from ezcore import virtfile
from ezcore import utils

#
# These are good guides for apache on macos:
#	https://jasonmccreary.me/articles/configure-apache-virtualhost-mac-os-x/
#	https://getgrav.org/blog/macos-catalina-apache-multiple-php-versions
#	https://tecadmin.net/install-apache-macos-homebrew/
#
# Handy apache commands:
#	sudo apachectl -k restart
#	sudo apachectl configtest
#       dscacheutil -flushcache			-- this clears macos dns cache
#
APACHE_CONFIG_FILE = 'httpd.conf'
SITES_AVAILABLE = 'sites-available'
SITES_ENABLED = 'sites-enabled'
DEFAULT_SITE_CONF_FN = 'default'

MACOS_HOMEBREW = {
    'apache_config_dir_path':	'/usr/local/etc/httpd',
    'document_base_dir':	'~/Sites',
    'apachectl':		'/usr/local/bin/apachectl',
    'httpd':			'/usr/local/bin/httpd',
    'service_start':		'brew services start httpd'
}

MACOS_DARWIN = {
    # The MacOS apachectl seems to be implemented as launchctl.
    'apache_config_dir_path':	'/private/etc/apache2',			# symlink to /etc/apache2
    'document_base_dir':	'~/Sites',
    'apachectl':		'/usr/sbin/apachectl',
    'httpd':			'/usr/sbin/httpd',
    'service_status':		'launchctl print system/org.apache.httpd',
    'service_disable':		'launchctl unload -w /System/Library/LaunchDaemons/org.apache.httpd.plist'
}

DEBIAN = {
    'apache_config_dir_path':	'/etc/apache2',
    'document_base_dir':	'/var/www'
}

ALL_APACHE_PLATFORMS = {
    exenv.PLATFORM_DARWIN: MACOS_DARWIN,
    exenv.PLATFORM_LINUX: DEBIAN
}

if exenv.execution_env.platform in ALL_APACHE_PLATFORMS:
    APACHE_PLATFORM = ALL_APACHE_PLATFORMS[exenv.execution_env.platform]
else:
    raise ValueError("Unsupported Apache platform '{}'.".format(
                     exenv.execution_env.platform))

#
# ConfDirectiveDef defines an Apache *.conf file directive and tracks its
# *.conf file parsing/editing state.
#
class ApacheDirective():
    """
    Records one apache conf file directive.
    """
    __slots__ = ('count_found', 'count_max', 'directives',
                 'name', 'name_uc',
                 'parent_block', 'value')
    def __init__(self, name, value, count_max=1, parent_block=None):
        self.count_found = 0
        self.count_max = count_max
        self.directives = None
        self.name = name
        self.name_uc = name.upper()		# apache config directives are case insensitive
        self.parent_block = parent_block
        self.value = value

class ApacheConf():
    """
    Records an apache configuation as a list of ApacheDirective objects.

    It saves comments and blank lines so that it can recreate the
    configuration file after any changes are made.
    """
    __slots__ = ('directives', 'file_handle')
    def __init__(self):
        self.directives = []
        self.file_handle = None

    def find_directives(self, name, value=None, recursive=True):
        result = []
        name_uc = name.upper()
        def search_this(d):
            for this in d.directives:
                if isinstance(this, ApacheDirective):
                    if this.name_uc == name_uc:
                        if (value is None) or (value == this.value):
                            result.append(this)
                    if recursive and (this.directives is not None):
                        search_this(this)
        search_this(self)
        return result

    def load(self, path, read_write=False, backup=True):
        """ Read config file and build directive list. """
        self.directives = []
        current_block = self
        line_ct = 0
        continuation = ''
        self.file_handle = virtfile.VirtFile()
        if read_write:
            mode = filedriver.MODE_RR
        else:
            mode = filedriver.MODE_R
        self.file_handle.open(path, mode=mode, backup=backup)
        try:
            for this in self.file_handle.readlines():
                line_ct += 1
                if this[-1] == '\\':
                    continuation += this[:-1]
                else:
                    continuation += this
                    result = self.parse(continuation)
                    continuation = ''
                    if isinstance(result, str):
                        current_block.directives.append(result)
                    else:
                        (new_block, end_block, name, value) = result
                        if end_block:
                            if current_block.name_uc != name.upper():
                                raise ValueError("Unmatched '<!{}>' @ {}".format(
                                                 name, line_ct
                                                 ))
                            current_block = current_block.parent_block
                        else:
                            directive = ApacheDirective(name, value)
                            current_block.directives.append(directive)
                            if new_block:
                                directive.directives = []
                                directive.parent_block = current_block
                                current_block = directive
        finally:
            if not read_write:
                self.file_handle.keep()
                self.file_handle = None


    def write(self, file_name=None, swap=True, backup=True):
        def write_block(spc, d):
            for this in d.directives:
                if isinstance(this, str):
                    if this == '':
                        self.file_handle.write('\n')
                    else:
                        self.file_handle.write(spc + this + '\n')
                elif this.directives is None:
                    self.file_handle.write(spc + this.name + ' ' + this.value + '\n')
                else:
                    open_ln = '<' + this.name
                    if this.value != '':
                        open_ln += ' ' + this.value
                    open_ln += '>'
                    self.file_handle.write(spc + open_ln + '\n')
                    write_block(spc+'    ', this)
                    self.file_handle.write(spc + '</' + this.name + '>\n')

        try:
            if self.file_handle is None:
                # If the config file was opened in read_write
                # mode by load(), file open parameters to
                # this method are ignored.
                self.file_handle = virtfile.VirtFile()
                if swap:
                    mode = filedriver.MODE_S
                else:
                    mode = filedriver.MODE_W
                self.file_handle.open(path, mode=mode, backup=backup)
            write_block('', self)
        except:
            if self.file_handle is not None:
                self.file_handle.drop()
                self.file_handle = None
            raise
        finally:
            if self.file_handle is not None:
                self.file_handle.keep()
                self.file_handle = None

    def parse(self, config_line):
        """
        Parse a config file line and add it to list.

        Config file parsing rules are pretty simple:
        https://httpd.apache.org/docs/current/configuring.html
        """
        new_block = False
        end_block = False
        trimmed = config_line.strip()
        if trimmed == '':
            return trimmed
        if trimmed[0] == '#':
            return trimmed
        if trimmed[0] == '<':
            trimmed = trimmed[1:]
            if trimmed[0] == '/':
                trimmed = trimmed[1:]
                end_block = True
            else:
                new_block = True
            if trimmed[-1] == '>':
                # The closing bracket should always be found but
                # we don't complain if it's missing.
                trimmed = trimmed[:-1]

        value_ix = utils.FindFirstWhiteSpace(trimmed)
        if value_ix < 0:
            directive = trimmed.strip()
            value = None
        else:
            directive = trimmed[:value_ix].strip()
            value = trimmed[value_ix+1:].strip()

        return (new_block, end_block, directive, value)

class ApacheHosting():
    """
    Class to manage configuration of Apache web server with virtual hosts
    under debian style linux and macos native or homebrew.
    """
    # pylint: disable=too-many-instance-attributes
    __slots__ = (
        'apache_config_dir_path', 'apache_config_file_path',
        'default_page_path', 'document_base_dir',
        'parsed_config_file',
        'sites_available_dir_path', 'sites_enabled_dir_path'
        )
    def __init__(self):
        # just consider this a good place to track core directories.
        self.apache_config_dir_path = APACHE_PLATFORM['apache_config_dir_path']
        self.apache_config_file_path = os.path.join(self.apache_config_dir_path, APACHE_CONFIG_FILE)
        self.sites_available_dir_path = os.path.join(self.apache_config_dir_path, SITES_AVAILABLE)
        self.sites_enabled_dir_path = os.path.join(self.apache_config_dir_path, SITES_ENABLED)
        self.document_base_dir = APACHE_PLATFORM['document_base_dir']
        self.document_base_dir = os.path.expanduser(self.document_base_dir)
        self.default_page_path = os.path.join(self.document_base_dir, 'index.html')
        self.parsed_config_file = None

    def load_host_conf_file(self):
        self.parsed_config_file = ApacheConf()
        self.parsed_config_file.load(self.apache_config_file_path)

    def create_directories(self):
        """
        Verify existance of apache configuration directories and create if missing.

        This creates debian style directories under macos. It shouldn't do anything
        under debian style linux installations.
        """
        if not os.path.isdir(self.apache_config_dir_path):
            print("Apache config directory {} not found.".format(self.apache_config_dir_path))
            sys.exit(-1)
        if not os.path.isdir(self.sites_available_dir_path):
            os.mkdir(self.sites_available_dir_path, mode=0o755)
        if not os.path.isdir(self.sites_enabled_dir_path):
            os.mkdir(self.sites_enabled_dir_path, mode=0o755)
        default_site_conf_path = os.path.join(self.sites_available_dir_path, DEFAULT_SITE_CONF_FN)
        if not os.path.isfile(default_site_conf_path):
            with textfile.open(default_site_conf_path, 'w') as f:
                f.writeln('<VirtualHost *:80>')
                f.writeln('\tDocumentRoot "/Library/WebServer/Documents')
                f.writeln('</VirtualHost>')
        self.parsed_config_file.add('Include', os.path.join(self.sites_enabled_dir_path, '*.conf'))


    def create_host(self, site_name):
        pass
        # add a line to hosts file
        # 127.0.0.1       jasonmccreary.local

    def create_virtual_host(self, site_name):
        site_conf_path = os.path.join(self.sites_available_dir_path, site_name + '.conf')
        if not os.path.isfile(site_conf_path):
            with textfile.open(site_conf_path, 'w') as f:
                f.writeln('<VirtualHost *:80>')
                f.writeln('\tDocumentRoot "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs"')
                f.writeln('\tServerName jasonmccreary.local')
                f.writeln('\tErrorLog "/private/var/log/apache2/jasonmccreary.local-error_log"')
                f.writeln('\tCustomLog "/private/var/log/apache2/jasonmccreary.local-access_log" common')
                f.writeln('')
                f.writeln('\t<Directory "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs">')
                f.writeln('t\tAllowOverride All')
                f.writeln('\t\tRequire all granted')
                f.writeln('\t</Directory>')
                f.writeln('</VirtualHost>')

def init_hosting():
    if not cli.cli_input_yn("Do you want to initialize or repair this host?"):
        sys.exit(-1)
    a = ApacheHosting()
    if not os.path.isfile(a.apache_config_file_path):
        raise ValueError("Unsupported Apache configuration, missing '{}'.".format(
                         a.apache_config_file_path))
    ez = ezstart.EzStart()
    ez.save_org(a.apache_config_file_path)
    a.load_host_conf_file()
    available_sites_selector = so.path.join(a.sites_available_dir_path, '*.conf')
    includes = a.parsed_config_file.find_directives('Include',
                                                    value=available_sites_selector,
                                                    recursive=False)
    if len(includes) < 1:
        a.keep()

def show_hosting():
    pass

def init_site(site_name):
    resp = cli.cli_input("Do you want to initialize or repair site '{}'?".format(site_name), "yn")

if __name__ == '__main__':
    # There is a great deal of symetry between hosting.py and apache.py
    # commands. If you change one, check the other to see if similar
    # changes are needed.
    menu = cli.CliCommandLine()
    exenv.command_line_quiet(menu)
    exenv.command_line_site(menu)
    exenv.command_line_website(menu)

    menu.add_item(cli.CliCommandLineActionItem('hinit', init_hosting, help="Initialize host"))
    menu.add_item(cli.CliCommandLineActionItem('show', show_hosting, help="Show host information"))
    #
    m = menu.add_item(cli.CliCommandLineActionItem('sinit', init_site, help="Initialize site"))
    m.add_parameter(cli.CliCommandLineParameterItem('s', is_positional=True))
    #
    exenv.execution_env.set_run_name(__name__)
    menu.cli_run()


"""
value_store = {}
value_store['DocumentRoot'] = document_base_dir
apache_httpd_conf_path = os.path.join(apache_config_dir_path, APACHE_CONFIG_FILE)

try:
    os.mkdir(document_base_dir)
except FileExistsError:
    pass						# it is already there. OK.

p = html.HtmlPage()
f = open(default_page_path, "w")
f.write(p.render_html())
f.close()

inp = textfile.open(apache_httpd_conf_path, 'r', debug=0)
out = inp.create_temp_output(debug=0)
l = 0
while l is not None:
    l = inp.readln()
    if l is not None:
        #print(l)
        directive_def = edit_defs.find(l)
        if directive_def is None:
            new_l = l
        else:
            new_l = directive_def.apply(value_store)
        out.writeln(new_l)
inp.safe_close()

"""
