import apache

conf_contents = []
conf_contents.append('<VirtualHost *:80>')
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

def test_xsynth(tmpdir):
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
