from email.utils import formatdate
from time import mktime
from xml.dom import getDOMImplementation

class RssFeed:
    def __init__(self, title, description, link,
            copyright=None,
            email=None,
            pub_date=None,
            rss_link=None):
        self.document = getDOMImplementation().createDocument(None, "rss", None)
        rss = self.document.documentElement
        rss.setAttribute("version", "2.0")
        rss.setAttribute("xmlns:atom", "http://www.w3.org/2005/Atom")
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
        elem.appendChild(self.document.createTextNode(formatdate()))
        channel.appendChild(elem)
        
        if copyright is not None:
            elem = self.document.createElement("copyright")
            elem.appendChild(self.document.createTextNode(copyright))
            channel.appendChild(elem)
        
        if email is not None:
            elem = self.document.createElement("managingEditor")
            elem.appendChild(self.document.createTextNode(email))
            channel.appendChild(elem)
            elem = self.document.createElement("webMaster")
            elem.appendChild(self.document.createTextNode(email))
            channel.appendChild(elem)
        
        if pub_date is not None:
            elem = self.document.createElement("pubDate")
            elem.appendChild(self.document.createTextNode(self.format_rfc822_date(pub_date)))
            channel.appendChild(elem)
        
        if rss_link is not None:
            elem = self.document.createElementNS("http://www.w3.org/2005/Atom", "atom:link")
            elem.setAttribute("rel", "self")
            elem.setAttribute("href", rss_link)
            channel.appendChild(elem)
        
        rss.appendChild(channel)

    def add_item(self, title, description, link, author=None, pub_date=None):
        channel = self.document.firstChild.firstChild
        item = self.document.createElement("item")
        
        elem = self.document.createElement("title")
        elem.appendChild(self.document.createTextNode(title))
        item.appendChild(elem)
        
        elem = self.document.createElement("description")
        elem.appendChild(self.document.createTextNode(description))
        item.appendChild(elem)
        
        elem = self.document.createElement("guid")
        elem.setAttribute("isPermaLink", "true")
        elem.appendChild(self.document.createTextNode(link))
        item.appendChild(elem)
        
        elem = self.document.createElement("link")
        elem.appendChild(self.document.createTextNode(link))
        item.appendChild(elem)
        
        if author is not None:
            elem = self.document.createElement("author")
            elem.appendChild(self.document.createTextNode(author))
            item.appendChild(elem)
            
        if pub_date is not None:
            elem = self.document.createElement("pubDate")
            elem.appendChild(self.document.createTextNode(self.format_rfc822_date(pub_date)))
            item.appendChild(elem)
        
        channel.appendChild(item)

    def format_rfc822_date(self, date):
        return formatdate(mktime(date.timetuple()))
        
    def to_xml(self):
        return self.document.toprettyxml()
