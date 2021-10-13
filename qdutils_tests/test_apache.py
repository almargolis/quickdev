from qdutils import apache

SITES_CONF_SELECTOR = '/etc/apache2/sites_available/*.conf'

conf_contents = []
conf_contents.append('# comment in column 1')
conf_contents.append('<VirtualHost *:80>')
conf_contents.append('    # indented comment')
conf_contents.append('    DocumentRoot "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs"')
conf_contents.append('    ServerName jasonmccreary.local')
conf_contents.append('    ErrorLog "/private/var/log/apache2/jasonmccreary.local-error_log"')
conf_contents.append('    CustomLog "/private/var/log/apache2/jasonmccreary.local-access_log" common')
conf_contents.append('')
conf_contents.append('    <Directory "/Users/Jason/Documents/workspace/jasonmccreary.me/htdocs">')
conf_contents.append('        AllowOverride All')
conf_contents.append('        Require all granted' )
conf_contents.append('    </Directory>')
conf_contents.append('</VirtualHost>')
conf_contents.append('Include ' + SITES_CONF_SELECTOR)

def test_apache_conf(tmpdir):
    print(tmpdir)

    fin = tmpdir.join("conf.in")
    fin.write('\n'.join(conf_contents))

    fout = tmpdir.join("conf.out")

    a = apache.ApacheConf()
    a.load(fin)
    a.write(fout)

    with open(fout) as f:
        out_lines = f.readlines()
    for ix, l in enumerate(out_lines):
        print(ix, '>>>', conf_contents[ix])
        print(ix, '<<<', l)
        assert l == conf_contents[ix]+'\n'

    includes = a.find_directives('Include', value=SITES_CONF_SELECTOR)
    assert len(includes) == 1
    assert includes[0].value == SITES_CONF_SELECTOR
