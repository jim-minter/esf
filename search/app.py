#!/usr/bin/python

import json
import time
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
    if "p" not in query: query["p"] = 0

    cursor = web.ctx.db.execute("SELECT name, url, SNIPPET(documents_fts) AS snippet, mtime FROM documents, documents_fts WHERE documents.rowid = documents_fts.rowid AND content MATCH ? ORDER BY mtime DESC LIMIT ?, 10", [query["q"], str(int(query["p"]) * 10)])
    fieldnames = [c[0] for c in cursor.description]
    rows = []
    for row in cursor:
      row = dict(zip(fieldnames, row))
      row["mtime"] = time.strftime("%d %B %Y", time.localtime(row["mtime"]))
      rows.append(row)

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
