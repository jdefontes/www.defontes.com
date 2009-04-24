import logging
import os
import re
import simplejson as json

from app import model
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class ResourceHandler(webapp.RequestHandler):
	def get(self, path):
		resource = model.Resource.all().filter("path = ", self.request.path).get()
		
		if resource == None:
			return not_found(self.response)
		
		# unbelievably robust content negotiation
		accept = self.request.headers['Accept'] or ""
		logging.info("Accept: " + accept)
		if accept.find("json") > -1:
			self.json_representation(resource)
		else:
			self.html_representation(resource)

	def html_representation(self, resource):
		template_values = {
			"resource": resource
		}
		template_name = resource.template or resource.class_name().lower() + ".html"
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
		self.response.out.write(template.render(path, template_values))
		
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
			
		if resource.child_resources:
			result['child_resources'] = [ {
				"class_name": c.class_name(),
				"author": str(c.author),
				"creation_date": c.creation_date.strftime(dateformat),
				"modification_date": c.modification_date.strftime(dateformat),
				"path": c.path,
				"title": c.title
			} for c in resource.child_resources.order("path") ]
		
		self.response.headers['Content-Type'] = "application/json"
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
			if self.request.get(p, None) != None:
				# this should be dynamic, like maybe:
				# if isinstance(resource.__class__.__dict__[p], db.BooleanProperty):
				if p == "browse":
					setattr(resource, p, bool(self.request.get(p)))
				else:
					setattr(resource, p, self.request.get(p))

		resource.put()
		self.json_representation(resource)

def not_found(response):
	path = os.path.join(os.path.dirname(__file__), '..', 'templates', '404.html')
	response.set_status(404)
	response.out.write(template.render(path, {} ))

			
application = webapp.WSGIApplication( [
	('(/.*)', ResourceHandler)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()

