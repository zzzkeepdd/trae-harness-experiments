import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import reverse, to_title_case, is_palindrome, word_count

def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse("a") == "a"

def test_to_title_case():
    assert to_title_case("hello world") == "Hello World"
    assert to_title_case("") == ""

def test_is_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("hello") == False

def test_word_count():
    result = word_count("hello world hello")
    assert result["hello"] == 2
    assert result["world"] == 1
    assert word_count("") == {}
