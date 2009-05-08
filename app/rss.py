from xml.dom import getDOMImplementation

class RssFeed:
    def __init__(self, title, description, link):
        self.document = getDOMImplementation().createDocument(None, "rss", None)
        rss = self.document.documentElement
        rss.setAttribute("version", "2.0")
        channel = self.document.createElement("channel")

        channel_title = self.document.createElement("title")
        channel_title.appendChild(self.document.createTextNode(title))
        channel.appendChild(channel_title)

        channel_desc = self.document.createElement("description")
        channel_desc.appendChild(self.document.createTextNode(description))
        channel.appendChild(channel_desc)
        
        channel_link = self.document.createElement("link")
        channel_link.appendChild(self.document.createTextNode(link))
        channel.appendChild(channel_link)

        rss.appendChild(channel)

    def to_xml(self):
        return self.document.toprettyxml()
