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
