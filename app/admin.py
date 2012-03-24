import datetime
import os
import urllib
import uuid
import webapp2

from app import model
from app import resources
from django.template.loader import render_to_string
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext.webapp import blobstore_handlers

class BlobHandler(blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/admin/blob')
        self.response.out.write('<html><body>')
        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
        self.response.out.write("""Upload File: <input name="path" /><input type="file" name="file"><br> <input type="submit"
            name="submit" value="Submit"> </form></body></html>""")
            
    def post(self):
        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        path = self.request.get("path")
        resource = resources.ResourceHandler.create_or_update_resource("Image", path, self.request)
        if not resource:
            self.error(412) # Precondition Failed
            self.response.out.write("parent folder not found for path '%s'" % path)
            return
            
        resource.blob = blob_info
        # fetch enough data to figure out the size (do we need the size for anything?)
        image_data = blobstore.fetch_data(blob_info, 0, blobstore.MAX_BLOB_FETCH_SIZE - 1)
        image = images.Image(image_data=image_data)
        resource.width = image.width
        resource.height = image.height
        resource.title = os.path.basename(path)
        resource.put()
        self.redirect('/admin/blob')
        
    
class MainPage(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
        
    def get(self, path):
        # make sure we have a root resource
        root = model.Folder.all().filter("path =", "/").get()
        if not root:
            root = model.Folder()
            root.path = "/"
            root.uuid = str(uuid.uuid1())
            root.author = users.get_current_user()
            root.put()
        
        templates = os.listdir(os.path.join(os.path.dirname(__file__), '..', 'templates'))
        template = "admin.old.html" if path.endswith("old") else "admin.html"
        self.response.out.write(render_to_string(template, { "resource": { "title": "Admin" }, "templates": templates }))
    
    # HACK - sticking this here for now because I can
    def post(self):
        memcache.flush_all()
        self.response.out.write("flushed")

app = webapp2.WSGIApplication( [
    ('/admin/(.*)', MainPage),
    ('/admin/blob', BlobHandler)
], debug=True)
