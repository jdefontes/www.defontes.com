import logging
import mimetypes
import os
import re
from django.utils import simplejson as json

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
    def __init__(self, content_type, modification_date, body):
        self.content_type = content_type
        self.modification_date = modification_date
        self.body = body

class ResourceHandler(webapp.RequestHandler):
    cache_duration = 3600
    dateformat = "%b %d, %Y %H:%M"
    def cached_representation(self, key):
        representation = memcache.get(key)
        if representation:
            logging.info("HIT: " + key)
        else:
            logging.info("MISS: " + key)
        return representation
    
    def head(self, path):
        self.get(path)
        
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
                # see if adding or removing a trailing slash finds anything
                if self.request.path.endswith("/"):
                    mangled = self.request.path.rstrip("/")
                else:
                    mangled = self.request.path + "/"
                resource = model.Resource.all().filter("path = ", mangled).get()
                if resource:
                    # resource paths are cannonical, so redirect
                    return self.redirect(resource.path)
                
                return self.not_found()
            
            if send_json:
                representation = self.json_representation(resource)
            else:
                resource.navigation = model.Resource.all().filter("main_navigation >", 0).order("main_navigation").fetch(100)
                handler_name = "handle_" + (resource.handler or resource.class_name().lower())
                handler = ResourceHandler.__dict__[handler_name]
                representation = handler(self, resource)
                memcache.set(key, representation, self.cache_duration)
                
        if not send_json and representation.modification_date and self.request.if_modified_since and self.request.if_modified_since.replace(microsecond=0,tzinfo=None) >= representation.modification_date.replace(microsecond=0,tzinfo=None):
            return self.not_modified()
        
        self.write(representation)

    def handle_article(self, resource):
        return self.template_representation(resource, None, resource.modification_date)
    
    def handle_artwork(self, resource):
        return self.template_representation(resource, None, resource.modification_date)
    
    def handle_blog(self, resource):
        posts = model.Article.all().order("-publication_date").fetch(1000)
        last_modified = resource.modification_date
        for p in posts:
            if p.modification_date > last_modified:
                last_modified = p.modification_date
        
        return self.template_representation(resource, posts, last_modified)
    
    def handle_feed(self, resource):
        # TODO - model attribute for item count?
        # TODO - model attributes for other hard-coded values?
        children =  model.__dict__[resource.resource_type].all().order("-publication_date").fetch(10)
        last_modified = resource.modification_date
        for c in children:
            if c.modification_date > last_modified:
                last_modified = c.modification_date
        
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
            if resource.template:
                body = self.render_template(resource.template, { "child": c })
            else:
                body = c.body
            # fix links to local URLs in body
            soup = BeautifulSoup(body, fromEncoding='utf-8')
            for link in soup.findAll('a', href=re.compile('^\/.*')):
            	link['href'] = self.request.host_url + link['href']
            feed.add_item(
                title = c.title,
                description = unicode(soup),
                link = self.request.host_url + c.path,
                author = "jason@defontes.com (Jason DeFontes)",
                pub_date = c.publication_date
            )
        
        return Representation("application/rss+xml", last_modified, feed.to_xml())
    
    def handle_folder(self, resource):
        children =  resource.child_resources
        last_modified = resource.modification_date
        for c in children:
            if c.modification_date > last_modified:
                last_modified = c.modification_date
        return self.template_representation(resource, children, last_modified)
    
    # sample custom handler
    def handle_home(self, resource):
        posts = model.Article.all().order("-publication_date").fetch(5)
        last_modified = resource.modification_date
        for p in posts:
            if p.modification_date > last_modified:
                last_modified = p.modification_date
        return self.template_representation(resource, posts, last_modified)
    
    def handle_image(self, resource):
        if self.request.get("w", None) != None and self.request.get("h", None) != None:
            image = images.Image(resource.image_blob)
            image.resize(width=int(self.request.get("w")), height=int(self.request.get("h")))
            return Representation("image/jpeg", resource.modification_date, image.execute_transforms(output_encoding=images.JPEG))
        else:
            return Representation(resource.mime_type, resource.modification_date, resource.image_blob)

    def handle_tag(self, resource):
        children = model.Resource.all().filter("tags = ", resource.title)
        last_modified = resource.modification_date
        for c in children:
            if c.modification_date > last_modified:
                last_modified = c.modification_date
        return self.template_representation(resource, children, last_modified)
    
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
        return Representation("text/html", None, json.dumps(result))
    
    def render_template(self, template_name, template_values):
        path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
        return template.render(path, template_values)
    
    def template_representation(self, resource, children, modification_date):
        template_values = {
            "resource": resource,
            "children": children
        }
        template_name = resource.template or resource.class_name().lower() + ".html"
        return Representation("text/html", modification_date, self.render_template(template_name, template_values))
    
    def write(self, representation):
        self.response.headers['Content-Type'] = representation.content_type
        if representation.modification_date:
            self.response.headers['Last-Modified'] = rss.format_rfc822_date(representation.modification_date)
            self.response.headers['Cache-Control'] = "max-age=" + str(self.cache_duration)
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
                elif p == "main_navigation":
                    setattr(resource, p, (value and int(value)) or None)
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
        
    def not_found(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'templates', '404.html')
        self.response.set_status(404)
        self.response.out.write(template.render(path, {} ))
        
    def not_modified(self):
        self.response.set_status(304)
        self.response.headers['Cache-Control'] = "max-age=" + str(self.cache_duration)
        
    def precondition_failed(self, message):
        self.error(412) # Precondition Failed
        self.response.out.write(message)
        
    def redirect(self, path):
        self.response.set_status(302)
        self.response.headers['Location'] = path


application = webapp.WSGIApplication( [
    ('/__meta__/', MetadataHandler),
    ('(/.*)', ResourceHandler)
], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

