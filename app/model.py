from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Resource(polymodel.PolyModel):
    parent_resource = db.SelfReferenceProperty(collection_name="child_resources")
    body = db.TextProperty()
    author = db.UserProperty()
    handler = db.StringProperty()
    main_navigation = db.IntegerProperty()
    path = db.StringProperty()
    title = db.StringProperty()
    creation_date = db.DateTimeProperty(auto_now_add=True)
    modification_date = db.DateTimeProperty(auto_now=True)
    publication_date = db.DateTimeProperty()

class Article(Resource):
    body_extended = db.TextProperty()
    tag_keys = db.ListProperty(db.Key)
    template = db.StringProperty()

class Artwork(Resource):
    def get_tags(self):
        return Tag.get(self.tag_keys)
    dimensions = db.StringProperty()
    image_path = db.StringProperty()
    media = db.StringProperty()
    tag_keys = db.ListProperty(db.Key)
    tags = property(get_tags)
    template = db.StringProperty()
    year = db.StringProperty()

class Feed(Resource):
    template = db.StringProperty()
    resource_types = db.StringListProperty()

class Folder(Resource):
    body_extended = db.TextProperty()
    template = db.StringProperty()

class Image(Resource):
    image_blob = db.BlobProperty()
    mime_type = db.StringProperty()
    width = db.IntegerProperty()
    height = db.IntegerProperty()

class Tag(Resource):
    template = db.StringProperty()
