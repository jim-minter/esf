#!/usr/bin/python

import os

import config
import spider

class PntRepo(spider.Repo):
  name = "pnt"

  def walk(self):
    base = config.get("pnt-filebase")
    for dirpath, dirnames, filenames in os.walk(base):
      dirnames[:] = sorted(dirnames)

      for f in sorted(filenames):
        p = os.path.join(dirpath, f)
        url = os.path.join(config.get("pnt-urlbase"),
                           os.path.relpath(p, base))

        yield PntDocument(self, f, url, p)


class PntDocument(spider.LocalDocument):
  def __init__(self, repo, name, url, basepath, ancestors = []):
    super(spider.LocalDocument, self).__init__(repo, name, url, ancestors)
    self.basepath = basepath
