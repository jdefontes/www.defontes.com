import datetime
import jinja2
import os
import webapp2

from app import model
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'templates')))

class MainPage(webapp2.RequestHandler):
    def get(self):
        # make sure we have a root resource
        root = model.Folder.all().filter("path =", "/").get()
        if root == None:
            root = model.Folder()
            root.path = "/"
            root.author = users.get_current_user()
            root.publication_date = datetime.datetime.now()
            root.put()
        
        #path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'admin.html')
        template = jinja_environment.get_template('admin.html')
        self.response.out.write(template.render({ "resource": { "title": "Admin" }, "templates": jinja_environment.list_templates() }))
    
    # HACK - sticking this here for now because I can
    def post(self):
        memcache.flush_all()
        self.response.out.write("flushed")

app = webapp2.WSGIApplication( [
    ('/admin/', MainPage)
], debug=True)
