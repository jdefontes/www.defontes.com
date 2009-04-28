import logging
import mimetypes
import os
import re
import simplejson as json

from app import model
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MetadataHandler(webapp.RequestHandler):
	def get(self):
		resources = [ model.Article(), model.Folder(), model.Image() ]
		hide = [ "_class", "parent_resource" ]
		meta = [
			dict([ (p, None) for p in r.properties() if p not in hide ] + [ ( "class_name", r.class_name() )])
		for r in resources ]
		self.response.headers['Content-Type'] = "application/json"
		self.response.out.write(json.dumps(meta))


class ResourceHandler(webapp.RequestHandler):
	def get(self, path):
		resource = model.Resource.all().filter("path = ", self.request.path).get()
		
		if resource == None:
			return not_found(self.response)
		
		# unbelievably robust content negotiation
		accept = self.request.headers['Accept'] or ""
		#logging.info("Accept: " + accept)
		if accept.find("json") > -1:
			self.json_representation(resource)
		elif resource.class_name() == "Image":
			self.image_representation(resource)
		else:
			self.html_representation(resource)

	def html_representation(self, resource):
		template_values = {
			"resource": resource
		}
		template_name = resource.template or resource.class_name().lower() + ".html"
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
		self.response.out.write(template.render(path, template_values))
	
	def image_representation(self, resource):
		if self.request.get("w", None) != None and self.request.get("h", None) != None:
			image = images.Image(resource.image_blob)
			image.resize(width=int(self.request.get("w")), height=int(self.request.get("h")))
			self.response.headers['Content-Type'] = "image/png"
			self.response.out.write(image.execute_transforms(output_encoding=images.PNG))
		else:
			self.response.headers['Content-Type'] = resource.mime_type
			self.response.out.write(resource.image_blob)

	def json_representation(self, resource):
		dateformat = "%b %d, %Y %H:%M"
		result = {
			"class_name": resource.class_name(),
			"author": str(resource.author),
			"creation_date": resource.creation_date.strftime(dateformat),
			"modification_date": resource.modification_date.strftime(dateformat),
			"path": resource.path
		}
	
		for p in [ "body", "browse", "template", "title", "summary" ]:
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
		self.response.headers['Content-Type'] = "text/html"
		self.response.out.write(json.dumps(result))
		
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
				# this should be dynamic, like maybe:
				# if isinstance(resource.__class__.__dict__[p], db.BooleanProperty):
				if p == "browse":
					setattr(resource, p, bool(value))
				elif p == "image_blob":
					if value != "":
						setattr(resource, p, db.Blob(value))
						resource.mime_type, encoding = mimetypes.guess_type(self.request.path)
						image = images.Image(resource.image_blob)
						resource.width = image.width
						resource.height = image.height
				else:
					setattr(resource, p, value)

		resource.put()
		self.json_representation(resource)

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

