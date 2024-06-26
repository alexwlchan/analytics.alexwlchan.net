const cookieName = "analytics.alexwlchan-isMe";

/* https://stackoverflow.com/a/5968306/1558022 */
function getCookie(name) {
    var dc = document.cookie;
    var prefix = name + "=";
    var begin = dc.indexOf("; " + prefix);
    if (begin == -1) {
        begin = dc.indexOf(prefix);
        if (begin != 0) return null;
    }
    else
    {
        begin += 2;
        var end = document.cookie.indexOf(";", begin);
        if (end == -1) {
        end = dc.length;
        }
    }
    // because unescape has been deprecated, replaced with decodeURI
    //return unescape(dc.substring(begin + prefix.length, end));
    return decodeURI(dc.substring(begin + prefix.length, end));
}

function removeExclusionCookie() {
    document.cookie = `${cookieName}=;domain=.alexwlchan.net;path=/;expires=1970-01-01 01:01:01`;
    hasNoExclusionCookie();
}

function addExclusionCookie() {
    document.cookie = `${cookieName}=true;domain=.alexwlchan.net;path=/;expires=2035-01-19 03:14:07`;
    hasExclusionCookie();
}

function hasExclusionCookie() {
  document.querySelector("#exclusionCookie").innerHTML = `✅ You currently <strong>have</strong> the isMe cookie, so your requests will be filtered out of stats. <a href="#" onclick="removeExclusionCookie()">Remove the cookie</a>`;
}

function hasNoExclusionCookie() {
  document.querySelector("#exclusionCookie").innerHTML = `⚠️ You currently <strong>do not</strong> have the isMe cookie, so your requests will be included in stats. <a href="#" onclick="addExclusionCookie()">Add the cookie</a>`;
}

function createExclusionCookieSection() {
    if (getCookie(cookieName) === "true") {
        hasExclusionCookie();
    } else {
        hasNoExclusionCookie();
    }
}
