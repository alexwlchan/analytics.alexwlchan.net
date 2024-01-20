## analytics.alexwlchan.net

This is a tiny Flask app for counting visitors to my websites (alexwlchan.net and its subdomains).
My goals for this project are:

*   Collect the data I need to make informed decisions about the site
*   Avoid collecting any Personally Identifiable Information about readers (e.g. IP address)
*   Collect more detailed statistics than Netlify Analytics

https://www.maxmind.com/en/accounts/963002/geoip/downloads

<script>
  window.onload = function() {
    const analyticsData = new URLSearchParams({
      "url": window.location.href,
      "referrer": document.referrer,
      "title": document.title,
      "width": window.innerWidth,
      "height": window.innerHeight,
      // IP address
      // User agent
    });

    fetch(`http://localhost:7007/a.gif?${analyticsData.toString()}`)
      .then(resp => console.log(resp));
  }

</script>


$ datasette requests.sqlite --port 8008 --metadata metadata.json