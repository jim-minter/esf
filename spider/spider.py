#!/usr/bin/python

import argparse
import importlib
import math
import multiprocessing
import os
import requests
import stat
import time
import weakref

import config
import db
import formats
import utils
import workerpool


class Document(object):
  def __init__(self, repo, name, url, ancestors = []):
    self.repo = repo
    self.name = name
    self.url = url
    self.ancestors = ancestors
    self.children = []

  def get(self):
    self.report()
    self.download()
    self.read()

  def report(self):
    if self.url:
      utils.log.info("  " * len(self.ancestors) + self.url)
    else:
      utils.log.info("  " * len(self.ancestors) + self.name)

  def download(self):
    pass

  def fresh(self):
    assert not self.ancestors
    c = ctx.db.execute("SELECT mtime FROM documents WHERE url = ?", [self.url])
    r = c.fetchone()
    return r and r[0] == self.mtime()

  def index_one(self):
    c = ctx.db.execute("INSERT OR REPLACE INTO documents(repo, name, url, mtime, indextime) VALUES (?, ?, ?, ?, STRFTIME('%s', 'now'))", [self.repo.name, self.name, self.url, self.mtime()])
    self.id = c.lastrowid

    if self.ancestors:
      ctx.db.executemany("INSERT INTO documents_tree VALUES (?, ?, ?)",
                         [[a().id, self.id, len(self.ancestors) - i] for (i, a) in enumerate(self.ancestors)])

    if self.text:
      ctx.db.execute("INSERT INTO documents_fts(rowid, content) VALUES (?, ?)", [self.id, self.text])

  def touch(self):
    assert not self.ancestors
    ctx.db.execute("UPDATE documents SET indextime = STRFTIME('%s', 'now') WHERE documents.rowid IN (SELECT child FROM documents_tree INNER JOIN documents ON documents_tree.parent = documents.rowid WHERE url = ?)", [self.url])


class LocalDocument(Document):
  def __init__(self, repo, name, url, ancestors = []):
    super(LocalDocument, self).__init__(repo, name, url, ancestors)
    self.unlink = False

  def mtime(self):
    return os.stat(self.basepath)[stat.ST_MTIME]

  def read(self):
    self.text = formats.read(self.basepath)

    for (filename, path) in formats.iter(self.basepath):
      child = LocalDocument(self.repo, os.path.split(filename)[1], None, self.ancestors + [weakref.ref(self)])
      child.basepath = path
      child.unlink = True
      self.children.append(child)

  def __del__(self):
    if self.unlink:
      os.unlink(self.basepath)


class RemoteDocument(LocalDocument):
  def download(self):
    self.basepath = utils.download(self.url)
    self.unlink = True


class Repo(workerpool.Worker):
  pass


class Spider(workerpool.WorkerPool):
  def __init__(self, repo, processcount = None):
    super(Spider, self).__init__(processcount, None)
    self.repo = repo

  def init_worker(self):
    ctx.db = db.DB(".db")
    self.repo.init_worker()

  def deinit_worker(self):
    self.repo.deinit_worker()
    ctx.db.close()

  def do_work(self, item):
    self.index_doc(item)

  def index(self):
    starttime = math.floor(time.time())

    self.start_processes()

    for doc in self.repo.walk():
      self.enqueue(doc)

    self.stop_processes()

    self.init_worker()
    ctx.db.execute("DELETE FROM documents WHERE repo = ? AND indextime < ?",
                   [self.repo.name, starttime])
    ctx.db.commit()
    self.deinit_worker()

  def index_doc(self, doc):
    if doc.fresh():
      doc.touch()
      ctx.db.commit()
      return

    try:
      self.do_index(doc)
      ctx.db.commit()

    except utils.DownloadException:
      ctx.db.rollback()
    except Exception:
      ctx.db.rollback()
      raise

  def dfs(self, doc, f):
    f(doc)
    failures = []
    for child in doc.children:
      try:
        self.dfs(child, f)
      except utils.DownloadException:
        failures.append(child)
    doc.children = [c for c in doc.children if c not in failures]

  def do_index(self, doc):
    def dlfn(doc):
      doc.get()

    def ifn(doc):
      doc.index_one()

    self.dfs(doc, dlfn)
    self.dfs(doc, ifn)

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
  multiprocessing.current_process().name = "mm"
  args = parse_args()
  repo = get_repo(args.repo)
  Spider(repo, args.workers).index()

ctx = type("Context", (), {})()

if __name__ == "__main__":
  import spider
  spider.main()
