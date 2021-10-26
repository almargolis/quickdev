from qdbase import exenv

def test_symlink_file(tmpdir):
    content = 'some content'
    target_file_name = 't'
    bad_target_file_name = 'bad'
    link_file_name = 'L'
    target_file_path = tmpdir.join(target_file_name)
    link_file_path = tmpdir.join(link_file_name)
    f_targ = open(target_file_path, 'w')
    f_targ.write(content)
    f_targ.close()
    assert not exenv.make_symlink_to_file(tmpdir, link_file_name, tmpdir, bad_target_file_name)
    assert exenv.make_symlink_to_file(tmpdir, link_file_name, tmpdir, target_file_name)
    f_link = open(link_file_path)
    read_content = f_link.read()
    assert read_content == content
