import datetime
import os

from app import model
from google.appengine.api import memcache
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
            root.publication_date = datetime.datetime.now()
            root.put()
        
        path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin.html')
        self.response.out.write(template.render(path, { "resource": { "title": "Admin" } }))
    
    # HACK - sticking this here for now because I can
    def post(self):
        memcache.flush_all()
        self.response.out.write("flushed")

application = webapp.WSGIApplication( [
    ('/admin/', MainPage)
], debug=True)


