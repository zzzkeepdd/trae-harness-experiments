import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import save_file, allowed_file
def test_path_traversal():
    assert not allowed_file("../../../etc/passwd")
def test_num_ext():
    assert allowed_file("photo.jpg")
    assert not allowed_file("virus.exe")
def test_null_byte():
    try:
        save_file(b"evil", "/tmp", "test.php\x00.jpg")
        assert False
    except ValueError: pass
def test_save():
    import tempfile; d=tempfile.mkdtemp()
    p=save_file(b"hello", d, "test.txt")
    assert os.path.exists(p)
    assert open(p,'rb').read()==b"hello"
    shutil.rmtree(d)
