## analytics.alexwlchan.net

This is a tiny Flask app for counting visitors to my websites (alexwlchan.net and its subdomains).
My goals for this project are:

*   Collect the data I need to make informed decisions about the site
*   Avoid collecting any Personally Identifiable Information about readers (e.g. IP address)
*   Collect more detailed statistics than Netlify Analytics

## How it works

Each of the websites I want to measure have a small JavaScript snippet that fetch a tracking pixel, which is served by this web app.
The tracking pixel includes some query parameters to tell you what page you were looking at.
e.g.

> https://analytics.alexwlchan.net/a.gif?url=https%3A%2F%2Falexwlchan.net%2F&referrer=https%3A%2F%2Fexample.net%2F&title=alexwlchan&width=1024&height=768

When you fetch the tracking pixel, it records the hit in a SQLite database.
In particular, it records the following fields:

*   The date of the request
*   The URL and title of the page you were looking at
*   The referrer, i.e. which page linked you to my website
*   The country you're in, which is guessed from your IP address
*   An anonymous session identifier, so I can correlate hits within the same session (more on this below)
*   The dimensions of your screen (e.g. 1024×768)
*   Whether you're a bot or crawler (based on your User-Agent, so I can separate humans from Google's search crawler)

I **don't** record your IP address or user agent.

## Privacy considerations (aka don’t be creepy)

### Anonymous session identifier

I want to see what pages people look at in the same browsing session.
If I'm looking at three hits in quick succession, I want to know if they were three people look at one page each, or one person looking at three pages.

For this, I create an anonymous session identifier.
This is a randomly-assigned UUID that's attached to all requests coming from your (IP address, User-Agent) combination.
It lasts for a single day, after which it expires and your requests get a new UUID.

This session identifier doesn't include your IP address or User-Agent, and I don't record those anywhere.

This means that I can see that a person looked at several pages in a single day, but I can't tell who that person is, and I can't tell you what they looked at over a span of multiple days.

### Matching IP addresses to geographic locations

I record the country associated with an IP address in the database - I don't need anything more granular than that.

To do geolocation lookups of IP addresses, I have a [MaxMind database][maxmind] that allows me to do the matching in an on-disk database.
This means I can do the country lookups without sending all my visitors' IP addresses to an external service.
Ick!

[maxmind]: https://www.maxmind.com/en/home

## Installation

```console
$ git clone git@github.com:alexwlchan/analytics.alexwlchan.net.git
$ cd analytics.alexwlchan.net
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

## Usage

To start the web server:

```console
$ ???
```

To send data to the server, add the following tracking snippet to the page:

```html
<script>
  window.onload = function() {
    const analyticsData = new URLSearchParams({
      "url": window.location.href,
      "referrer": document.referrer,
      "title": document.title,
      "width": window.innerWidth,
      "height": window.innerHeight,
    });

    fetch(`https://alexwlchan.net/a.gif?${analyticsData.toString()}`)
      .then(resp => console.log(resp));
  }
</script>
```

## Analysing the data

Because the data is in a SQLite database, I can analyse it using Datasette.
I use the following command:

```console
$ datasette requests.sqlite --port 8008 --metadata metadata.json
```

## License

tbc



