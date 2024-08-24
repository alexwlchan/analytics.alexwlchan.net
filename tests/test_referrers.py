"""
Tests for ``analytics.referrer``.
"""

import pytest

from analytics.referrers import get_normalised_referrer, QueryParams


def test_empty_referrer_data_is_none() -> None:
    """
    If there's no referrer information, there's no normalised referrer.
    """
    assert get_normalised_referrer(referrer="", query=()) is None


@pytest.mark.parametrize(
    "referrer",
    [
        "https://alexwlchan.net/",
        "https://books.alexwlchan.net/reviews/",
        "http://localhost:3000",
        "http://192.168.2.112:3000/",
        "https://192.168.0.230/",
        "https://example.net/",
        "http://roam.localhost:8000/",
        "http://75.2.60.5:6080/",
    ],
)
def test_it_drops_unhelpful_referrers(referrer: str) -> None:
    """
    If the referrer information isn't useful, it gets discarded.

    e.g. links within my own site, or other non-public sites.
    """
    assert get_normalised_referrer(referrer=referrer, query=()) is None


@pytest.mark.parametrize(
    "referrer",
    [
        # An unrecognised domain
        "https://unrecognisedomain.net",
        # A recognised domain, but with a path/query included
        "https://news.ycombinator.com/post/1234",
        "https://news.ycombinator.com/?query=123",
        # An unrecognised Android app name
        "android-app://com.unrecognised",
        # A recognised Android app name, but with a path includec
        "android-app://com.slack/path/inside",
    ],
)
def test_unrecognised_domain_is_preserved(referrer: str) -> None:
    """
    If the referrer domain isn't recognised, it's left as-is.
    """
    assert get_normalised_referrer(referrer=referrer, query=()) == referrer


@pytest.mark.parametrize(
    ["referrer", "name"],
    [
        ("http://baidu.com/", "Baidu"),
        ("https://mail.google.com/", "Email"),
        ("https://www.reddit.com/", "Reddit"),
        ("https://news.ycombinator.com/", "Hacker News"),
        ("https://t.co/", "Twitter"),
        ("android-app://com.slack/", "Slack"),
        ("https://news.hada.io/", "News aggregator (Flipboard, HN, Reddit, …)"),
        ("https://www.baidu.com/link?url=F8luxqXIkN5B7W", "Baidu"),
        ("https://github.com", "GitHub"),
    ],
)
def test_domain_with_recognised_referrer_is_mapped(referrer: str, name: str) -> None:
    """
    If I recognise the referrer domain, it's mapped to a human-readable label.
    """
    assert get_normalised_referrer(referrer=referrer, query=()) == name


@pytest.mark.parametrize(
    "referrer",
    [
        "https://cl.search.yahoo.com/",
        "https://duckduckgo.com/",
        "https://html.duckduckgo.com/",
        "https://m.sogou.com/web/searchList.jsp?s_from=hint_last",
        "https://malaysia.search.yahoo.com/",
        "https://r.search.yahoo.com/_ylt=Awr1RUZ",
        "https://search.brave.com/",
        "https://search.yahoo.com/",
        "https://www.google.co.uk/",
        "https://www.google.com/",
        "https://www.google.com/search?sca_esv=6457b5ff455aa099",
        # Yandex and its subdomains
        "https://yandex.ru/",
        "https://yandex.kz",
        "https://www.yandex.com.tr/",
        "https://www.yandex.ru/",
    ],
)
def test_maps_search_referrer(referrer: str) -> None:
    """
    If the referrer domain is a search domain, it gets mapped to my
    catchall search label.
    """
    assert (
        get_normalised_referrer(referrer=referrer, query=())
        == "Search (Google, Bing, DDG, …)"
    )


def test_spots_a_substack_email() -> None:
    """
    Links from Substack are mapped to the 'Substack' label.
    """
    result = get_normalised_referrer(
        referrer="https://substack.com/",
        query=(("utm_source", "substack"), ("utm_medium", "email")),
    )
    assert result == "Substack"


@pytest.mark.parametrize(
    ["utm_source", "name"],
    [
        ("tldrnewsletter", "TLDR Newsletter (https://tldr.tech/)"),
        ("substack", "Substack"),
    ],
)
def test_utm_source_is_mapped(utm_source: str, name: str) -> None:
    """
    If I recognise the ``utm_source``, it's mapped to a human-readable label.
    """
    query = (("utm_source", utm_source),)
    assert get_normalised_referrer(referrer="", query=query) == name


