import functools
import sys

import hyperlink


def invert_dict(d: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}

    for key, values in d.items():
        for v in values:
            result[v] = key

    return result


def has_empty_path(u: hyperlink.DecodedURL) -> bool:
    return u.path == () or u.path == ("",)


def _is_search_referrer(u: hyperlink.DecodedURL) -> bool:
    """
    Returns True if this referrer is from a search engine, False otherwise.
    """
    if u.host.startswith(("www.google.", "www.yandex.", "yandex.")):
        return True

    if u.host.endswith((".search.yahoo.com", ".bing.com")):
        return True

    if u.host in {
        "baidu.com",
        "duckduckgo.com",
        "search.brave.com",
        "search.yahoo.com",
        "searchmysite.net",
        "bing.com",
        "onlinewebsearches.co",
        "www.ecosia.org",
        "www.perplexity.ai",
        "www.qwant.com",
        "www.startpage.com",
        "ya.ru",
        "iframe-yang.yandex",
        "m.sogou.com",
        "online-mobilesearch.com",
        "search.lilo.org",
        "oceanhero.today",
    }:
        return True

    if u.scheme == "android-app" and u.host in {
        "com.google.android.googlequicksearchbox",
        "com.google.android.gm",
    }:
        return True

    return False


def _is_rss_reader(u: hyperlink.DecodedURL) -> bool:
    """
    Returns true if this referrer looks like somebody's RSS reader.
    """
    if has_empty_path(u) and u.host in {
        "www.inoreader.com",
        "rss.cloudier.com",
        "jp.inoreader.com",
        "feedly.com",
        "app.usepanda.com",
        "api.daily.dev",
        "base.usepanda.com",
        "www.newsblur.com",
        "newsblur.com",
        "ios.feeddler.com",
        "theoldreader.com",
        "feedbin.com",
        "newsletters.feedbinusercontent.com",
    }:
        return True

    if (
        has_empty_path(u)
        and u.scheme == "android-app"
        and u.host
        in {
            "org.fox.ttrss",
        }
    ):
        return True

    return False


def _is_news_aggregator(u: hyperlink.DecodedURL) -> bool:
    if has_empty_path(u) and u.host in {
        "hackurls.com",
        "devurls.com",
        "serializer.io",
        "www.buzzing.cc",
        "progscrape.com",
        "brutalist.report",
        "news.hada.io",
        "feeder.co",
        "techurls.com",
        "old.thenews.im",
        "readspike.com",
        "flipboard.com",
        "www.hntoplinks.com",
        "now.hackertab.dev",
        "newz-mixer.vercel.app",
        "hn.cr4xy.dev",
        "hn.kickflip.workers.dev",
        "hnpwa-vanilla.firebaseapp.com",
        "hnpwa.dev.muze.nl",
        "b.hatena.ne.jp",
        "spike.news",
        "read.squidapp.co",
        "daily.sdinet.de",
        "christian.rubbert.de",
        "apollo.fractum.nl",
        "app.mailbrew.com",
        "www.freshnews.org",
    }:
        return True

    if u.host == "b.hatena.ne.jp" and u.path == ("hotentry", "it"):
        return True

    if u.host == "b.hatena.ne.jp" and u.path == ("hotentry", "fun"):
        return True

    if u.host == "b.hatena.ne.jp" and u.path == ("entrylist", "it"):
        return True

    return False


