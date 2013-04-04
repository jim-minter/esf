#!/usr/bin/python

import os
import urlparse

import spider

class LocalRepo(spider.Repo):
  def walk(self):
    base = self.config.get("base")

    for dirpath, dirnames, filenames in os.walk(base):
      dirnames[:] = sorted(dirnames)

      for f in sorted(filenames):
        p = os.path.join(dirpath, f)
        url = self.map(os.path.relpath(p, base))

        doc = spider.LocalDocument(self, f, url)
        doc.basepath = p

        yield doc

  def map(self, p):
    return urlparse.urljoin(self.config.get("baseurl"), p)