@pytest.mark.parametrize(
    ["query", "name"],
    [
        ((("fbclid", "1234"),), "Facebook"),
        ((("ref", "stachu.net"),), "https://stachu.net/"),
        ((("ref", "usepanda.com"),), "News reader (Feedly, Inoreader, …)"),
        (
            (
                ("utm_source", "stefanjudis"),
                ("utm_medium", "email"),
                ("utm_campaign", "web-weekly-121-will-there-be-an-eu-only-web-3254"),
            ),
            "https://www.stefanjudis.com/blog/web-weekly-122/",
        ),
        (
            (
                ("utm_source", "efanjudis"),
                ("utm_medium", "ail"),
                (
                    "utm_campaign",
                    "b-weekly-121-will-there-be-an-eu-only-web-3254/bP1H/giSzAQ/AQ/339bf4f3-36d0-42ba-86bf-a85c79004f4e/10/ovlYVfsLv-",
                ),
            ),
            "https://www.stefanjudis.com/blog/web-weekly-122/",
        ),
        (
            (
                ("utm_source", "stefanjudis"),
                ("utm_medium", "email"),
                ("utm_campaign", "web-weekly-130-why-is-centering-text-vertically"),
            ),
            "https://www.stefanjudis.com/blog/web-weekly-130/",
        ),
        (
            (("source", "weeklyVueNews"), ("campaign", "133")),
            "https://weekly-vue.news/issues/133",
        ),
        (
            (
                ("utm_source", "newsletter.readbalancesheet.com"),
                ("utm_medium", "newsletter"),
                ("utm_campaign", "cum-ex-conviction"),
            ),
            "https://newsletter.readbalancesheet.com/p/cum-ex-conviction",
        ),
        (
            (
                ("utm_source", "linklatte.beehiiv.com"),
                ("utm_medium", "newsletter"),
                ("utm_campaign", "169-ya-soy-el-target-demografico-del-super-bowl"),
            ),
            "https://linklatte.beehiiv.com/p/super-bowl-2024-comerciales-michael-cera-cerave-temu-song",
        ),
        (
            (
                ("utm_source", "thefutureislikepie.beehiiv.com"),
                ("utm_medium", "newsletter"),
                ("utm_campaign", "water-seeking-roots"),
            ),
            "https://thefutureislikepie.beehiiv.com/p/water-seeking-roots",
        ),
        (
            (
                ("utm_source", "alexhyett"),
                ("utm_medium", "email"),
                ("utm_campaign", "building-a-new-home-server"),
            ),
            "https://www.alexhyett.com/newsletter/building-a-new-home-server/",
        ),
        (
            (
                ("utm_source", "thisisanitsupportgroup.beehiiv.com"),
                ("utm_medium", "newsletter"),
                ("utm_campaign", "2024-it-salary-report-open"),
            ),
            "https://thisisanitsupportgroup.beehiiv.com/p/it-salary-report-open",
        ),
        ((("mc_cid", "fb89cc6974"), ("mc_eid", "164f28f2c3")), "Email newsletter"),
        (
            (
                ("utm_medium", "email"),
                ("_hsmi", "294404254"),
                ("_hsenc", "p2ANqtz"),
                ("utm_content", "294404254"),
                ("utm_source", "hs_email"),
            ),
            "Email newsletter",
        ),
        ((("ref", "cloudhiker.net"),), "News aggregator (Flipboard, HN, Reddit, …)"),
        ((("utm_source", "rss"),), "RSS subscribers"),
    ],
)
def test_query_is_mapped(query: QueryParams, name: str) -> None:
    """
    If I recognise the query parameters on the request URL, they
    get mapped to a human-readable label.
    """
    assert get_normalised_referrer(referrer="", query=query) == name


def test_an_unrecognised_utm_source_is_preserved() -> None:
    """
    If I don't recognise the ``utm_source`` parameter, it gets shown
    as a string that includes the unrecognised values.
    """
    query = (("utm_source", "unrecognised"),)
    assert (
        get_normalised_referrer(referrer="", query=query)
        == "(query=(('utm_source', 'unrecognised'),))"
    )


