import os

from app import model
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MainPage(webapp.RequestHandler):
	def get(self):
		# make sure we have a root resource
		root = model.Folder.all().filter("path =", "/").get()
		if root == None:
			root = model.Folder()
			root.path = "/"
			root.author = users.get_current_user()
			root.put()
		
		path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin.html')
		self.response.out.write(template.render(path, { "resource": { "title": "Admin" } }))

application = webapp.WSGIApplication( [
	('/admin/', MainPage)
], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()

