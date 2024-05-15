import pytest

from analytics.referrers import get_normalised_referrer, QueryParams


def test_empty_referrer_data_is_none() -> None:
    assert get_normalised_referrer(referrer="", query=()) is None


@pytest.mark.parametrize(
    "referrer",
    [
        "https://alexwlchan.net/",
        "https://books.alexwlchan.net/reviews/",
        "http://localhost:3000",
        "http://192.168.2.112:3000/",
    ],
)
def test_it_drops_boring_referrers(referrer: str) -> None:
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
    ],
)
def test_domain_with_recognised_referrer_is_mapped(referrer: str, name: str) -> None:
    assert get_normalised_referrer(referrer=referrer, query=()) == name


@pytest.mark.parametrize(
    "referrer",
    [
        "https://duckduckgo.com/",
        "https://search.brave.com/",
        "https://www.google.co.uk/",
        "https://www.google.com/",
        "https://www.google.com/search?sca_esv=6457b5ff455aa099",
        "https://r.search.yahoo.com/_ylt=Awr1RUZ",
        "https://m.sogou.com/web/searchList.jsp?s_from=hint_last",
        "https://search.yahoo.com/",
        "https://cl.search.yahoo.com/",
        # Yandex and its subdomains
        "https://yandex.ru/",
        "https://yandex.kz",
        "https://www.yandex.com.tr/",
        "https://www.yandex.ru/",
    ],
)
def test_maps_search_referrer(referrer: str) -> None:
    assert (
        get_normalised_referrer(referrer=referrer, query=())
        == "Search (Google, Bing, DDG, …)"
    )


def test_maps_an_exact_match() -> None:
    result = get_normalised_referrer(
        referrer="https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID",
        query=(),
    )

    assert (
        result
        == "https://www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.html"
    )


def test_spots_a_substack_email() -> None:
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
    ],
)
def test_query_is_mapped(query: QueryParams, name: str) -> None:
    assert get_normalised_referrer(referrer="", query=query) == name


def test_an_unrecognised_utm_source_is_preserved() -> None:
    query = (("utm_source", "unrecognised"),)
    assert (
        get_normalised_referrer(referrer="", query=query)
        == "(query=(('utm_source', 'unrecognised'),))"
    )


def test_an_unrecognised_referrer_and_utm_source_are_preserved() -> None:
    result = get_normalised_referrer(
        referrer="example.com", query=(("utm_source", "unrecognised"),)
    )
    assert result == "example.com (query=(('utm_source', 'unrecognised'),))"


def test_prioritises_utm_source_over_android_app() -> None:
    result = get_normalised_referrer(
        referrer="android-app://com.google.android.gm/",
        query=(("utm_source", "tldrnewsletter"),),
    )

    assert result == "TLDR Newsletter (https://tldr.tech/)"


def test_prioritises_utm_source_over_gmail() -> None:
    result = get_normalised_referrer(
        referrer="https://mail.google.com/", query=(("utm_source", "tldrnewsletter"),)
    )

    assert result == "TLDR Newsletter (https://tldr.tech/)"


@pytest.mark.parametrize(
    "query",
    [
        (("tag", "drawing-things"),),
        (("tag", "shell-scripting"), ("details", "open")),
        (("s", "08"),),
    ],
)
def test_bad_queries_are_ignored(query: QueryParams) -> None:
    assert get_normalised_referrer(referrer="", query=query) is None


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
    ],
)
def test_it_tidies_up_urls(referrer: str, normalised_referrer: str) -> None:
    assert (
        get_normalised_referrer(
            referrer=referrer,
            query=(),
        )
        == normalised_referrer
    )


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
    assert get_normalised_referrer(referrer=referrer, query=query) == referrer
