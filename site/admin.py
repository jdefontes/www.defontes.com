import logging
import os
import re
import simplejson as json

from site import model
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MainPage(webapp.RequestHandler):
	def get(self):
		# make sure we have a root resource
		results = model.Folder.all().filter("path =", "/").fetch(1)
		if len(results) == 0:
			resource = model.Folder()
			resource.path = "/"
			resource.author = users.get_current_user()
			resource.title = "ROOT"
			resource.put()
		
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin.html')
		self.response.out.write(template.render(path, { "resource": { "title": "Admin" } }))

class ResourceHandler(webapp.RequestHandler):
	def get(self, path):
		dateformat = "%b %d, %Y %H:%M"
		resources = model.Resource.all().filter("path = ", path).fetch(1)
		if len(resources) == 1:
			resource = resources[0]
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
				
			if resource.class_name() == "Folder":
				result['child_resources'] = [ {
					"class_name": c.class_name(),
					"author": str(c.author),
					"creation_date": c.creation_date.strftime(dateformat),
					"modification_date": c.modification_date.strftime(dateformat),
					"path": c.path,
					"title": c.title
				} for c in resource.child_resources.order("path") ]
				
			# http://simonwillison.net/2009/Feb/6/json/
			self.response.headers['Content-Type'] = "application/javascript"
			self.response.out.write(json.dumps(result))
		else:
			self.error(404)
			self.response.out.write(path + " not found")

	# Using POST here even though PUT would be more REST-ful because
	# POST parses the entity body as a query string which makes life
	# easier both here and on the client.
	def post(self, path):
		resources = model.Resource.all().filter("path =", path).fetch(1)
		if len(resources) == 1:
			resource = resources[0]
		else:
			if path != "/":
				parent_path = re.match(".*/", path.rstrip("/")).group(0)
				parents = model.Folder.all().filter("path =", parent_path).fetch(1)
				if len(parents) == 1:
					parent_resource = parents[0]
				else:
					self.error(404)
					self.response.out.write("parent folder " + parent_path + " not found")
					return
				resource = model.__dict__[self.request.get("class_name")]()
				resource.author = users.get_current_user()
				resource.parent_resource = parent_resource

		for p in resource.properties():
			if self.request.get(p, None) != None:
				# this should be dynamic, like maybe:
				# if isinstance(resource.__class__.__dict__[p], db.BooleanProperty):
				if p == "browse":
					setattr(resource, p, bool(self.request.get(p)))
				else:
					setattr(resource, p, self.request.get(p))

		resource.put()
		self.response.out.write("updated")
		

application = webapp.WSGIApplication( [
	('/admin/', MainPage),
	('/admin/resources(/.*)', ResourceHandler)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()

