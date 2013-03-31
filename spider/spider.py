#!/usr/bin/python

import argparse
import importlib
import math
import os
import requests
import stat
import time

from db import DB
import config
import formats
import utils
import workerpool


class Document(object):
  def __init__(self, repo, name, url, ancestors = []):
    self.repo = repo
    self.name = name
    self.url = url
    self.ancestors = ancestors

  def report(self):
    if self.url:
      utils.log.info("  " * len(self.ancestors) + self.url)
    else:
      utils.log.info("  " * len(self.ancestors) + self.name)

  def download(self):
    pass

  def fresh(self):
    assert not self.ancestors
    c = db.execute("SELECT mtime FROM documents WHERE url = ?", [self.url])
    r = c.fetchone()
    return r and r[0] == self.mtime()

  def index_one(self):
    c = db.execute("INSERT OR REPLACE INTO documents(repo, name, url, mtime, indextime) VALUES (?, ?, ?, ?, STRFTIME('%s', 'now'))", [self.repo.name, self.name, self.url, self.mtime()])
    self.id = c.lastrowid

    if self.ancestors:
      db.executemany("INSERT INTO documents_tree VALUES (?, ?, ?)",
                     [[a.id, self.id, len(self.ancestors) - i] for (i, a) in enumerate(self.ancestors)])

    if self.text:
      db.execute("INSERT INTO documents_fts(rowid, content) VALUES (?, ?)", [self.id, self.text])

  def touch(self):
    assert not self.ancestors
    db.execute("UPDATE documents SET indextime = STRFTIME('%s', 'now') WHERE documents.rowid IN (SELECT child FROM documents_tree INNER JOIN documents ON documents_tree.parent = documents.rowid WHERE url = ?)", [self.url])


class LocalDocument(Document):
  def __init__(self, repo, name, url, ancestors = []):
    super(LocalDocument, self).__init__(repo, name, url, ancestors)
    self.unlink = False

  def mtime(self):
    return os.stat(self.basepath)[stat.ST_MTIME]

  def read(self):
    self.text = formats.read(self.basepath)

  def children(self):
    for (filename, path) in formats.iter(self.basepath):
      child = LocalDocument(self.repo, os.path.split(filename)[1], None, self.ancestors + [self])
      child.basepath = path
      child.unlink = True
      yield child

  def __del__(self):
    if self.unlink:
      os.unlink(self.basepath)


class RemoteDocument(LocalDocument):
  def download(self):
    self.basepath = utils.download(self.url)
    self.unlink = True


class Spider(workerpool.WorkerPool):
  def __init__(self, repo, processcount = None):
    super(Spider, self).__init__(processcount, None)
    self.repo = repo

  def init_worker(self):
    global db
    db = DB(".db")
    global s
    s = requests.session()

  def deinit_worker(self):
    db.close()

  def do_work(self, item):
    self.index_doc(item)

  def index(self):
    starttime = math.floor(time.time())

    self.start_processes()

    for doc in self.repo.walk():
      self.enqueue(doc)

    self.stop_processes()

    self.init_worker()
    db.execute("DELETE FROM documents WHERE repo = ? AND indextime < ?",
               [self.repo.name, starttime])
    db.commit()
    self.deinit_worker()

  def index_doc(self, doc):
    doc.report()
    doc.download()

    if doc.fresh():
      doc.touch()
      db.commit()
      return

    try:
      self.do_index(doc)
      db.commit()

    except Exception:
      db.rollback()
      raise

  def do_index(self, doc):
    # TODO: make the transaction length as short as possible for performance

    doc.read()
    doc.index_one()

    for child in doc.children():
      child.report()
      try:
        child.download()
        self.do_index(child)
      except utils.DownloadException:
        pass

def parse_args():
  ap = argparse.ArgumentParser()
  ap.add_argument("repo")
  ap.add_argument("-w", "--workers", type = int, default = 4)
  return ap.parse_args()

def get_repo(name):
  path = "repos.%s" % name
  m = importlib.import_module(path)
  return getattr(m, "%sRepo" % name.capitalize())()

def main():
  os.environ["REQUESTS_CA_BUNDLE"] = "/etc/pki/tls/certs/ca-bundle.crt"
  args = parse_args()
  repo = get_repo(args.repo)
  Spider(repo, args.workers).index()

if __name__ == "__main__":
  import spider
  spider.main()
