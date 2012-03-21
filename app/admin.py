import datetime
import os
import webapp2

from app import model
from django.template.loader import render_to_string
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db

class MainPage(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
        
    def get(self):
        # make sure we have a root resource
        root = model.Folder.all().filter("path =", "/").get()
        if root == None:
            root = model.Folder()
            root.path = "/"
            root.author = users.get_current_user()
            root.publication_date = datetime.datetime.now()
            root.put()
        
        templates = os.listdir(os.path.join(os.path.dirname(__file__), '..', 'templates'))
        self.response.out.write(render_to_string('admin.html', { "resource": { "title": "Admin" }, "templates": templates }))
    
    # HACK - sticking this here for now because I can
    def post(self):
        memcache.flush_all()
        self.response.out.write("flushed")

app = webapp2.WSGIApplication( [
    ('/admin/', MainPage)
], debug=True)
