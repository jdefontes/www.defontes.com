from email.utils import formatdate
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
        elem.appendChild(self.document.createTextNode(formatdate()))
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
