import datetime
import functools
import glob
import sqlite3
import sys
from typing import TypedDict
import uuid

import hyperlink
import maxminddb
from sqlite_utils import Database


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
    if u.host in {
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
    }:
        return True

    # Materialistic is a Hacker News Android reader.
    # See https://github.com/hidroh/materialistic
    if u.scheme == "android-app" and u.host == "io.github.hidroh.materialistic":
        return True

    return False


def _is_rss_reader(u: hyperlink.DecodedURL) -> bool:
    """
    Returns true if this referrer looks like somebody's RSS reader.
    """
    if u.path == ("",) and u.host in {
        "www.inoreader.com",
        "rss.cloudier.com",
        "jp.inoreader.com",
        "feedly.com",
        "app.usepanda.com",
        "api.daily.dev",
        "base.usepanda.com",
    }:
        return True

    return False


def _is_news_aggregator(u: hyperlink.DecodedURL) -> bool:
    if u.host in {
        "hackurls.com",
        "devurls.com",
        "serializer.io",
        "www.buzzing.cc",
        "progscrape.com",
        "brutalist.report",
    }:
        return True

    return False


@functools.lru_cache
def normalise_referrer(referrer: str | None) -> str | None:
    """
    If possible, create a "normalised form" of a referrer.
    """
    if referrer is None:
        return None

    try:
        u = hyperlink.DecodedURL.from_text(referrer)
    except Exception as e:
        print(f"Unable to parse {referrer}: {e}", file=sys.stderr)
        return None

    if _is_search_referrer(u):
        return "Search (Google, Bing, DDG, …)"

    hostname_matches = {
        "til.alexwlchan.net": None,
        "analytics.alexwlchan.net": None,
        "alexwlchan.net": None,
        "facebook.com": "Facebook",
        "gist.github.com": "GitHub",
        "localhost:5757": None,
        "mail.google.com": "Gmail",
        "out.reddit.com": "Reddit",
        "pypi.org": "PyPI",
        "t.co": "Twitter",
        "translate.google.co.jp": None,
        "weibo.cn": "Weibo",
        "wordpress.com": "WordPress",
        "www.linkedin.com": "LinkedIn",
        "www.reddit.com": "Reddit",
        "instagram.com": "Instagram",
        "books.alexwlchan.net": None,
        "web.skype.com": "Skype",
        "t.cn": "Tencent",
        "lobste.rs": "Lobsters",
        "chat.openai.com": "ChatGPT",
        "127.0.0.1": None,
        "ln.ht": "Linkhut",
    }

    try:
        return hostname_matches[u.host]
    except KeyError:
        pass

    android_app_id_matches = {
        "com.linkedin.android": "LinkedIn",
        "com.slack": "Slack",
        "io.syncapps.lemmy_sync": "Lemmy",
        "org.telegram.messenger": "Telegram",
    }

    if u.scheme == "android-app":
        try:
            return android_app_id_matches[u.host]
        except KeyError:
            pass

    if u.host == "github.com" and u.get("tab"):
        u = u.remove("tab")
        return u.to_text()

    if _is_hacker_news_referrer(u):
        return "Hacker News"

    if _is_rss_reader(u):
        return "RSS reader (Feedly, Inoreader, …)"

    if _is_news_aggregator(u):
        return "News aggregator (HN, Reddit, …)"

    if u.host.endswith(".facebook.com"):
        return "Facebook"

    return referrer
