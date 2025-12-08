import os
import sys

from . import qdstart

from qdbase import cliargs
from qdbase import cliinput
from qdbase import exenv
from qdbase import pdict
from qdbase import qdsqlite

from qdcore import filedriver
from qdcore import textfile
from qdcore import virtfile
from qdcore import utils
from qdcore import inifile
from qdcore import qdconst
from qdcore import qdsite


#
# These are good guides for apache on macos:
# 	https://jasonmccreary.me/articles/configure-apache-virtualhost-mac-os-x/
# 	https://getgrav.org/blog/macos-catalina-apache-multiple-php-versions
# 	https://tecadmin.net/install-apache-macos-homebrew/
#
# Handy apache commands:
# 	sudo apachectl -k restart
# 	sudo apachectl configtest
#       dscacheutil -flushcache			-- this clears macos dns cache
#
APACHE_CONFIG_FILE = "httpd.conf"
SITES_AVAILABLE = "sites-available"
SITES_ENABLED = "sites-enabled"
DEFAULT_SITE_CONF_FN = "default"
ACCESS_LOG_SUFFIX = ".local-access-log"
ERROR_LOG_SUFFIX = ".local-error-log"

MACOS_HOMEBREW = {
    "apache_config_dir_path": "/usr/local/etc/httpd",
    "document_base_dir": "~/Sites",
    "log_base_dir": "/private/var/log/apache2/",
    "apachectl": "/usr/local/bin/apachectl",
    "httpd": "/usr/local/bin/httpd",
    "service_start": "brew services start httpd",
}

MACOS_DARWIN = {
    # The MacOS apachectl seems to be implemented as launchctl.
    "apache_config_dir_path": "/private/etc/apache2",  # symlink to /etc/apache2
    "document_base_dir": "~/Sites",
    "log_base_dir": "/private/var/log/apache2/",
    "apachectl": "/usr/sbin/apachectl",
    "httpd": "/usr/sbin/httpd",
    "service_status": "launchctl print system/org.apache.httpd",
    "service_disable": "launchctl unload -w /System/Library/LaunchDaemons/org.apache.httpd.plist",
}

DEBIAN = {
    "apache_config_dir_path": "/etc/apache2",
    "document_base_dir": "/var/www",
    "log_base_dir": "/var/log/apache2",
}

ALL_APACHE_PLATFORMS = {
    exenv.PLATFORM_DARWIN: MACOS_DARWIN,
    exenv.PLATFORM_LINUX: DEBIAN,
}

if exenv.execution_env.platform in ALL_APACHE_PLATFORMS:
    APACHE_PLATFORM = ALL_APACHE_PLATFORMS[exenv.execution_env.platform]
else:
    raise ValueError(
        "Unsupported Apache platform '{}'.".format(exenv.execution_env.platform)
    )


#
# ConfDirectiveDef defines an Apache *.conf file directive and tracks its
# *.conf file parsing/editing state.
#
class ApacheDirective:
    """
    Records one apache conf file directive.
    """

    __slots__ = (
        "count_found",
        "count_max",
        "directives",
        "name",
        "name_uc",
        "parent_block",
        "value",
    )

    def __init__(self, name, value, count_max=1, parent_block=None):
        self.count_found = 0
        self.count_max = count_max
        self.directives = None
        self.name = name
        self.name_uc = name.upper()  # apache config directives are case insensitive
        self.parent_block = parent_block
        self.value = value


