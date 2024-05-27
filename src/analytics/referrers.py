"""
This file does some aggregation and normalisation of referrer data.

e.g. I have search traffic from something like 100 different Google domains
(google.com, google.hk, google.co.uk, and so on).  I don't need to see all
those broken out in detail -- it's enough to know the traffic came from
Google.
"""

import functools
import ipaddress
import re
import sys
import typing

import hyperlink


QueryParams: typing.TypeAlias = tuple[tuple[str, str | None], ...]


@functools.cache
def get_normalised_referrer(*, referrer: str, query: QueryParams) -> str | None:
    """
    Given referrer information from the original request, convert it
    to the normalised form.
    """
    # Clean up a couple of query parameters on my /articles/ page
    if len(query) == 1 and query[0][0] == "tag":
        query = ()

    if len(query) == 2 and {q[0] for q in query} == {"tag", "details"}:
        query = ()

    if query in {
        (("force_isolation", "true"),),
        (("homescreen", "1"),),
        (("s", "03"),),
        (("s", "08"),),
        (("s", "09"),),
        (("secureweb", "Teams"),),
        (("seed", "202404"),),
        (("t", None),),
        (("trk", "article-ssr-frontend-pulse_little-text-block"),),
        (("v", "10"),),
        (("_hsmi", "294404254"),),
        (("ref", "sidebar"),),
    }:
        query = ()

    # Remove some redundant referrer info
    if referrer == "https://api.daily.dev/" and query == (("ref", "dailydev"),):
        query = ()

    if referrer == "https://birchtree.me/" and query == (("ref", "birchtree.me"),):
        query = ()

    # If we don't have any referrer or query info, we can stop here.
    if not referrer and not query:
        return None

    # Exact referrer matches.  This is for when there's no easy way to
    # do an automated cleanup, and it's easier to just tell the script
    # exactly what URL I want it to match.
    exact_matches = invert_dict(
        {
            "https://boingboing.net/": [
                "https://bbs.boingboing.net/",
                "https://boingboing.net",
            ],
            "https://www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.html": [
                "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID",
                "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_js_v=a6&amp_gsa=1",
                "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_js_v=0.1&usqp=mq331AQIUAKwASCAAgM%3D",
            ],
            "https://b.hatena.ne.jp/": [
                "https://b.hatena.ne.jp/entrylist/fun/%E3%81%93%E3%82%8C%E3%81%AF%E3%81%99%E3%81%94%E3%81%84",
                "https://b.hatena.ne.jp/entrylist/it/AI%E3%83%BB%E6%A9%9F%E6%A2%B0%E5%AD%A6%E7%BF%92",
                "https://b.hatena.ne.jp/entrylist/it?page=2"
                "https://b.hatena.ne.jp/entrylist/it?page=3",
                "https://b.hatena.ne.jp/entrylist/it?page=10",
                "https://b.hatena.ne.jp/hotentry/fun",
                "https://b.hatena.ne.jp/hotentry/it",
                "https://hatena.ne.jp/",
                "https://b.hatena.ne.jp/?iosapp=1",
                "https://b.hatena.ne.jp/entrylist/all?page=8",
                "https://b.hatena.ne.jp/entrylist/fun/%E3%81%93%E3%82%8C%E3%81%AF%E3%81%99%E3%81%94%E3%81%84?page=6",
                "https://b.hatena.ne.jp/entrylist/fun/%E3%83%8D%E3%82%BF",
            ],
            "https://www.golem.de/": [
                "https://backend.golem.de/",
                "https://www-golem-de.cdn.ampproject.org/",
            ],
            "http://www.daemonology.net/": [
                "https://www.daemonology.net/",
            ],
            "https://slashdot.org/": [
                "https://slashdot.org/?page=1",
            ],
            "https://slashdot.org/story/24/02/02/1534229/making-a-pdf-thats-larger-than-germany": [
                "https://it.slashdot.org/story/24/02/02/1534229/making-a-pdf-thats-larger-than-germany?utm_source=rss1.0mainlinkanon&utm_medium=feed",
                "https://m.slashdot.org/story/424446",
            ],
            "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html": [
                "https://www.numerama.com/?p=1623224&preview=true",
            ],
            "https://old.reddit.com/": [
                "https://old.reddit.com/?count=250&after=t3_1agnhgf",
                "https://old.reddit.com/?count=75&after=t3_1ag8jtu",
            ],
            # This website seems to be dual-published in Germany/Austria,
            # and the Austrian site is more popular.
            "https://www.derstandard.at/": [
                "https://www.derstandard.de/",
            ],
        }
    )

    try:
        referrer = exact_matches[referrer]
    except KeyError:
        pass

    # Now use the query string to see if it contains referrer info.
    query_referrer = _get_referrer_from_query(query)

    if query_referrer is not None:
        return query_referrer

    # Note: this branch is somewhat theoretical.  I've never had a referrer
    # which didn't parse as a URL, but I don't want the tracking pixel
    # not to save just because it got weird data.
    try:
        u = parse_url(referrer)
    except Exception as e:  # pragma: no cover
        print(f"Unable to parse {referrer}: {e}", file=sys.stderr)
        return referrer

    # Ignore any requests coming from local IP addresses; I can't do
    # anything with this.
    if u.host == "localhost":
        return None

    try:
        if ipaddress.ip_address(u.host).is_private:
            return None
    except ValueError:
        pass

    # Ignore any referrer data from my own domain -- I'm more interested
    # in who's linking to me than how people are moving about my site.
    if u.host in {
        "alexwlchan.net",
        "analytics.alexwlchan.net",
        "books.alexwlchan.net",
        "til.alexwlchan.net",
    }:
        return None

    # Do any normalisation of referrer URLs
    if u.host == "github.com":
        u = u.remove("tab")

    if u.host == "newsletter.wearedevelopers.com":
        for param_name, _ in list(u.query):
            u = u.remove(param_name)

    if u.host == "old.reddit.com":
        u = u.replace(host="www.reddit.com")

    if u.host == "www.numerama.com":
        u = u.remove("utm_source")
        u = u.remove("utm_param")
        u = u.remove("utm_medium")
        u = u.remove("utm_campaign")

    if u.host == "stackoverflow.blog":
        u = u.remove("cb")
        u = u.remove("force_isolation")

    # Now use the referrer header to see what, if anything, we learn.
    header_referrer = _get_referrer_from_header(u)

    if header_referrer is not None:
        return header_referrer

    # Now look for referrers which have an Android user agent string.
    #
    # I don't know what these are, but I'm guessing they're apps on
    # Android devices, or browsers running in-app.
    android_referrer = _get_referrer_from_android_app_name(u)

    if android_referrer is not None:
        return android_referrer

    # If we can't map it, return the original referer data, and include
    # the UTM source so I know if there are more values I should be mapping.
    if referrer and query:
        return f"{u.to_text()} (query={query})"
    elif referrer:
        return u.to_text()
    elif query:
        return f"(query={query})"
    else:  # pragma: no cover
        assert 0, "Unreachable"


