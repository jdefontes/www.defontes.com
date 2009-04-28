from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Resource(polymodel.PolyModel):
	parent_resource = db.SelfReferenceProperty(collection_name="child_resources")
	author = db.UserProperty()
	path = db.StringProperty()
	title = db.StringProperty()
	creation_date = db.DateTimeProperty(auto_now_add=True)
	modification_date = db.DateTimeProperty(auto_now=True)

class Folder(Resource):
	body = db.TextProperty()
	browse = db.BooleanProperty()
	template = db.StringProperty()

class Article(Resource):
	body = db.TextProperty()
	template = db.StringProperty()

class Image(Resource):
	image_blob = db.BlobProperty()
	mime_type = db.StringProperty()
	width = db.IntegerProperty()
	height = db.IntegerProperty()
