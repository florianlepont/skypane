"""Unit tests for i18n_ids.slug_for()/ids_for_area() — the deterministic
English-to-slug rule shared by the i18n stable-ID migration effort.
"""
import i18n_ids


def test_slug_for_home():
    assert i18n_ids.slug_for("Home") == "home"


def test_slug_for_just_now():
    assert i18n_ids.slug_for("just now") == "just_now"


def test_slug_for_percent_s_ago_drops_the_placeholder_letter():
    # "%s ago": the placeholder contributes nothing beyond the "_"
    # separator — the trailing "s" must not survive into the slug.
    assert i18n_ids.slug_for("%s ago") == "ago"


def test_slug_for_truncates_at_an_underscore_boundary():
    long_english = "a " * 40 + "final word"
    slug = i18n_ids.slug_for(long_english)
    assert len(slug) <= i18n_ids.MAX_SLUG_LENGTH
    assert not slug.endswith("_")


def test_ids_for_area_resolves_a_slug_collision_in_source_order():
    # "Hello!" and "Hello?" both slug to "hello" — the later entry gets
    # "_2", in the order the two strings were passed.
    ids = i18n_ids.ids_for_area("test", ["Hello!", "Hello?", "Home"])
    assert ids == ["test.hello", "test.hello_2", "test.home"]