@functools.cache
def _get_referrer_from_header(u: hyperlink.DecodedURL) -> str | None:
    """
    Given the value of the Referer header, look to see if that tells
    us the source.
    """
    # Now look for referrers which match a hostname, and don't send any
    # path or query information.  This usually suggests the originating
    # domain has a Referer-Policy of `origin`.
    #
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
    hostname_lookup = invert_dict(
        {
            "Baidu": ["baidu.com", "m.baidu.com"],
            "Bluesky": ["bsky.app", "staging.bsky.app"],
            "Email": [
                "deref-gmx.com",
                "e.mail.ru",
                "email.t-online.de",
                "mail.google.com",
                "securemail.tulsaconnect.com",
                "webmail.mail.eu-west-1.awsapps.com",
                "webmail.seriot.ch",
                "webmail.gpntb.ru",
            ],
            "Email newsletter": [
                "app.mailbrew.com",
                "buttondown.email",
                "mailchi.mp",
                "us1.campaign-archive.com",
            ],
            "Evernote": ["www.evernote.com"],
            "GitHub": ["gist.github.com", "github.com"],
            "Facebook": ["l.facebook.com", "m.facebook.com", "lm.facebook.com"],
            "Fark": ["www.fark.com", "m.fark.com"],
            "Financial Times": ["www.ft.com"],
            "Hacker News": [
                "news.ycombinator.com",
                #
                # Whenever I get linked on Hacker News, the same URL ends
                # up on dozens of domains that just scrape HN links.
                # I don't care about them individually, but I do care about
                # the aggregate effect of HN over other aggregation sites,
                # so throw them all into one bucket.
                "hacker-news.news",
                "hacker.news",
                "hackerdaily.io",
                "hackernews.betacat.io",
                "hackerweb.app",
                "hackyournews.com",
                "hckrnews.com",
                "hn-news.cdcde.com",
                "hn.algolia.com",
                "hn.buzzing.cc",
                "hn.cotyhamilton.com",
                "hnfrontpage.pages.dev",
                "hn.luap.info",
                "hn.premii.com",
                "hn.svelte.dev",
                "hnapp.com",
                "hntoplinks.com",
                "news-ycombinator-com.translate.goog",
                "sveltekit-hacker-news-pwa.vercel.app",
                "www.hackernewz.com",
                "www.hndigest.com",
                "www.hntoplinks.com",
            ],
            "Instagram": ["instagram.com", "l.instagram.com"],
            "Kottke": ["kottke.org", "www.kottke.org"],
            "LinkedIn": ["www.linkedin.com", "lnkd.in"],
            "Linkhut": ["ln.ht"],
            "Lobsters": ["lobste.rs"],
            "Mastodon": [
                "federation.network",
                "fedia.social",
                "fediverse.fun",
                "hachyderm.io",
            ],
            "MetaFilter": ["www.metafilter.com"],
            "MSN": ["www.msn.com"],
            "News aggregator (Flipboard, HN, Reddit, …)": [
                "boredreading.com",
                "devurls.com",
                "flipboard.com",
                "freshnews.org",
                "habr.com",
                "hackurls.com",
                "ios.feeddler.com",
                "narenohatebu.jp",
                "news.hada.io",
                "news.social-protocols.org",
                "newz-mixer.vercel.app",
                "now.hackertab.dev",
                "old.thenews.im",
                "readspike.com",
                "refind.com",
                "serializer.io",
                "spike.news",
                "techurls.com",
                "tuxurls.com",
                "upstract.com",
                "www.freshnews.org",
            ],
            "News reader (Feedly, Inoreader, …)": [
                "app.usepanda.com",
                "base.usepanda.com",
                "bazqux.com",
                "dm.hn",
                "feedbin.com",
                "feeder.co",
                "feedly.com",
                "jp.inoreader.com",
                "newsblur.com",
                "newsletters.feedbinusercontent.com",
                "read.readwise.io",
                "read.squidapp.co",
                "theoldreader.com",
                "www.inoreader.com",
                "www.newsblur.com",
                "www.rssheap.com",
            ],
            "Pinboard": ["pinboard.in", "m.pinboard.in", "www.pinboard.in"],
            "Pinterest": ["www.pinterest.com"],
            "Search (Google, Bing, DDG, …)": [
                "au.search.yahoo.com",
                "bing.com",
                "cn.bing.com",
                "duckduckgo.com",
                "edgeservices.bing.com",
                "iframe-yang.yandex",
                "lens.google.com",
                "online-mobilesearch.com",
                "presearch.com",
                "search.brave.com",
                "search.lilo.org",
                "searchmysite.net",
                "sogou.com",
                "www.bing.com",
                "www.ecosia.org",
                "www.qwant.com",
                "www.startpage.com",
                "ya.ru",  # I think this is to do with Yandex?
                "yep.com",
                "you.com",
            ],
            "Slashdot": ["slashdot.org", "m.slashdot.org", "it.slashdot.org"],
            "Snapchat": ["www.snapchat.com"],
            "Spotify": ["open.spotify.com"],
            "Substack": ["substack.com"],
            "Reddit": [
                "old.reddit.com",
                "out.reddit.com",
                "new.reddit.com",
                "www.reddit.com",
            ],
            "Telegram": ["web.telegram.org", "weba.telegram.org"],
            "Threads": ["l.threads.net"],
            "Tumblr": ["www.tumblr.com"],
            "Twitter": ["t.co"],
            "Weibo": ["weibo.cn"],
            "Wikimedia Commons": ["commons.wikimedia.org", "commons.m.wikimedia.org"],
            "YouTube": ["www.youtube.com"],
            "Zenodo": ["zenodo.org"],
            #
            # I get a bunch of links from Office-related domains.  I don't
            # really know what they are; I guess they're corporate Intranets?
            # Throw them all into one bucket for now.
            "Microsoft Office": [
                "res.cdn.office.net",
                "statics.gov.teams.microsoft.us",
                "statics.teams.cdn.office.net",
                "teams.microsoft.com",
                "ukc-word-edit.officeapps.live.com",
                "word-edit.officeapps.live.com",
            ],
        }
    )

    if u.scheme in {"http", "https"} and is_origin_referrer(u):
        try:
            return hostname_lookup[u.host]
        except KeyError:
            pass

        # e.g. www.google.com, www.google.co.uk
        if re.match(r"^www\.google\.[a-z]{1,3}(\.[a-z]{1,3})?$", u.host):
            return "Search (Google, Bing, DDG, …)"

        # e.g. yandex.ru, yandex.com.tr, www.yandex.ru
        if re.match(r"^(www\.)?yandex\.[a-z]{1,3}(\.[a-z]{1,3})?$", u.host):
            return "Search (Google, Bing, DDG, …)"

        # e.g. cl.search.yahoo.com, it.search.yahoo.com
        if re.match(r"^([a-z]{2}\.)?search\.yahoo.com$", u.host):
            return "Search (Google, Bing, DDG, …)"

    if u.scheme in {"http", "https"} and u.host in {
        "www.google.com",
        "r.search.yahoo.com",
        "m.sogou.com",
    }:
        return "Search (Google, Bing, DDG, …)"

    if u.scheme in {"http", "https"} and u.host == "www.baidu.com":
        return "Baidu"

    return None


