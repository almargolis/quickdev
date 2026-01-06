"""
Tests apache utility functions.
"""

import os


from qdbase import exenv

from qdcore import inifile

from qdutils import apache

from . import test_qdstart

SITES_CONF_SELECTOR = "/etc/apache2/sites_available/*.conf"

conf_contents = []
conf_contents.append("# comment in column 1")
conf_contents.append("<VirtualHost *:80>")
conf_contents.append("    # indented comment")
conf_contents.append(
    '    DocumentRoot "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs"'
)
conf_contents.append("    ServerName jasonmccreary.local")
conf_contents.append(
    '    ErrorLog "/private/var/log/apache2/jasonmccreary.local-error_log"'
)
conf_contents.append(
    '    CustomLog "/private/var/log/apache2/jasonmccreary.local-access_log" common'
)
conf_contents.append("")
conf_contents.append(
    '    <Directory "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs">'
)
conf_contents.append("        AllowOverride All")
conf_contents.append("        Require all granted")
conf_contents.append("    </Directory>")
conf_contents.append("</VirtualHost>")
conf_contents.append("Include " + SITES_CONF_SELECTOR)


def test_apache_conf(tmpdir):
    """
    Tests apache2 conf file handler.
    """
    print(tmpdir)

    fin = tmpdir.join("conf.in")
    fin.write("\n".join(conf_contents))

    fout = tmpdir.join("conf.out")

    apache_conf = apache.ApacheConf()
    apache_conf.load(fin)
    apache_conf.write(fout)

    with open(fout, encoding="utf-8") as f:
        out_lines = f.readlines()
    for ix, this_line in enumerate(out_lines):
        print(ix, ">>>", conf_contents[ix])
        print(ix, "<<<", this_line)
        assert this_line == conf_contents[ix] + "\n"

    includes = apache_conf.find_directives("Include", value=SITES_CONF_SELECTOR)
    assert len(includes) == 1
    assert includes[0].value == SITES_CONF_SELECTOR


class MakeDevSite:
    def __init__(self, acronym, apache_host):
        self.acronym = acronym
        self.apache_host = apache_host
        self.qdsite_dpath = os.path.join(exenv.g.qdsites_dpath, acronym)
        self.website_subdir = "html"
        self.website_dpath = os.path.join(self.qdsite_dpath, self.website_subdir)
        self.domain_name = "www.{}.com".format(acronym)
        www_ini_fn = os.path.join(exenv.g.qdhost_websites_dpath, acronym + ".ini")
        with open(www_ini_fn, "w", encoding="utf-8") as www_ini_file:
            www_ini_file.write(
                "acronym={}\ndomain_name={}\n".format(acronym, self.domain_name)
            )
        dev_ini_fn = os.path.join(exenv.g.qdhost_qdsites_dpath, acronym + ".ini")
        with open(dev_ini_fn, "w", encoding="utf-8") as dev_ini_file:
            dev_ini_file.write(
                "acronym={}\nqdsite_dpath={}\n".format(acronym, self.qdsite_dpath)
            )
        os.mkdir(self.qdsite_dpath)
        os.mkdir(self.website_dpath)
        conf_dpath = os.path.join(self.qdsite_dpath, "conf")
        os.mkdir(conf_dpath)
        conf_fpath = os.path.join(conf_dpath, "site.conf")
        with open(conf_fpath, "w", encoding="utf-8") as site_ini_file:
            site_ini_file.write(
                "acronym={}\nwebsite_subdir={}\n".format(acronym, self.website_subdir)
            )
        self.make_expected_vhost_conf()

    def make_expected_vhost_conf(self):
        access_log_fpath = os.path.join(
            self.apache_host.log_base_dir, self.acronym + apache.ACCESS_LOG_SUFFIX
        )
        error_log_fpath = os.path.join(
            self.apache_host.log_base_dir, self.acronym + apache.ERROR_LOG_SUFFIX
        )
        self.vhost_conf = []
        self.vhost_conf.append("<VirtualHost *:80>\n")
        self.vhost_conf.append('\tDocumentRoot "{}"\n'.format(self.website_dpath))
        self.vhost_conf.append("\tServerName {}\n".format(self.domain_name))
        self.vhost_conf.append('\tErrorLog "{}"\n'.format(error_log_fpath))
        self.vhost_conf.append('\tCustomLog "{}" common\n'.format(access_log_fpath))
        self.vhost_conf.append("\n")
        self.vhost_conf.append('\t<Directory "{}">\n'.format(self.website_dpath))
        self.vhost_conf.append("\t\tAllowOverride All\n")
        self.vhost_conf.append("\t\tRequire all granted\n")
        self.vhost_conf.append("\t</Directory>\n")
        self.vhost_conf.append("</VirtualHost>\n")

    def check_vhost_conf(self):
        vhost_conf_fpath = os.path.join(
            self.apache_host.sites_available_dir_path, self.acronym + ".conf"
        )
        try:
            with open(vhost_conf_fpath, "r") as f:
                generated_lines = f.readlines()
        except FileNotFoundError:
            # a better handler needed
            generated_lines = []
        len_expected = len(self.vhost_conf)
        len_generated = len(generated_lines)
        line_ct = max(len_expected, len_generated)
        for ix in range(line_ct):
            if ix < len_expected:
                line_expected = self.vhost_conf[ix]
            else:
                line_expected = ""
            if ix < len_generated:
                line_generated = generated_lines[ix]
                assert line_expected == line_generated
            else:
                pass # needed a better handler


def test_config_vhosts(tmpdir):
    """
    Test apache2 vhost generation.

    Uses test_qdstart.MakeQdev() to create test environment so
    nothing should try to write to actual system files.
    """
    test_qdstart.MakeQdChroot(tmpdir)
    apache_host = apache.ApacheHosting()
    dev1 = MakeDevSite("xx1", apache_host)
    apache.config_vhosts()
    dev1.check_vhost_conf()
