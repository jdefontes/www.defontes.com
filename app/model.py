from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Resource(polymodel.PolyModel):
    parent_resource = db.SelfReferenceProperty(collection_name="child_resources")
    author = db.UserProperty()
    handler = db.StringProperty()
    path = db.StringProperty()
    title = db.StringProperty()
    creation_date = db.DateTimeProperty(auto_now_add=True)
    modification_date = db.DateTimeProperty(auto_now=True)
    publication_date = db.DateTimeProperty()

class Article(Resource):
    body = db.TextProperty()
    body_extended = db.TextProperty()
    tags = db.StringListProperty()
    template = db.StringProperty()

class Artwork(Resource):
    body = db.TextProperty()
    dimensions = db.StringProperty()
    image_path = db.StringProperty()
    media = db.StringProperty()
    tags = db.StringListProperty()
    template = db.StringProperty()
    year = db.StringProperty()

class Feed(Resource):
    body = db.TextProperty()
    template = db.StringProperty()
    resource_type = db.StringProperty()

class Folder(Resource):
    body = db.TextProperty()
    body_extended = db.TextProperty()
    template = db.StringProperty()

class Image(Resource):
    image_blob = db.BlobProperty()
    mime_type = db.StringProperty()
    width = db.IntegerProperty()
    height = db.IntegerProperty()

class Tag(Resource):
    item_count = db.IntegerProperty(default=0)
    template = db.StringProperty()
