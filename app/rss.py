from datetime import datetime
from xml.dom import getDOMImplementation

class RssFeed:
    def __init__(self, title, description, link, email=None):
        self.document = getDOMImplementation().createDocument(None, "rss", None)
        rss = self.document.documentElement
        rss.setAttribute("version", "2.0")
        channel = self.document.createElement("channel")

        elem = self.document.createElement("title")
        elem.appendChild(self.document.createTextNode(title))
        channel.appendChild(elem)

        elem = self.document.createElement("description")
        elem.appendChild(self.document.createTextNode(description))
        channel.appendChild(elem)
        
        elem = self.document.createElement("link")
        elem.appendChild(self.document.createTextNode(link))
        channel.appendChild(elem)
        
        elem = self.document.createElement("docs")
        elem.appendChild(self.document.createTextNode("http://www.rssboard.org/rss-specification"))
        channel.appendChild(elem)
        
        elem = self.document.createElement("generator")
        elem.appendChild(self.document.createTextNode("Mr. Fusion"))
        channel.appendChild(elem)
        
        elem = self.document.createElement("lastBuildDate")
        elem.appendChild(self.document.createTextNode(rfc822_date(datetime.now())))
        channel.appendChild(elem)
        
        if email is not None:
            elem = self.document.createElement("managingEditor")
            elem.appendChild(self.document.createTextNode(email))
            channel.appendChild(elem)
            elem = self.document.createElement("webMaster")
            elem.appendChild(self.document.createTextNode(email))
            channel.appendChild(elem)
        
        rss.appendChild(channel)

    def to_xml(self):
        return self.document.toprettyxml()
        
def rfc822_date(dt):
    """convert a datetime into an RFC 822 formatted date

    Input date must be in GMT.
    """
    # Looks like:
    #   Sat, 07 Sep 2002 00:00:01 GMT
    # Can't use strftime because that's locale dependent
    #
    # Isn't there a standard way to do this for Python?  The
    # rfc822 and email.Utils modules assume a timestamp.  The
    # following is based on the rfc822 module.
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
            dt.day,
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month-1],
            dt.year, dt.hour, dt.minute, dt.second)