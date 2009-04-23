from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Resource(polymodel.PolyModel):
  parent_resource = db.SelfReferenceProperty(collection_name="child_resources")
  author = db.UserProperty()
  body = db.TextProperty()
  path = db.StringProperty()
  template = db.StringProperty()
  title = db.StringProperty()
  creation_date = db.DateTimeProperty(auto_now_add=True)
  modification_date = db.DateTimeProperty(auto_now=True)

class Folder(Resource):
  browse = db.BooleanProperty()

class Article(Resource):
  pass