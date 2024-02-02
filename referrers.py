import functools
import sys

import hyperlink


def has_empty_path(u):
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
        "www.ecosia.org",
        "www.perplexity.ai",
        "www.qwant.com",
        "www.startpage.com",
        "ya.ru",
        "iframe-yang.yandex",
    }:
        return True

    if u.scheme == "android-app" and u.host in {
        "com.google.android.googlequicksearchbox",
        "com.google.android.gm",
    }:
        return True

    return False


def _is_hacker_news_referrer(u: hyperlink.DecodedURL) -> bool:
    """
    Returns True if this referrer is Hacker News or an aggregator.

    If one of my posts hits the front page of Hacker News, this allows
    me to gather all that into a single category.
    """
    if has_empty_path(u) and u.host in {
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
    }:
        return True

    # Materialistic is a Hacker News Android reader.
    # See https://github.com/hidroh/materialistic
    if (
        has_empty_path(u)
        and u.scheme == "android-app"
        and u.host
        in {
            "io.github.hidroh.materialistic",
            "com.jiaqifeng.hacki",
            "com.stefandekanski.hackernews.free",
        }
    ):
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
    }:
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
    }:
        return True

    if u.host == "b.hatena.ne.jp" and u.path == ("hotentry", "it"):
        return True

    if u.host == "b.hatena.ne.jp" and u.path == ("hotentry", "fun"):
        return True

    return False


def _is_reddit(u: hyperlink.DecodedURL) -> bool:
    return has_empty_path(u) and u.host in {
        "old.reddit.com",
        "out.reddit.com",
        "www.reddit.com",
    }


@functools.lru_cache
def normalise_referrer(referrer: str | None) -> str | None:
    """
    If possible, create a "normalised form" of a referrer.
    """
    if referrer is None:
        return None

    hardcoded_matches = {
        "https://lemmy.blahaj.zone/?dataType=Post&listingType=All&page=3&sort=Active	": "Lemmy",
        "https://lemmy.blahaj.zone/?dataType=Post&listingType=All&page=3&sort=Active": "Lemmy",
        "https://boingboing-net.cdn.ampproject.org/v/s/boingboing.net/2024/02/01/a-pdf-the-size-of-germany-or-the-universe.html/amp?amp_gsa=1&amp_js_v=a9&usqp=mq331AQGsAEggAID": "https://boingboing.net/2024/02/01/a-pdf-the-size-of-germany-or-the-universe.html",
        "https://b.hatena.ne.jp/?iosapp=1": "https://b.hatena.ne.jp/",
        "https://boingboing.net": "https://boingboing.net/",
    }

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
        "alexwlchan.net",
        "analytics.alexwlchan.net",
        "books.alexwlchan.net",
        "til.alexwlchan.net",
        "localhost",
    }:
        return None

    hostname_matches = {
        "127.0.0.1": None,
        "chat.openai.com": "ChatGPT",
        "facebook.com": "Facebook",
        "gist.github.com": "GitHub",
        "instagram.com": "Instagram",
        "l.messenger.com": "Facebook",
        "ln.ht": "Linkhut",
        "lobste.rs": "Lobsters",
        "localhost": None,
        "mail.google.com": "Gmail",
        "pypi.org": "PyPI",
        "t.cn": "Tencent",
        "t.co": "Twitter",
        "translate.google.co.jp": None,
        "twitter.com": "Twitter",
        "web.skype.com": "Skype",
        "weibo.cn": "Weibo",
        "wordpress.com": "WordPress",
        "www.linkedin.com": "LinkedIn",
        "www.reddit.com": "Reddit",
        "www.youtube.com": "YouTube",
        "pinboard.in": "Pinboard",
        "www.tumblr.com": "Tumblr",
        "www.msn.com": "MSN",
        "teams.microsoft.com": "Microsoft Teams",
        "bsky.app": "Bluesky",
        "l.instagram.com": "Instagram",
        "web.telegram.org": "Telegram",
        "lemmy.dbzer0.com": "Lemmy",
        "lemmy.packitsolutions.net": "Lemmy",
        "staging.bsky.app": "Bluesky",
        "www.ft.com": "The Financial Times",

    }

    if has_empty_path(u):
        try:
            return hostname_matches[u.host]
        except KeyError:
            pass

    android_app_id_matches = {
        "com.linkedin.android": "LinkedIn",
        "com.slack": "Slack",
        "io.syncapps.lemmy_sync": "Lemmy",
        "org.telegram.messenger": "Telegram",
        "org.telegram.messenger.web": "Telegram",
        "org.telegram.plus": "Telegram",
        "com.twitter.android": "Twitter",
        "com.ft.news": "The Financial Times",
    }

    if u.scheme == "android-app":
        try:
            return android_app_id_matches[u.host]
        except KeyError:
            pass

    if has_empty_path(u) and u.host == "bbs.boingboing.net":
        return "https://boingboing.net"

    if u.host == "github.com" and u.get("tab"):
        u = u.remove("tab")
        return u.to_text()

    if _is_hacker_news_referrer(u):
        return "Hacker News"

    if _is_rss_reader(u):
        return "RSS reader (Feedly, Inoreader, …)"

    if _is_reddit(u):
        return "Reddit"

    if _is_news_aggregator(u):
        return "News aggregator (Flipboard, HN, Reddit, …)"

    if u.host.endswith(".facebook.com"):
        return "Facebook"

    return referrer
