#!/usr/bin/python

import calendar
import functools
import math
import requests
import stat
import os
import tarfile
import tempfile
import time
import traceback
import zipfile

import config
import db
import formats
import utils
import workerpool

def memo(f):
  cache = {}
  @functools.wraps(f)
  def wrap(*args):
    if args not in cache:
      cache[args] = f(*args)
    return cache[args]
  return wrap


class DownloadException(Exception):
  pass


class Document(object):
  def __init__(self, repo, name, url, ancestors = []):
    self.repo = repo
    self.name = name
    self.url = url
    self.ancestors = ancestors

  def report(self):
    if self.url:
      print "  " * len(self.ancestors) + self.url
    else:
      print "  " * len(self.ancestors) + self.name

  def download(self):
    self.report()

  def done(self):
    pass


class LocalDocument(Document):
  @memo
  def type(self):
    return formats.type(self.basepath)

  def interesting(self):
    return self.type() is not None

  def mtime(self):
    return os.stat(self.basepath)[stat.ST_MTIME]

  def read(self):
    self.text = formats.read(self.basepath, self.type())

  def children(self):
    for (filename, path) in formats.iter(self.basepath):
      yield TempDocument(self.repo, os.path.split(filename)[1], None, path, self.ancestors + [self])


class TempDocument(LocalDocument):
  def __init__(self, repo, name, url, basepath, ancestors = []):
    super(LocalDocument, self).__init__(repo, name, url, ancestors)
    self.basepath = basepath

  def done(self):
    os.unlink(self.basepath)


class RemoteDocument(LocalDocument):
  def download(self):
    (fd, self.basepath) = tempfile.mkstemp()  # TODO: insecure
    os.close(fd)
    f = open(self.basepath, "w")

    self.report()

    response = requests.get(self.url, prefetch = False, verify = False)
    if response.status_code != 200:
      raise DownloadException()
    remaining = int(response.headers["Content-Length"])
    r = response.raw
    while True:
      data = r.read(4096)
      remaining -= len(data)
      if data == "": break
      f.write(data)
    f.flush()
    os.fsync(f.fileno())
    f.close()

    if remaining > 0:
      # download terminated early, retry
      self.done()
      raise Exception("short read")

    mtime = utils.parsetime(response.headers["Last-Modified"],
                            "%a, %d %b %Y %H:%M:%S %Z")
    os.utime(self.basepath, (mtime, mtime))

  def done(self):
    os.unlink(self.basepath)


class Repo(object):
  pass


class Spider(workerpool.WorkerPool):
  def __init__(self, repo, processcount = 4):
    super(Spider, self).__init__(processcount)
    self.repo = repo

  def init_worker(self):
    self.db = db.DB(".db")

  def deinit_worker(self):
    self.db.close()

  def do_work(self, item):
    self.index_doc(item)

  def index(self):
    self.init_worker()
    self.start_processes()

    now = math.floor(time.time())

    for doc in self.repo.walk():
      self.enqueue(doc)

    self.stop_processes()

    self.db.execute("DELETE FROM documents WHERE repo = ? AND indextime < ?",
                        [self.repo.name, now])
    self.db.commit()
    self.deinit_worker()

  def touch(self, doc):
    c = self.db.execute("SELECT rowid FROM documents WHERE url = ?", [doc.url])
    doc.id = c.fetchone()[0]

    self.db.execute("UPDATE documents SET indextime = STRFTIME('%s', 'now') WHERE documents.rowid IN (SELECT child FROM documents_tree WHERE parent = ?)", [doc.id])
    self.db.commit()

  def fresh(self, doc):
    c = self.db.execute("SELECT mtime FROM documents WHERE url = ?", [doc.url])
    r = c.fetchone()
    return r and r[0] == doc.mtime()

  def index_doc(self, doc):
    doc.download()

    try:
      if not doc.interesting():
        return

      if self.fresh(doc):
        self.touch(doc)
        return

      try:
        self.do_index(doc)
      except Exception, e:
        print "ERROR: %s on %s" % (e.message, doc.name)
        traceback.print_exc()
        if config.get("errors-fatal"):
          raise

        self.db.rollback()

      self.db.commit()

    finally:
      doc.done()

  def do_index(self, doc):
    if not doc.interesting():
      return

    # TODO: make the transaction length as short as possible for performance

    doc.read()

    c = self.db.execute("INSERT OR REPLACE INTO documents(repo, name, url, mtime, indextime) VALUES (?, ?, ?, ?, STRFTIME('%s', 'now'))", [doc.repo.name, doc.name, doc.url, doc.mtime()])
    doc.id = c.lastrowid

    if doc.ancestors:
      self.db.executemany("INSERT INTO documents_tree VALUES (?, ?, ?)",
                              [[a.id, doc.id, len(doc.ancestors) - i] for (i, a) in enumerate(doc.ancestors)])

    if doc.text:
      self.db.execute("INSERT INTO documents_fts(rowid, content) VALUES (?, ?)", [doc.id, doc.text])
      
    for child in doc.children():
      try:
        child.download()
        self.do_index(child)
      except DownloadException:
        pass
      finally:
        child.done()
