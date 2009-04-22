import logging
import os
import re
import simplejson as json

from common import model
from google.appengine.api import users
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
		self.response.out.write(template.render(path, {}))

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

			for p in [ "title", "summary", "body" ]:
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
			self.error(404)
			self.response.out.write("path " + path + " not found")
			return
		for p in resource.properties():
			if self.request.get(p, None) != None:
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

