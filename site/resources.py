import cgi
import os

from common import model
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class ArticleHandler(webapp.RequestHandler):
  def get(self):
  
    articles = model.Article.all().filter("path = ", self.request.path).fetch(1)
    
    if len(articles) == 1:
      article = articles[0]
      
    template_values = {
        "article": article
      }

    path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'article.html')
    self.response.out.write(template.render(path, template_values))

class ResourceHandlerApplication(object):
  # example of writing our own version of WSGIApplication
  def __init__(self):
    self.__debug = True # framework expects this

  def __call__(self, environ, start_response):
    request = webapp.Request(environ)
    response = webapp.Response()
    
    # TODO - handler mapping goes here
    handler = ArticleHandler()
    
    handler.initialize(request, response)
    groups = ()
    if handler:
      try:
        method = environ['REQUEST_METHOD']
        if method == 'GET':
          handler.get(*groups)
        elif method == 'POST':
          handler.post(*groups)
        elif method == 'HEAD':
          handler.head(*groups)
        elif method == 'OPTIONS':
          handler.options(*groups)
        elif method == 'PUT':
          handler.put(*groups)
        elif method == 'DELETE':
          handler.delete(*groups)
        elif method == 'TRACE':
          handler.trace(*groups)
        else:
          handler.error(501)
      except Exception, e:
        handler.handle_exception(e, self.__debug)
    else:
      response.set_status(404)

    response.wsgi_write(start_response)
    return ['']

application = ResourceHandlerApplication()

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