class ReferrerMatch(typing.TypedDict):
    referrer: str
    params: dict[str, str]


def _get_referrer_from_query(query: QueryParams) -> str | None:
    """
    Given the query string appended to the URL, look to see if it tells
    us the source, e.g. through UTM tracking parameters.
    """
    if not query:
        return None

    # Look for a ``utm_source`` parameter in the query string.
    #
    # These aren't URLs but I can map the most common examples in my data.
    utm_source_lookup = invert_dict(
        {
            "Email newsletter": ["newsletter"],
            "Hacker News": ["hackernewsletter", "hnblogs.substack.com"],
            "Mastodon": ["mastodon"],
            "News aggregator (Flipboard, HN, Reddit, …)": ["cloudhiker.net"],
            "Pocket": ["pocket_mylist", "pocket_reader", "pocket_saves"],
            "RSS subscribers": ["rss"],
            "Substack": ["substack"],
            "TLDR Newsletter (https://tldr.tech/)": ["tldrnewsletter", "tldrwebdev"],
        }
    )

    query_dict = {k: v for k, v in query}

    utm_source = query_dict.get("utm_source", "")

    try:
        return utm_source_lookup[utm_source]  # type: ignore
    except KeyError:
        pass

    # Look for a ``utm_source`` and ``utm_campaign`` parameters in the
    # query string.
    #
    # These aren't URLs but I can map the common examples.
    matches: list[ReferrerMatch] = [
        {
            "referrer": "News reader (Feedly, Inoreader, …)",
            "params": {"ref": "usepanda.com"},
        },
        {
            "referrer": "News aggregator (Flipboard, HN, Reddit, …)",
            "params": {"ref": "cloudhiker.net"},
        },
        {
            "referrer": "https://www.stefanjudis.com/blog/web-weekly-122/",
            "params": {
                "utm_source": "stefanjudis",
                "utm_campaign": "web-weekly-121-will-there-be-an-eu-only-web-3254",
            },
        },
        {
            "referrer": "https://www.stefanjudis.com/blog/web-weekly-130/",
            "params": {
                "utm_source": "stefanjudis",
                "utm_campaign": "web-weekly-130-why-is-centering-text-vertically",
            },
        },
        {
            "referrer": "https://weekly-vue.news/issues/133",
            "params": {
                "source": "weeklyVueNews",
                "campaign": "133",
            },
        },
        {
            "referrer": "https://newsletter.readbalancesheet.com/p/cum-ex-conviction",
            "params": {
                "utm_source": "newsletter.readbalancesheet.com",
                "utm_campaign": "cum-ex-conviction",
            },
        },
        {
            "referrer": "https://linklatte.beehiiv.com/p/super-bowl-2024-comerciales-michael-cera-cerave-temu-song",
            "params": {
                "utm_source": "linklatte.beehiiv.com",
                "utm_campaign": "169-ya-soy-el-target-demografico-del-super-bowl",
            },
        },
        {
            "referrer": "https://thefutureislikepie.beehiiv.com/p/water-seeking-roots",
            "params": {
                "utm_source": "thefutureislikepie.beehiiv.com",
                "utm_campaign": "water-seeking-roots",
            },
        },
        {
            "referrer": "https://www.alexhyett.com/newsletter/building-a-new-home-server/",
            "params": {
                "utm_source": "alexhyett",
                "utm_campaign": "building-a-new-home-server",
            },
        },
        {"referrer": "https://stachu.net/", "params": {"ref": "stachu.net"}},
        {
            "referrer": "https://thisisanitsupportgroup.beehiiv.com/p/it-salary-report-open",
            "params": {
                "utm_source": "thisisanitsupportgroup.beehiiv.com",
                "utm_campaign": "2024-it-salary-report-open",
            },
        },
        {
            "referrer": "https://jekyll-themes.com",
            "params": {"ref": "jekyll-themes.com"},
        },
        {
            "referrer": "https://weeklyfoo.com",
            "params": {"utm_source": "weeklyfoo", "utm_campaign": "weeklyfoo"},
        },
        {
            "referrer": "https://weeklyfoo.com/foos/foo-032/",
            "params": {"utm_source": "weeklyfoo", "utm_campaign": "weeklyfoo-32"},
        },
    ]

    for m in matches:
        if all(query_dict.get(k) == v for k, v in m["params"].items()):
            return m["referrer"]

    # fbclid is a tracking parameter added to outbound links on Facebook.
    #
    # I gets lots of different values for it and I'm not sure what, if
    # anything, I can do with them, but I also don't care much -- it's
    # enough to know Facebook is the source.
    if query_dict.keys() == {"fbclid"}:
        return "Facebook"

    # mc_cid and mc_eid are tracking parameters added by Mailchimp
    if query_dict.keys() == {"mc_cid", "mc_eid"}:
        return "Email newsletter"

    # Look for any other useful query string values which might help us.
    if (
        utm_source == "efanjudis"
        and "weekly-121-will-there-be-an-eu-only-web-3254"
        in (query_dict.get("utm_campaign") or "")
    ):
        return "https://www.stefanjudis.com/blog/web-weekly-122/"

    # hs_email stands for HubSpot.  If we get here and we don't have any
    # more useful info, toss them all into one bucket.
    if (
        query_dict.get("utm_source") == "hs_email"
        and query_dict.keys()
        == {"utm_medium", "_hsmi", "_hsenc", "utm_content", "utm_source"}
        and query_dict.get("utm_content").isnumeric()  # type: ignore
    ):
        return "Email newsletter"

    return None


