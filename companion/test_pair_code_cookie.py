"""The cookie that keeps a refused pairing code, and the optional frame name
typed with it, for the next showing of the form."""
from companion import pair_code_cookie as cookie

KEY = "0123456789abcdef"
OTHER_KEY = "fedcba9876543210"


def _sent(set_cookie):
    """The `Cookie` request header a browser would send back."""
    return set_cookie.split(";", 1)[0]


def test_a_name_round_trips_with_the_code():
    header = cookie.keep_header(KEY, "abcd-2345", "Cuisine d’Orly")
    assert cookie.take_with_name(_sent(header), KEY)[:2] == ("ABCD-2345", "Cuisine d’Orly")


def test_the_name_is_stored_as_inert_hex_not_as_text():
    value = _sent(cookie.keep_header(KEY, "ABCD2345", '"><b>x</b>; a=b'))
    assert set(value.split("=", 1)[1].split(".", 2)[2]) <= set("0123456789abcdef")
    assert cookie.take_with_name(value, KEY)[1] == '"><b>x</b>; a=b'


def test_a_name_the_rename_rules_refuse_is_not_stored():
    for bad in ("x" * 41, "tab\there"[:4] + "\x07", "   "):
        header = cookie.keep_header(KEY, "ABCD2345", bad)
        assert cookie.take_with_name(_sent(header), KEY)[:2] == ("ABCD2345", "")


def test_the_value_stays_short_enough_for_a_cookie():
    header = cookie.keep_header(KEY, "ABCD2345", "é" * 40)
    assert len(header) < 1000


def test_another_sessions_cookie_gives_neither_code_nor_name():
    header = cookie.keep_header(KEY, "ABCD2345", "Kitchen")
    code, name, clear = cookie.take_with_name(_sent(header), OTHER_KEY)
    assert (code, name) == ("", "") and clear is not None


def test_a_tampered_value_gives_no_name():
    prefix = "%s=%s.ABCD2345." % (cookie.COOKIE_NAME, KEY)
    for tail in ("zz", "4b6", "ff", "c3"):
        assert cookie.take_with_name(prefix + tail, KEY)[1] == ""


def test_the_code_only_behaviour_is_unchanged():
    header = cookie.keep_header(KEY, "abcd-2345")
    assert cookie.take(_sent(header), KEY)[0] == "ABCD-2345"
    assert cookie.take_with_name(_sent(header), KEY)[:2] == ("ABCD-2345", "")
    code, clear = cookie.take(None, KEY)
    assert code == "" and clear is None
    assert "HttpOnly" in header and "SameSite=Strict" in header
    assert "Path=/pair-frame" in header and "Max-Age=120" in header


def test_the_end_of_the_cookie_is_returned_once_it_was_sent():
    header = cookie.keep_header(KEY, "ABCD2345", "Kitchen")
    assert "Max-Age=0" in cookie.take_with_name(_sent(header), KEY)[2]
