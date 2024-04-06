import hyperlink
import pytest

from referrers import has_empty_path, normalise_referrer


@pytest.mark.parametrize("url", ["android-app://org.telegram.messenger.web/"])
def test_has_empty_path_is_true(url: str) -> None:
    u = hyperlink.DecodedURL.from_text(url)
    assert has_empty_path(u)


@pytest.mark.parametrize(
    "referrer",
    [
        "https://www.google.pl/",
        "https://www.google.de/",
        "android-app://com.google.android.googlequicksearchbox/",
        "https://in.search.yahoo.com/",
        "https://cn.bing.com/",
        "https://bing.com/",
    ],
)
def test_referrer_is_search(referrer):
    assert normalise_referrer(referrer) == "Search (Google, Bing, DDG, …)"


@pytest.mark.parametrize(
    ["referrer", "expected"],
    [
        ("https://l.facebook.com/", "Facebook"),
        ("https://alexwlchan.net/2014/part-ia-exams/", None),
        ("https://t.co/", "Twitter"),
        (None, None),
        ("https://shkspr.mobi/", "https://shkspr.mobi/"),
        (
            "https://github.com/alexwlchan?tab=repositories",
            "https://github.com/alexwlchan",
        ),
        ("https://github.com/alexwlchan", "https://github.com/alexwlchan"),
        ("https://news.ycombinator.com", "Hacker News"),
        ("android-app://io.github.hidroh.materialistic/", "Hacker News"),
        ("https://www.inoreader.com/", "RSS reader (Feedly, Inoreader, …)"),
        ("https://old.reddit.com/?count=75&after=t3_1ag8jtu", "Reddit"),
        (
            "https://old.reddit.com/r/ForAllMankindTV/comments/1ag7bke/i_was_rewatching_season_1/",
            "https://old.reddit.com/r/ForAllMankindTV/comments/1ag7bke/i_was_rewatching_season_1/",
        ),
        (
            "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html?utm_source=newsletter_daily&utm_campaign=20240203&utm_medium=e-mail",
            "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html",
        ),
        ("android-app://org.telegram.messenger.web/", "Telegram"),
        ("https://m.baidu.com/", "Baidu"),
    ],
)
def test_normalise_referrer(referrer, expected):
    assert normalise_referrer(referrer) == expected
