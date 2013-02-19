#!/usr/bin/python

import json
import urlparse
import web

from spider import db

class Index(object):
  def GET(self):
    web.header("Content-Type", "text/html")
    return open("static/index.html")

class Search(object):
  def GET(self):
    query = dict(urlparse.parse_qsl(str(web.ctx.query[1:])))
    print query["q"]

    rows = []
    for row in web.ctx.db.execute("SELECT DISTINCT name, url, SNIPPET(documents_fts) FROM documents, documents_fts WHERE documents.rowid = documents_fts.rowid AND content MATCH ? ORDER BY url LIMIT 10", [query["q"]]):
      rows.append(dict(zip(["name", "url", "snippet"], row)))

    web.header("Content-Type", "application/json")
    return json.dumps(rows)

urls = ("/", "Index",
        "/s", "Search",
        )

def db_load_hook():
    web.ctx.db = db.DB("spider/.db")

def db_unload_hook():
    web.ctx.db.close()

web.config.debug = False
app = web.application(urls, globals())
app.add_processor(web.loadhook(db_load_hook))
app.add_processor(web.unloadhook(db_unload_hook))
application = app.wsgifunc()

if __name__ == "__main__":
  app.run()
