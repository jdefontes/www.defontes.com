import hashlib
import json
import logging
import mimetypes
import os
import re
import uuid
import webapp2

from app import model
from app import rss
from app.BeautifulSoup import BeautifulSoup
from datetime import datetime
from datetime import timedelta
from django.template.loader import render_to_string
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db

class MetadataHandler(webapp2.RequestHandler):
    def get(self):
        resources = [ model.Artwork(), model.Article(), model.Feed(), model.Folder(), model.Image(), model.Tag() ]
        hide = [ "_class", "parent_resource" ]
        meta = [
            dict([ (p, None) for p in r.properties() if p not in hide ] + [ ( "class_name", r.class_name() )])
        for r in resources ]
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(meta))

class Representation(object):
    def __init__(self, content_type, body, cacheable, blob_key = None):
        self.content_type = str(content_type)
        self.cacheable = cacheable
        self.body = body if body else None
        self.etag = hashlib.md5(self.body).hexdigest() if body else None
        self.blob_key = blob_key

class ResourceHandler(webapp2.RequestHandler):
    cache_duration = 3600
    dateformat = "%b %d, %Y %H:%M"
    
    @staticmethod
    def create_or_update_resource(class_name, path, request):
        resource = model.Resource.all().filter("path =", path).get()
        if resource == None:
            if path != "/":
                parent_path = re.match(".*/", path.rstrip("/")).group(0)
                parents = model.Folder.all().filter("path =", parent_path).fetch(1)
                if len(parents) == 1:
                    parent_resource = parents[0]
                else:
                    return None
                
                resource = model.__dict__[class_name]()
                resource.author = users.get_current_user()
                resource.uuid = str(uuid.uuid1())
                resource.parent_resource = parent_resource
            else:
                return None

        for p in resource.properties():
            value = request.get(p)
            if request.get(p, None) != None:
                if  p == "main_navigation":
                    setattr(resource, p, (value and int(value)) or None)
                elif p == "publication_date":
                    setattr(resource, p, (value and datetime.strptime(value, ResourceHandler.dateformat) or None))
                elif p == "resource_types":
                    setattr(resource, p, [ t.strip() for t in value.split(",") if t.strip() != ""  ])
                elif p == "tag_keys":
                    titles = ",".join([ "'%s'" % name.strip() for name in value.split(',') if name.strip() != "" ])
                    if titles:
                        tags = model.Tag.gql("WHERE title IN (" + titles + ")").fetch(1000)
                        setattr(resource, p, [ t.key() for t in tags ])
                    else:
                        setattr(resource, p, [])
                else:
                    setattr(resource, p, value)
        
        
        
        return resource
                    
    def __init__(self, request, response):
        self.initialize(request, response)
        os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
        
    def add_cache_headers(self):
        self.response.headers['Cache-Control'] = "public, max-age=" + str(self.cache_duration)
        self.response.headers['Expires'] = rss.format_rfc822_date(datetime.utcnow() + timedelta(seconds=self.cache_duration))
    
    def cached_representation(self, key):
        if os.environ["SERVER_SOFTWARE"].startswith("Development"): return None
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
        
        key = self.request.path_qs
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
            
            # Now that we have a resource...
            
            # calculate the parent path
            parts = resource.path.rstrip("/").rpartition("/")
            resource.parent_path = parts[0] + parts[1]
            
            if send_json:
                representation = self.json_representation(resource)
            else:
                resource.navigation = model.Resource.all().filter("main_navigation >", 0).order("main_navigation").fetch(100)
                handler_name = "handle_" + (resource.handler or resource.class_name().lower())
                handler = ResourceHandler.__dict__[handler_name]
                representation = handler(self, resource)
                
            if representation.cacheable:
                memcache.set(key, representation, self.cache_duration)
                
        if representation.etag in self.request.if_none_match:
            return self.not_modified()
            
        self.write(representation)

    def handle_article(self, resource):
        return self.template_representation(resource, None)
    
    def handle_artwork(self, resource):
        return self.template_representation(resource, None)
    
    def handle_blog(self, resource):
        posts = model.Article.all().order("-publication_date").fetch(1000)
        return self.template_representation(resource, posts)
    
    def handle_feed(self, resource):
        # TODO - model attribute for item count?
        # TODO - model attributes for other hard-coded values?
        types = ",".join([ "'%s'" % t for t in resource.resource_types ])
        children =  model.Resource.gql("WHERE class IN (" + types + ") ORDER BY publication_date DESC").fetch(10)
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
            body = self.render_template(c.class_name().lower() + "_post.html", { "child": c })

            # fix links to local URLs in body
            soup = BeautifulSoup(body, fromEncoding='utf-8')
            for link in soup.findAll('a', href=re.compile('^\/.*')):
                link['href'] = self.request.host_url + link['href']
            for img in soup.findAll('img', src=re.compile('^\/.*')):
                img['src'] = self.request.host_url + img['src']
            feed.add_item(
                title = c.title,
                description = unicode(soup),
                link = self.request.host_url + c.path,
                author = "jason@defontes.com (Jason DeFontes)",
                pub_date = c.publication_date,
                guid = c.uuid
            )
        
        return Representation("application/rss+xml", feed.to_xml(), True)
    
    def handle_folder(self, resource):
        children =  resource.child_resources
        return self.template_representation(resource, children)
    
    # sample custom handler
    def handle_home(self, resource):
        #posts = model.Article.all().order("-publication_date").fetch(5)
        posts = model.Resource.gql("WHERE class IN ('Article', 'Artwork') ORDER BY publication_date DESC").fetch(5)
        return self.template_representation(resource, posts)
    
    def handle_image(self, resource):
        if self.request.get("w", None) != None and self.request.get("h", None) != None:
            image = images.Image(blob_key=resource.blob.key())
            image.resize(width=int(self.request.get("w")), height=int(self.request.get("h")))
            if resource.blob.content_type == "image/jpeg":
                content_type = "image/jpeg"
                encoding = images.JPEG
            else:
                content_type = "image/png"
                encoding = images.PNG
            return Representation(content_type, image.execute_transforms(output_encoding=encoding), True)
        else:
            return Representation(resource.blob.content_type, None, True, resource.blob.key())

    def handle_tag(self, resource):
        children = model.Resource.all().filter("tag_keys = ", resource.key())
        return self.template_representation(resource, children)
    
    def json_representation(self, resource):
        result = {
            "class_name": resource.class_name(),
            "author": str(resource.author),
            "creation_date": resource.creation_date.strftime(self.dateformat),
            "modification_date": resource.modification_date.strftime(self.dateformat),
            "publication_date": (resource.publication_date and resource.publication_date.strftime(self.dateformat) or None)
        }
    
        ignore = [ "_class", "author", "creation_date", "modification_date", "parent_resource", "publication_date", "tag_keys", "blob" ]
        properties = [ p for p in resource.properties() if p not in ignore ]
        for p in properties:
            result[p] = getattr(resource, p)
        
        if "tag_keys" in resource.properties():
            result["tag_keys"] = ",".join([ t.title for t in resource.tags ])
            
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
        return Representation("text/html", json.dumps(result), False)
    
    def render_template(self, template_name, template_values):
        return render_to_string(template_name, template_values)
    
    def template_representation(self, resource, children):
        template_values = {
            "resource": resource,
            "children": children
        }
        template_name = resource.template or resource.class_name().lower() + ".html"
        return Representation("text/html", self.render_template(template_name, template_values), True)
    
    def write(self, representation):
        self.response.headers['Content-Type'] = representation.content_type
        self.response.headers['Vary'] = "Accept"
        self.response.headers['X-Inspired-By'] = "Kittens!"
        if representation.blob_key:
            self.response.headers['X-AppEngine-BlobKey'] = str(representation.blob_key)
        else:
            if representation.cacheable:
                self.add_cache_headers()
            self.response.headers['ETag'] = representation.etag
            self.response.out.write(representation.body)

        
    # Using POST here even though PUT would be more REST-ful because
    # POST parses the entity body as a query string which makes life
    # easier both here and on the client
    def post(self, path):
        if not users.is_current_user_admin():
            self.error(401)
            return
        
        resource = self.create_or_update_resource(self.request.get("class_name"), path, self.request)
        if not resource:
            self.precondition_falied("parent folder not found for path '%s'" % path)
            return
            
        resource.put()
        self.write(self.json_representation(resource))
        
    def not_found(self):
        self.response.set_status(404)
        self.response.out.write(render_to_string('404.html', {"resource": None}))
        
    def not_modified(self):
        self.response.set_status(304)
        self.add_cache_headers()
        
    def precondition_failed(self, message):
        self.error(412) # Precondition Failed
        self.response.out.write(message)
        
    def redirect(self, path):
        self.response.set_status(302)
        self.response.headers['Location'] = str(path)


app = webapp2.WSGIApplication( [
    ('/__meta__/', MetadataHandler),
    ('(/.*)', ResourceHandler)
], debug=True)