def _get_referrer_from_android_app_name(u: hyperlink.DecodedURL) -> str | None:
    """
    Given a parsed referrer URL, look to see if it's the name of an
    Android app.
    """
    if u.scheme != "android-app" or not is_origin_referrer(u):
        return None

    android_name_lookup = invert_dict(
        {
            "Financial Times": ["com.ft.news"],
            "Hacker News": [
                "io.github.hidroh.materialistic",
                "com.stefandekanski.hackernews.free",
                "com.jiaqifeng.hacki",
            ],
            "Lemmy": ["io.syncapps.lemmy_sync"],
            "LinkedIn": ["com.linkedin.android"],
            "Pinterest": ["com.pinterest"],
            "Search (Google, Bing, DDG, …)": [
                "com.google.android.gm",
                "com.google.android.googlequicksearchbox",
            ],
            "Slack": ["com.slack"],
            "Telegram": [
                "app.nicegram",
                "org.telegram.biftogram",
                "org.telegram.messenger",
                "org.telegram.messenger.web",
                "org.telegram.plus",
            ],
            "Twitter": ["com.twitter.android"],
        }
    )

    try:
        return android_name_lookup[u.host]
    except KeyError:
        return None


def invert_dict(d: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}

    for key, values in d.items():
        for v in values:
            result[v] = key

    return result


def is_origin_referrer(u: hyperlink.DecodedURL) -> bool:
    """
    Returns True if this URL only contains the origin, and no path
    or query information.
    """
    has_empty_path = u.path == () or u.path == ("",)
    has_empty_query = bool(not u.query)

    return has_empty_path and has_empty_query


@functools.cache
def parse_url(text: str) -> hyperlink.DecodedURL:
    """
    Parse a ``str`` as a ``hyperlink.DecodedURL``.

    This is wrapped in a function so it can be cached; this speeds up
    the performance of the ``update_normalised_referrer.py`` script by
    about a third.
    """
    return hyperlink.DecodedURL.from_text(text)