@functools.lru_cache
def normalise_referrer(referrer: str | None) -> str | None:
    """
    If possible, create a "normalised form" of a referrer.
    """
    if referrer is None:
        return None

    hardcoded_lookup = {
        "Lemmy": [
            "https://lemmy.blahaj.zone/?dataType=Post&listingType=All&page=3&sort=Active",
        ],
        "https://b.hatena.ne.jp/": [
            "https://b.hatena.ne.jp/?iosapp=1",
            "https://b.hatena.ne.jp/entrylist/it?page=2",
            "https://b.hatena.ne.jp/entrylist/it?page=3",
            "https://b.hatena.ne.jp/entrylist/all?page=8",
            "https://b.hatena.ne.jp/entrylist/fun/%E3%81%93%E3%82%8C%E3%81%AF%E3%81%99%E3%81%94%E3%81%84",
            "https://b.hatena.ne.jp/entrylist/it/AI%E3%83%BB%E6%A9%9F%E6%A2%B0%E5%AD%A6%E7%BF%92",
            "https://hatena.ne.jp/",
        ],
        "https://boingboing.net/": [
            "https://boingboing.net",
            "https://boingboing-net.cdn.ampproject.org/",
        ],
        "https://boingboing.net/2024/02/01/a-pdf-the-size-of-germany-or-the-universe.html": [
            "https://boingboing-net.cdn.ampproject.org/v/s/boingboing.net/2024/02/01/a-pdf-the-size-of-germany-or-the-universe.html/amp?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID",
            "https://boingboing-net.cdn.ampproject.org/v/s/boingboing.net/2024/02/01/a-pdf-the-size-of-germany-or-the-universe.html/amp?amp_gsa=1&amp_js_v=a9&usqp=mq331AQIUAKwASCAAgM%3D",
        ],
        "https://slashdot.org/story/24/02/02/1534229/making-a-pdf-thats-larger-than-germany": [
            "https://slashdot.org/story/424446",
            "https://m.slashdot.org/story/424446",
            "https://it.slashdot.org/story/424446",
        ],
        "https://www.fark.com/": ["https://m.fark.com/", "https://fark.com/"],
        "https://www.golem.de/": [
            "https://www-golem-de.cdn.ampproject.org/",
            "https://backend.golem.de/",
        ],
        "https://www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.html": [
            "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID",
            "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_js_v=a6&amp_gsa=1",
            "https://www-golem-de.cdn.ampproject.org/v/s/www.golem.de/news/spassprojekt-mann-erstellt-pdf-dokument-in-der-groesse-der-welt-2402-181844.amp.html?amp_js_v=0.1&usqp=mq331AQIUAKwASCAAgM%3D",
        ],
        "https://www.meneame.net/": [
            "https://old.meneame.net/queue",
            "https://old.meneame.net/",
            "https://www.meneame.net/queue",
        ],
        "https://www.numerama.com/politique/1623224-un-fichier-pdf-grand-comme-lunivers-cest-possible.html": [
            "https://www.numerama.com/?p=1623224&preview=true"
        ],
    }

    hardcoded_matches = invert_dict(hardcoded_lookup)

    try:
        return hardcoded_matches[referrer]
    except KeyError:
        pass

    try:
        u = hyperlink.DecodedURL.from_text(referrer)
    except Exception as e:
        print(f"Unable to parse {referrer}: {e}", file=sys.stderr)
        return None

    if _is_search_referrer(u):
        return "Search (Google, Bing, DDG, …)"

    if u.host in {
        "127.0.0.1",
        "alexwlchan.net",
        "analytics.alexwlchan.net",
        "books.alexwlchan.net",
        "localhost",
        "til.alexwlchan.net",
        "translate.google.co.jp",
    }:
        return None

    hostname_lookup = {
        "Baidu": ["m.baidu.com"],
        "Bluesky": ["bsky.app", "staging.bsky.app"],
        "ChatGPT": ["chat.openai.com"],
        "Email": [
            "email.t-online.de",
            "mailchi.mp",
            "mail.missiveapp.com",
            "mail.yahoo.co.jp",
            "mail.zoho.com",
            "url.emailprotection.link",
            "url11.mailanyone.net",
            "us1-campaign--archive-com.translate.goog",
            "us1.campaign-archive.com",
            "us9.admin.mailchimp.com",
            "webmail.nikola.com",
            "webmail.seriot.ch",
            "webmail.gpntb.ru",
            "webmail.mail.eu-west-1.awsapps.com",
        ],
        "Facebook": ["facebook.com", "l.messenger.com"],
        "GitHub": ["gist.github.com", "github.com"],
        "Gmail": ["mail.google.com"],
        "Hacker News": [
            "news.ycombinator.com",
            "hckrnews.com",
            "y-combinator-news-trends.vercel.app",
            "sveltekit-hacker-news-pwa.vercel.app",
            "remix-clone-hacker-news.flameddd1.workers.dev",
            "news-ycombinator-com.translate.goog",
            "modernorange.io",
            "hn.cxjs.io",
            "hn.algolia.com",
            "hackyournews.com",
            "hackerlive.net",
            "hn.luap.info",
            "hnfrontpage.pages.dev",
            "www.hackernewz.com",
            "hn.cotyhamilton.com",
            "hn.buzzing.cc",
            "hacker-news.news",
            "hn.svelte.dev",
            "hackernews.betacat.io",
            "hn.premii.com",
            "hackerweb.app",
            "hacc.foo",
            "mono-hackernews.deno.dev",
            "quiethn.gyttja.com",
            "hacker.news",
            "hntoplinks.com",
            "www.hntoplinks.com",
            "now.hackertab.dev",
            "news.social-protocols.org",
            "ycnews.tech",
            "hnapp.com",
            "www.hndigest.com",
            "hn.nuxt.space",
            "hn-news.cdcde.com",
            "www.hakaran.com",
            "hackerdaily.io",
            "blogs.hn",
        ],
        "Instagram": ["instagram.com", "l.instagram.com"],
        "Instapaper": ["www.instapaper.com"],
        "Kottke": ["kottke.org", "www.kottke.org"],
        "Lemmy": ["lemmy.dbzer0.com", "lemmy.packitsolutions.net"],
        "LinkedIn": ["www.linkedin.com", "lnkd.in"],
        "Linkhut": ["ln.ht"],
        "Lobsters": ["lobste.rs"],
        "MSN": ["www.msn.com"],
        "MetaFilter": ["www.metafilter.com"],
        "Microsoft Teams": ["teams.microsoft.com"],
        "Pinboard": ["pinboard.in", "m.pinboard.in", "www.pinboard.in"],
        "Pinterest": ["www.pinterest.de"],
        "PyPI": ["pypi.org"],
        "Reddit": [
            "reddit.com",
            "www.reddit.com",
            "old.reddit.com",
            "out.reddit.com",
            "www.reddit.com",
        ],
        "Skype": ["web.skype.com"],
        "Slashdot": ["slashdot.org", "m.slashdot.org", "it.slashdot.org"],
        "Substack": ["link.sbstck.com", "substack.com"],
        "Telegram": ["web.telegram.org", "weba.telegram.org"],
        "Tencent": ["t.cn"],
        "The Financial Times": ["www.ft.com"],
        "Threads": ["l.threads.net"],
        "Tumblr": ["www.tumblr.com"],
        "Twitter": ["t.co", "twitter.com", "nitter.moomoo.me", "nitter.holo-mix.com"],
        "Weibo": ["weibo.cn"],
        "WordPress": ["wordpress.com"],
        "YouTube": ["www.youtube.com"],
    }

    hostname_matches = invert_dict(hostname_lookup)

    if has_empty_path(u):
        try:
            return hostname_matches[u.host]
        except KeyError:
            pass

    android_app_id_lookup = {
        "Hacker News": [
            "io.github.hidroh.materialistic",
            "com.jiaqifeng.hacki",
            "com.stefandekanski.hackernews.free",
        ],
        "Lemmy": ["io.syncapps.lemmy_sync"],
        "LinkedIn": ["com.linkedin.android"],
        "Pinterest": ["com.pinterest"],
        "Slack": ["com.slack"],
        "Telegram": [
            "app.nicegram",
            "org.telegram.messenger",
            "org.telegram.messenger.web",
            "org.telegram.plus",
            "org.telegram.biftogram",
        ],
        "The Financial Times": ["com.ft.news"],
        "Twitter": ["com.twitter.android"],
    }

    android_app_id_matches = invert_dict(android_app_id_lookup)

    if has_empty_path(u) and u.scheme == "android-app":
        try:
            return android_app_id_matches[u.host]
        except KeyError:
            pass

    if has_empty_path(u) and u.host == "bbs.boingboing.net":
        return "https://boingboing.net/"

    if u.host == "www.baidu.com" and set(k for k, _ in u.query) == {
        "url",
        "wd",
        "eqid",
    }:
        return "Baidu"

    for host, query in [
        ("github.com", "tab"),
        ("stackoverflow.blog", "cb"),
        ("stackoverflow.blog", "force_isolation"),
    ]:
        if u.host == host and u.get(query):
            u = u.remove(query)

    if _is_rss_reader(u):
        return "RSS reader (Feedly, Inoreader, …)"

    if _is_news_aggregator(u):
        return "News aggregator (Flipboard, HN, Reddit, …)"

    if u.host.endswith(".facebook.com"):
        return "Facebook"

    for param, _ in u.query:
        if param.startswith("utm_"):
            u = u.remove(param)

    if u.host in {"m.slashdot.org", "it.slashdot.org"}:
        u = u.replace(host="slashdot.org")

    return u.to_text()
