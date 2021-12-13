"""
Tests apache utility functions.
"""
from qdutils import apache
from qdbase import exenv
from qdcore import inifile
import os
from . import test_hosting

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

def make_devsite(acronym):
    www_ini_fn = os.path.join(exenv.g.qdhost_websites_dpath, acronym+'.ini')
    with open(www_ini_fn, 'w', encoding='utf-8') as www_ini_file:
        www_ini_file.write('acronym={}\ndomain_name=www.{}.com\n'.format(acronym, acronym))
    dev_ini_fn = os.path.join(exenv.g.qdhost_devsites_dpath, acronym+'.ini')
    site_dpath = os.path.join(exenv.g.devsites_dpath, acronym)
    with open(dev_ini_fn, 'w', encoding='utf-8') as dev_ini_file:
        dev_ini_file.write('acronym={}\nsite_dpath={}\n'.format(acronym, site_dpath))
    os.mkdir(site_dpath)
    conf_dpath = os.path.join(site_dpath, 'conf')
    os.mkdir(conf_dpath)
    conf_fpath = os.path.join(conf_dpath, 'site.conf')
    with open(conf_fpath, 'w', encoding='utf-8') as site_ini_file:
        site_ini_file.write('acronym={}\nwebsite_subdir={}\n'.format(acronym, 'html'))

def test_config_vhosts(tmpdir):
    """
    Test apache2 vhost generation.

    Uses test_hosting.MakeQdev() to create test environment so
    nothing should try to write to actual system files.
    """
    test_hosting.MakeQdev(tmpdir)
    make_devsite('xx1')
    apache.config_vhosts()
