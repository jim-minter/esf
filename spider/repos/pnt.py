#!/usr/bin/python

import os

import spider

class PntRepo(spider.Repo):
  name = "pnt"

  def walk(self):
    base = self.config.get("filebase")
    for dirpath, dirnames, filenames in os.walk(base):
      dirnames[:] = sorted(dirnames)

      for f in sorted(filenames):
        p = os.path.join(dirpath, f)
        url = os.path.join(self.config.get("urlbase"),
                           os.path.relpath(p, base))

        doc = spider.LocalDocument(self, f, url)
        doc.basepath = p
        yield doc