class ApacheConf:
    """
    Records an apache configuation as a list of ApacheDirective objects.

    It saves comments and blank lines so that it can recreate the
    configuration file after any changes are made.
    """

    __slots__ = ("directives", "file_handle", "file_path")

    def __init__(self, file_path=None):
        self.directives = []
        self.file_path = file_path
        self.file_handle = None

    def add_directive(self, name, value):
        self.directives.append(ApacheDirective(name, value))

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

    def load(self, file_path=None, read_write=False, backup=True):
        """Read config file and build directive list."""
        self.directives = []
        current_block = self
        line_ct = 0
        continuation = ""
        self.file_handle = virtfile.VirtFile()
        if read_write:
            mode = filedriver.MODE_RR
        else:
            mode = filedriver.MODE_R
        if file_path is None:
            file_path = self.file_path
        else:
            if self.file_path is None:
                self.file_path = file_path
        self.file_handle.open(file_path, mode=mode, backup=backup)
        try:
            for this in self.file_handle.readlines():
                line_ct += 1
                if this[-1] == "\\":
                    continuation += this[:-1]
                else:
                    continuation += this
                    result = self.parse(continuation)
                    continuation = ""
                    if isinstance(result, str):
                        current_block.directives.append(result)
                    else:
                        (new_block, end_block, name, value) = result
                        if end_block:
                            if current_block.name_uc != name.upper():
                                raise ValueError(
                                    "Unmatched '<!{}>' @ {}".format(name, line_ct)
                                )
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

    def write(self, file_path=None, swap=True, backup=True):
        def write_block(spc, d):
            for this in d.directives:
                if isinstance(this, str):
                    if this == "":
                        self.file_handle.write("\n")
                    else:
                        self.file_handle.write(spc + this + "\n")
                elif this.directives is None:
                    self.file_handle.write(spc + this.name + " " + this.value + "\n")
                else:
                    open_ln = "<" + this.name
                    if this.value != "":
                        open_ln += " " + this.value
                    open_ln += ">"
                    self.file_handle.write(spc + open_ln + "\n")
                    write_block(spc + "    ", this)
                    self.file_handle.write(spc + "</" + this.name + ">\n")

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
                if file_path is None:
                    file_path = self.file_path
                else:
                    if self.file_path is None:
                        self.file_path = file_path
                self.file_handle.open(file_path, mode=mode, backup=backup)
            write_block("", self)
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
        if trimmed == "":
            return trimmed
        if trimmed[0] == "#":
            return trimmed
        if trimmed[0] == "<":
            trimmed = trimmed[1:]
            if trimmed[0] == "/":
                trimmed = trimmed[1:]
                end_block = True
            else:
                new_block = True
            if trimmed[-1] == ">":
                # The closing bracket should always be found but
                # we don't complain if it's missing.
                trimmed = trimmed[:-1]

        value_ix = utils.FindFirstWhiteSpace(trimmed)
        if value_ix < 0:
            directive = trimmed.strip()
            value = None
        else:
            directive = trimmed[:value_ix].strip()
            value = trimmed[value_ix + 1 :].strip()

        return (new_block, end_block, directive, value)


class ApacheHosting:
    """
    Class to manage configuration of Apache web server with virtual hosts
    under debian style linux and macos native or homebrew.
    """

    # pylint: disable=too-many-instance-attributes
    __slots__ = (
        "apache_config_dir_path",
        "apache_config_file_path",
        "default_page_path",
        "document_base_dir",
        "log_base_dir",
        "parsed_config_file",
        "sites_available_dir_path",
        "sites_enabled_dir_path",
    )

    def __init__(self):
        # just consider this a good place to track core directories.
        self.apache_config_dir_path = exenv.safe_join(
            exenv.g.root, APACHE_PLATFORM["apache_config_dir_path"]
        )
        self.apache_config_file_path = os.path.join(
            self.apache_config_dir_path, APACHE_CONFIG_FILE
        )
        self.sites_available_dir_path = os.path.join(
            self.apache_config_dir_path, SITES_AVAILABLE
        )
        self.sites_enabled_dir_path = os.path.join(
            self.apache_config_dir_path, SITES_ENABLED
        )
        self.document_base_dir = APACHE_PLATFORM["document_base_dir"]
        self.document_base_dir = os.path.expanduser(self.document_base_dir)
        self.log_base_dir = APACHE_PLATFORM["log_base_dir"]
        self.log_base_dir = os.path.expanduser(self.log_base_dir)
        self.default_page_path = os.path.join(self.document_base_dir, "index.html")
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
        exenv.make_directory(
            "Apache configuration", self.apache_config_dir_path, raise_ex=True
        )
        if not exenv.make_directory(
            "Sites Available", self.sites_available_dir_path, mode=0o755
        ):
            return False
        if not exenv.make_directory(
            "Sites Enabled", self.sites_enabled_dir_path, mode=0o755
        ):
            return False
        default_site_conf_path = os.path.join(
            self.sites_available_dir_path, DEFAULT_SITE_CONF_FN
        )
        if not os.path.isfile(default_site_conf_path):
            with textfile.TextFile(
                file_name=default_site_conf_path, open_mode="w"
            ) as f:
                f.writeln("<VirtualHost *:80>")
                f.writeln('\tDocumentRoot "/Library/WebServer/Documents')
                f.writeln("</VirtualHost>")
        return True

    def create_host(self, site_name):
        pass
        # add a line to hosts file
        # 127.0.0.1       jasonmccreary.local

    def create_virtual_host(self, host_devsite_ini, host_website_ini, site_info):
        """
        Creates or replaces an apache2 virtual host conf file.

        host_website_ini is owned by operations administrators.  Application
        developers have to go through a process to have those
        parameters changed. This includes domain and host names and
        the top levels of directory paths.

        site_info is owned by application developers.
        """
        site_acronym = host_devsite_ini[qdsite.CONF_PARM_ACRONYM]
        qdsite_dpath = host_devsite_ini[qdsite.CONF_PARM_SITE_DPATH]
        domain_name = host_website_ini[qdsite.CONF_PARM_HOST_NAME]
        website_subdir = site_info.ini_data[qdsite.CONF_PARM_WEBSITE_SUBDIR]

        apache_conf_path = os.path.join(
            self.sites_available_dir_path, site_acronym + ".conf"
        )
        document_root = os.path.join(qdsite_dpath, website_subdir)
        access_log = os.path.join(self.log_base_dir, site_acronym + ACCESS_LOG_SUFFIX)
        error_log = os.path.join(self.log_base_dir, site_acronym + ERROR_LOG_SUFFIX)

        with textfile.TextFile(file_name=apache_conf_path, open_mode="w") as f:
            f.writeln("<VirtualHost *:80>")
            f.writeln('\tDocumentRoot "{}"'.format(document_root))
            f.writeln("\tServerName {}".format(domain_name))
            f.writeln('\tErrorLog "{}"'.format(error_log))
            f.writeln('\tCustomLog "{}" common'.format(access_log))
            f.writeln("")
            f.writeln('\t<Directory "{}">'.format(document_root))
            f.writeln("\t\tAllowOverride All")
            f.writeln("\t\tRequire all granted")
            f.writeln("\t</Directory>")
            f.writeln("</VirtualHost>")


