import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import reverse, to_title_case, is_palindrome, word_count

def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse("a") == "a"
    assert reverse("Hello World") == "dlroW olleH"
    assert reverse("123") == "321"
    assert reverse(None) == ""
    assert reverse("  spaced  ") == "  decaps  "

def test_to_title_case():
    assert to_title_case("hello world") == "Hello World"
    assert to_title_case("HELLO WORLD") == "Hello World"
    assert to_title_case("") == ""
    assert to_title_case("a") == "A"
    assert to_title_case(None) == ""
    assert to_title_case("hElLo wOrLd") == "Hello World"
    assert to_title_case("  leading space") == "  Leading Space"

def test_is_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("hello") == False
    assert is_palindrome("A man a plan a canal Panama") == True
    assert is_palindrome("") == False
    assert is_palindrome(None) == False
    assert is_palindrome("12321") == True
    assert is_palindrome("No 'x' in Nixon") == True
    assert is_palindrome("hello!@#$%^&*()") == False
    assert is_palindrome("a.") == True

def test_word_count():
    assert word_count("hello world hello") == {"hello": 2, "world": 1}
    assert word_count("") == {}
    assert word_count(None) == {}
    assert word_count("a a a a") == {"a": 4}
    assert word_count("Hello hello HELLO") == {"hello": 3}
    result = word_count("one two two three three three")
    assert result["one"] == 1
    assert result["two"] == 2
    assert result["three"] == 3
    assert word_count("hello, world! hello.") == {"hello": 2, "world": 1}
    assert word_count("123 456 123") == {"123": 2, "456": 1}
    assert word_count("a-b c_d") == {"a": 1, "b": 1, "c": 1, "d": 1}
