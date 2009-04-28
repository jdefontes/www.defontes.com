import logging
import mimetypes
import os
import re
import simplejson as json

from app import model
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MetadataHandler(webapp.RequestHandler):
	def get(self):
		resources = [ model.Artwork(), model.Article(), model.Folder(), model.Image() ]
		hide = [ "_class", "parent_resource" ]
		meta = [
			dict([ (p, None) for p in r.properties() if p not in hide ] + [ ( "class_name", r.class_name() )])
		for r in resources ]
		self.response.headers['Content-Type'] = "application/json"
		self.response.out.write(json.dumps(meta))


class ResourceHandler(webapp.RequestHandler):
	def get(self, path):
		# unbelievably robust content negotiation
		accept = self.request.headers['Accept'] or ""
		send_json = accept.find("json") > -1
		
		key = path
		representation = None
		if self.request.query_string:
			key = key + "?" + self.request.query_string
		
		if not send_json:
			representation = memcache.get(key)
			
		if representation:
			logging.info("cache hit: " +key)
		else:
			logging.info("cache miss: " +key)
			resource = model.Resource.all().filter("path = ", self.request.path).get()
			
			if resource == None:
				return not_found(self.response)
			
			if send_json:
				representation = self.json_representation(resource)
			else:
				if resource.class_name() == "Image":
					representation = self.image_representation(resource)
				else:
					representation = self.html_representation(resource)
				memcache.set(key, representation)
		
		self.write(representation)

	def html_representation(self, resource):
		template_values = { "resource": resource }
		template_name = resource.template or resource.class_name().lower() + ".html"
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
		return { "content_type": "text/html", "body": template.render(path, template_values) }
	
	def image_representation(self, resource):
		if self.request.get("w", None) != None and self.request.get("h", None) != None:
			image = images.Image(resource.image_blob)
			image.resize(width=int(self.request.get("w")), height=int(self.request.get("h")))
			return { "content_type": "image/png", "body": image.execute_transforms(output_encoding=images.PNG) }
		else:
			return { "content_type": resource.mime_type, "body": resource.image_blob }

	def json_representation(self, resource):
		dateformat = "%b %d, %Y %H:%M"
		result = {
			"class_name": resource.class_name(),
			"author": str(resource.author),
			"creation_date": resource.creation_date.strftime(dateformat),
			"modification_date": resource.modification_date.strftime(dateformat),
			"path": resource.path
		}
	
		for p in [ "body", "image_path", "template", "title", "summary" ]:
			if hasattr(resource, p):
				result[p] = getattr(resource, p)
		
		if resource.class_name() == "Image":
			result["image_blob"] = None
		
		if resource.child_resources:
			result['child_resources'] = [ {
				"class_name": c.class_name(),
				"author": str(c.author),
				"creation_date": c.creation_date.strftime(dateformat),
				"modification_date": c.modification_date.strftime(dateformat),
				"path": c.path,
				"title": c.title
			} for c in resource.child_resources.order("path") ]
		
		# browsers don't like the proper mime type: http://simonwillison.net/2009/Feb/6/json/
		# and also a workaround for this: http://tech.groups.yahoo.com/group/ydn-javascript/message/29416
		return { "content_type": "text/html", "body": json.dumps(result) }
	
	def write(self, representation):
		self.response.headers['Content-Type'] = representation["content_type"]
		self.response.out.write(representation["body"])

		
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
					self.error(412) # Precondition Failed
					self.response.out.write("parent folder " + parent_path + " not found")
					return
				
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
				else:
					setattr(resource, p, value)

		resource.put()
		self.write(self.json_representation(resource))

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