def init_hosting():
    if not cliinput.cli_input_yn("Do you want to initialize or repair this host?"):
        sys.exit(-1)
    a = ApacheHosting()
    if not os.path.isfile(a.apache_config_file_path):
        raise ValueError(
            "Unsupported Apache configuration, missing '{}'.".format(
                a.apache_config_file_path
            )
        )
    if not a.create_directories():
        print("Host not initialized.")
        return False
    exenv.save_org(a.apache_config_file_path)
    a.load_host_conf_file()
    available_sites_selector = os.path.join(a.sites_available_dir_path, "*.conf")
    includes = a.parsed_config_file.find_directives(
        "Include", value=available_sites_selector, recursive=False
    )
    if len(includes) < 1:
        a.parsed_config_file.add_directive(
            "Include", os.path.join(a.sites_enabled_dir_path, "*.conf")
        )
        a.parsed_config_file.write()


def config_vhosts():
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath)
    apache_host = ApacheHosting()
    websites = db.select(qdsite.HDB_WEBSITES)
    for host_website_ini in websites:
        host_devsite_ini = db.lookup(
            qdsite.qdsite.HDB_DEVSITES,
            where={qdsite.CONF_PARM_UUID: host_website_ini[qdsite.CONF_PARM_UUID]},
        )
        qdsite_info = qdsite.QdSite(
            qdsite_dpath=host_devsite_ini[qdsite.CONF_PARM_SITE_DPATH]
        )
        apache_host.create_virtual_host(host_devsite_ini, host_website_ini, qdsite_info)


def show_hosting():
    pass


webini_dict = pdict.TupleDict()
webini_dict.add_column(pdict.Text(qdsite.CONF_PARM_UUID))
webini_dict.add_column(pdict.Text(qdsite.CONF_PARM_HOST_NAME))
webini_dict.add_column(pdict.Text(qdsite.CONF_PARM_WEBSITE_SUBDIR))


def register_website(qdsite_dpath=None, api_data=None):
    """
    Register a website that has not previously been registered.
    """
    site = qdsite.QdSite(qdsite_dpath=qdsite_dpath)
    db = qdsqlite.QdSqlite(exenv.g.qdhost_db_fpath)

    # Update hosting database
    website_row = {}
    website_row[qdsite.CONF_PARM_UUID] = site_uuid
    website_row[qdsite.CONF_PARM_HOST_NAME] = site.ini_data[qdsite.CONF_PARM_ACRONYM]
    website_row[qdsite.CONF_PARM_WEBSITE_SUBDIR] = site.qdsite_dpath
    db.insert(qdsite.HDB_WEBSITES, website_row)

    # Update develelopment site conf file
    site.ini_data[qdsite.CONF_PARM_UUID] = site_uuid
    site.ini_data[qdsite.CONF_PARM_SITE_UDI] = site_udi
    site.write_site_ini()


if __name__ == "__main__":
    # There is a great deal of symetry between hosting.py and apache.py
    # commands. If you change one, check the other to see if similar
    # changes are needed.
    menu = cliargs.CliCommandLine()
    exenv.command_line_quiet(menu)
    exenv.command_line_site(menu)
    exenv.command_line_website(menu)

    menu.add_item(
        cliargs.CliCommandLineActionItem("hinit", init_hosting, help="Initialize host")
    )
    menu.add_item(
        cliargs.CliCommandLineActionItem(
            "show", show_hosting, help="Show host information"
        )
    )
    menu.add_item(
        cliargs.CliCommandLineActionItem(
            "vhosts", config_vhosts, help="Configure Apache vhosts"
        )
    )
    #
    m = menu.add_item(
        cliargs.CliCommandLineActionItem("sinit", init_site, help="Initialize site")
    )
    m.add_parameter(
        cliargs.CliCommandLineParameterItem(exenv.ARG_S_SITE, is_positional=True)
    )
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
