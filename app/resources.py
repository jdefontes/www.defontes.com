import logging
import os

from app import model
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class ResourceHandler(webapp.RequestHandler):
	def get(self, path):
		logging.info("Accept: " + self.request.headers['Accept'])
		resource = model.Resource.all().filter("path = ", self.request.path).get()
		
		if resource == None:
			return not_found(self.response)
		
		template_values = {
			"resource": resource
		}
		
		template_name = resource.template or resource.class_name().lower() + ".html"
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', template_name )
		self.response.out.write(template.render(path, template_values))

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