def test_an_unrecognised_referrer_and_utm_source_are_preserved() -> None:
    """
    If I don't recognise the referrer domain or the query parameters,
    both of them are shown in the human-readable string.
    """
    result = get_normalised_referrer(
        referrer="example.com", query=(("utm_source", "unrecognised"),)
    )
    assert result == "example.com (query=(('utm_source', 'unrecognised'),))"


@pytest.mark.parametrize(
    "query",
    [
        (("commit", None),),
        (("tag", "drawing-things"),),
        (("tag", "shell-scripting"), ("details", "open")),
        (("s", "08"),),
        (("msclkid", "cac221a3c04b11ecae4a4fc62f02d101"),),
    ],
)
def test_irrelevant_query_params_are_ignored(
    query: tuple[tuple[str, str], ...],
) -> None:
    """
    If the query parameter is irrelevant for the referrer, it's discarded.
    """
    result = get_normalised_referrer(referrer="", query=query)

    assert result is None


def test_prioritises_utm_source_over_android_app() -> None:
    """
    If the referrer domain and ``utm_source`` have conflicting information,
    pick the ``utm_source`` which is usually more specific.
    """
    result = get_normalised_referrer(
        referrer="android-app://com.google.android.gm/",
        query=(("utm_source", "tldrnewsletter"),),
    )

    assert result == "TLDR Newsletter (https://tldr.tech/)"


def test_prioritises_utm_source_over_gmail() -> None:
    """
    If the referrer domain and ``utm_source`` have conflicting information
    and one of them says it's Gmail, pick the other one.

    This occurs with email newsletters if somebody opens the link in
    the Gmail app -- the referrer domain will be Gmail, but the query
    params will point to the newsletter.
    """
    result = get_normalised_referrer(
        referrer="https://mail.google.com/", query=(("utm_source", "tldrnewsletter"),)
    )

    assert result == "TLDR Newsletter (https://tldr.tech/)"


@pytest.mark.parametrize(
    ["referrer", "normalised_referrer"],
    [
        (
            "https://newsletter.wearedevelopers.com/103?ecid=ACsprvtZ_nRI6Fp3dN99zcYrq",
            "https://newsletter.wearedevelopers.com/103",
        ),
        (
            "https://github.com/trumtomte/introduktion-git-och-github?tab=readme-ov-file",
            "https://github.com/trumtomte/introduktion-git-och-github",
        ),
        (
            "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html?utm_source=newsletter_daily&utm_campaign=20240203&utm_medium=e-mail",
            "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html",
        ),
        (
            "https://stackoverflow.blog/2024/02/09/building-a-pdf-larger-than-the-known-universe/?cb=1&force_isolation=true",
            "https://stackoverflow.blog/2024/02/09/building-a-pdf-larger-than-the-known-universe/",
        ),
        (
            "https://old.reddit.com/r/logitech/comments/pi5flh/anyone_know_how_to_fix_this_inactive_problem_with/",
            "https://www.reddit.com/r/logitech/comments/pi5flh/anyone_know_how_to_fix_this_inactive_problem_with/",
        ),
        (
            "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID",
            "https://www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.html",
        ),
    ],
)
def test_it_tidies_up_urls(referrer: str, normalised_referrer: str) -> None:
    """
    It handles all the special cases and unusual URLs which aren't
    mapped by more general rules.
    """
    assert (
        get_normalised_referrer(
            referrer=referrer,
            query=(),
        )
        == normalised_referrer
    )


@pytest.mark.parametrize(
    "referrer",
    [
        "https://github.com/alexwlchan/safari-webarchiver/?tab=readme-ov-file",
        "https://github.com/alexwlchan/safari-webarchiver?tab=readme-ov-file",
    ],
)
def test_it_normalises_github_urls(referrer: str) -> None:
    """
    If the referrer URL is the README of a GitHub repository, link to
    the root of the repo instead.
    """
    actual = get_normalised_referrer(referrer=referrer, query=())
    expected = "https://github.com/alexwlchan/safari-webarchiver"

    assert actual == expected


@pytest.mark.parametrize(
    ["referrer", "query"],
    [
        ("https://api.daily.dev/", (("ref", "dailydev"),)),
        ("https://birchtree.me/", (("ref", "birchtree.me"),)),
    ],
)
def test_it_removes_redundant_query_info(
    referrer: str, query: tuple[tuple[str, str | None], ...]
) -> None:
    """
    If the referrer header and query params both contain the same info,
    discard the query parameters.
    """
    assert get_normalised_referrer(referrer=referrer, query=query) == referrer
