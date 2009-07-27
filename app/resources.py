import logging
import mimetypes
import os
import re
import simplejson as json

from app import model
from app import rss
from app.BeautifulSoup import BeautifulSoup
from datetime import datetime
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class MetadataHandler(webapp.RequestHandler):
    def get(self):
        resources = [ model.Artwork(), model.Article(), model.Feed(), model.Folder(), model.Image(), model.Tag() ]
        hide = [ "_class", "parent_resource" ]
        meta = [
            dict([ (p, None) for p in r.properties() if p not in hide ] + [ ( "class_name", r.class_name() )])
        for r in resources ]
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(meta))

class Representation(object):
    def __init__(self, content_type, body):
        self.content_type = content_type
        self.body = body

class ResourceHandler(webapp.RequestHandler):
    dateformat = "%b %d, %Y %H:%M"
    def cached_representation(self, key):
        representation = None #memcache.get(key)
        if representation:
            logging.info("HIT: " + key)
        else:
            logging.info("MISS: " + key)
        return representation
        
    def get(self, path):
        # unbelievably robust content negotiation
        accept = (self.request.headers.has_key('Accept') and self.request.headers['Accept'] or "")
        send_json = accept.find("json") > -1
        
        representation = None
        key = self.request.path_qs
        
        if not send_json:
            representation = self.cached_representation(key)
            
        if not representation:
            resource = model.Resource.all().filter("path = ", self.request.path).get()
            
            if resource == None:
                return not_found(self.response)
            
            if send_json:
                representation = self.json_representation(resource)
            else:
                handler_name = "handle_" + (resource.handler or resource.class_name().lower())
                handler = ResourceHandler.__dict__[handler_name]
                representation = handler(self, resource)
                memcache.set(key, representation)
        
        self.write(representation)

    def handle_article(self, resource):
        return self.template_representation(resource, None)
    
    def handle_artwork(self, resource):
        return self.template_representation(resource, None)
    
    def handle_feed(self, resource):
        # TODO - model attribute for item count?
        # TODO - model attributes for other hard-coded values?
        children =  model.__dict__[resource.resource_type].all().order("-publication_date").fetch(10)
        last_modified = None
        for c in children:
            if last_modified is None or c.publication_date > last_modified:
                last_modified = c.publication_date
        
        feed = rss.RssFeed(
            title = resource.title,
            description = resource.body,
            link = self.request.host_url + "/",
            copyright = "Copyright 2009 Jason DeFontes",
            email = "jason@defontes.com (Jason DeFontes)",
            pub_date = last_modified,
            rss_link = self.request.host_url + resource.path
        )
        
        for c in children:
            # fix links to local URLs in body
            soup = BeautifulSoup(c.body, fromEncoding='utf-8')
            for link in soup.findAll('a', href=re.compile('^\/.*')):
            	logging.info(link['href'])
            	link['href'] = self.request.host_url + link['href']
            feed.add_item(
                title = c.title,
                description = unicode(soup),
                link = self.request.host_url + c.path,
                author = "jason@defontes.com (Jason DeFontes)",
                pub_date = c.publication_date
            )
        
        return Representation("application/rss+xml", feed.to_xml())
    
    def handle_folder(self, resource):
        return self.template_representation(resource, resource.child_resources)
    
    # sample custom handler
    #def handle_home(self, resource):
    #    posts = model.Article.all().order("-creation_date").fetch(5)
    #    return self.template_representation(resource, posts)
    
    def handle_image(self, resource):
        if self.request.get("w", None) != None and self.request.get("h", None) != None:
            image = images.Image(resource.image_blob)
            image.resize(width=int(self.request.get("w")), height=int(self.request.get("h")))
            return Representation("image/png", image.execute_transforms(output_encoding=images.PNG))
        else:
            return Representation(resource.mime_type, resource.image_blob)

    def handle_tag(self, resource):
        children = model.Resource.all().filter("tags = ", resource.title)
        return self.template_representation(resource, children)
    
    def json_representation(self, resource):
        result = {
            "class_name": resource.class_name(),
            "author": str(resource.author),
            "creation_date": resource.creation_date.strftime(self.dateformat),
            "modification_date": resource.modification_date.strftime(self.dateformat),
            "publication_date": (resource.publication_date and resource.publication_date.strftime(self.dateformat) or None)
        }
    
        ignore = [ "_class", "author", "creation_date", "modification_date", "parent_resource", "publication_date" ]
        properties = [ p for p in resource.properties() if p not in ignore ]
        for p in properties:
            result[p] = getattr(resource, p)
        
        if resource.class_name() == "Image":
            result["image_blob"] = None
        
        if resource.child_resources:
            result['child_resources'] = [ {
                "class_name": c.class_name(),
                "author": str(c.author),
                "creation_date": c.creation_date.strftime(self.dateformat),
                "modification_date": c.modification_date.strftime(self.dateformat),
                "publication_date": (c.publication_date and c.publication_date.strftime(self.dateformat) or None),
                "path": c.path,
                "title": c.title
            } for c in resource.child_resources.order("path") ]
        
        # browsers don't like the proper mime type: http://simonwillison.net/2009/Feb/6/json/
        # and also a workaround for this: http://tech.groups.yahoo.com/group/ydn-javascript/message/29416
        return Representation("text/html", json.dumps(result))
        
    def template_representation(self, resource, children):
        template_values = {
            "resource": resource,
            "children": children
        }
        template_name = resource.template or resource.class_name().lower() + ".html"
        path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
        return Representation("text/html", template.render(path, template_values))
    
    def write(self, representation):
        self.response.headers['Content-Type'] = representation.content_type
        self.response.out.write(representation.body)

        
    # Using POST here even though PUT would be more REST-ful because
    # POST parses the entity body as a query string which makes life
    # easier both here and on the client
    def post(self, path):
        if not users.is_current_user_admin():
            self.error(401)
            return
        
        resource = model.Resource.all().filter("path =", path).get()
        if resource == None:
            if path != "/":
                parent_path = re.match(".*/", path.rstrip("/")).group(0)
                parents = model.Folder.all().filter("path =", parent_path).fetch(1)
                if len(parents) == 1:
                    parent_resource = parents[0]
                else:
                    return self.precondition_failed("parent folder " + parent_path + " not found")
                
                resource = model.__dict__[self.request.get("class_name")]()
                resource.author = users.get_current_user()
                resource.parent_resource = parent_resource
            else:
                self.error(500)
                self.response.out.write("root resource is missing")
                return

        for p in resource.properties():
            value = self.request.get(p)
            if self.request.get(p, None) != None:
                if p == "image_blob":
                    if value != "":
                        setattr(resource, p, db.Blob(value))
                        resource.mime_type, encoding = mimetypes.guess_type(self.request.path)
                        image = images.Image(resource.image_blob)
                        resource.width = image.width
                        resource.height = image.height
                elif p == "publication_date":
                    setattr(resource, p, (value and datetime.strptime(value, self.dateformat) or None))
                elif p == "tags":
                    old_tags = resource.tags
                    new_tags = [ name.strip() for name in value.split(',') if name.strip() != "" ]
                    tags = set(old_tags + new_tags)
                    for name in tags:
                        tag = model.Tag.all().filter("title = ", name).get()
                        if tag == None:
                            return self.precondition_failed("tag " + name + " not found")
                        if name in new_tags and name not in old_tags:
                            tag.item_count = tag.item_count + 1
                        elif name in old_tags and name not in new_tags:
                            tag.item_count = tag.item_count - 1
                        tag.put()
                    setattr(resource, p, new_tags)
                else:
                    setattr(resource, p, value)

        resource.put()
        self.write(self.json_representation(resource))
    
    def precondition_failed(self, message):
        self.error(412) # Precondition Failed
        self.response.out.write(message)

def not_found(response):
    path = os.path.join(os.path.dirname(__file__), '..', 'templates', '404.html')
    response.set_status(404)
    response.out.write(template.render(path, {} ))

            
application = webapp.WSGIApplication( [
    ('/__meta__/', MetadataHandler),
    ('(/.*)', ResourceHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

