#!/usr/bin/python

# requires minimum pypoppler-0.12.1-22

import calendar
import itertools
import lxml.etree
import math
import poppler
import requests
import stat
import os
import tarfile
import threading
import tempfile
import time
import traceback
import zipfile

import config
import db
import workerpool

def read_docx(f):
  def walk_xml(xml, text):
    if xml.text:
      text.append(xml.text)

    for e in xml:
      walk_xml(e, text)

    if xml.tail:
      text.append(xml.tail)

    if xml.tag == "{%s}p" % xml.nsmap["w"]:
      text.append("\n")

  with zipfile.ZipFile(f) as z:
    xml = lxml.etree.fromstring(z.read("word/document.xml"))
  text_e = xml.find("w:body", xml.nsmap)

  text = []
  walk_xml(text_e, text)
  return "".join(text)

def read_odx(f):
  def walk_xml(xml, text):
    if xml.tag == "{%s}tracked-changes" % xml.nsmap["text"] \
          or xml.tag == "{%s}page-number" % xml.nsmap["text"]:
      return

    if xml.tag == "{%s}s" % xml.nsmap["text"]:
      text.append(" ")

    if xml.tag == "{%s}t" % xml.nsmap["text"]:
      text.append("\t")

    if xml.tag == "{%s}line-break" % xml.nsmap["text"]:
      text.append("\n")

    if xml.text:
      text.append(xml.text)

    for e in xml:
      walk_xml(e, text)

    if xml.tail:
      text.append(xml.tail)

    if xml.tag == "{%s}p" % xml.nsmap["text"] or \
          xml.tag == "{%s}h" % xml.nsmap["text"]:
      text.append("\n")

  with zipfile.ZipFile(f) as z:
    xml = lxml.etree.fromstring(z.read("content.xml"))
  text_e = xml.find("office:body", xml.nsmap)

  text = []
  walk_xml(text_e, text)
  return "".join(text)

def read_pdf(f):
  doc = poppler.document_new_from_file("file://" + f, None)
  pages = []
  for i in range(doc.get_n_pages()):
    page = doc.get_page(i)
    pages.append(unicode(page.get_text()))
  return "".join(pages)

def read_pptx(f):
  def walk_xml(xml, text):
    if xml.tag == "{%s}tableStyleId" % xml.nsmap["a"]:
      return

    if xml.text:
      text.append(xml.text)

    for e in xml:
      walk_xml(e, text)

    if xml.tail:
      text.append(xml.tail)

    if xml.tag == "{%s}p" % xml.nsmap["a"]:
      text.append("\n")

  text = []

  with zipfile.ZipFile(f) as z:
    for i in itertools.count(1):
      if not "ppt/slides/slide%u.xml" % i in z.namelist():
        break

      xml = lxml.etree.fromstring(z.read("ppt/slides/slide%u.xml" % i))
      text_e = xml.find("p:cSld", xml.nsmap)
      walk_xml(text_e, text)

  return "".join(text)


class Document(object):
  def __init__(self, repo, name, url, ancestors = []):
    self.repo = repo
    self.name = name
    self.url = url
    self.ancestors = ancestors

  def interesting(self):
    return True

  def done(self):
    pass


class LocalDocument(Document):
  def __init__(self, repo, name, url, basepath, ancestors = []):
    super(LocalDocument, self).__init__(repo, name, url, ancestors)
    self.basepath = basepath
    self.type = self.type()

  def type(self):
    with open(self.basepath, "r") as f:
      buf = f.read(4)

    # txt, html
    # audio/video: m4v, mov, mp[34], og[agvx]
    # legacy MS formats: doc, ppt
    # spreadsheets(?): ods, xls[mx]?
    # templates(?): ot[pst]
    if buf[:4] == "%PDF":
      return "pdf"
    elif zipfile.is_zipfile(self.basepath):
      with zipfile.ZipFile(self.basepath) as z:
        if "mimetype" in z.namelist():
          mimetype = z.read("mimetype")
          if mimetype == "application/vnd.oasis.opendocument.presentation":
            return "odp"
          elif mimetype == "application/vnd.oasis.opendocument.text":
            return "odt"
          else:
            return None

        if "[Content_Types].xml" in z.namelist():
          if "word/document.xml" in z.namelist():
            return "docx"
          elif "ppt/presentation.xml" in z.namelist():
            return "pptx"
          else:
            return None

      return "zip"
    elif tarfile.is_tarfile(self.basepath):
      return "tar"
    else:
      return None

  def interesting(self):
    return self.type is not None

  def mtime(self):
    return os.stat(self.basepath)[stat.ST_MTIME]

  def read(self):
    self.text = None
    if self.type == "docx":
      self.text = read_docx(self.basepath)
    elif self.type == "pdf":
      self.text = read_pdf(self.basepath)
    elif self.type == "pptx":
      self.text = read_pptx(self.basepath)
    elif self.type in ["odp", "odt"]:
      self.text = read_odx(self.basepath)

  def children(self):
    if self.type == "zip":
      with zipfile.ZipFile(self.basepath) as z:
        for zi in z.infolist():
          (fd, path) = tempfile.mkstemp()  # TODO: insecure
          os.close(fd)
          with open(path, "w") as f:       # TODO: do this piecewise
            f.write(z.read(zi))
          mtime = calendar.timegm(zi.date_time)
          os.utime(path, (mtime, mtime))
          child = LocalDocument(self.repo, os.path.split(zi.filename)[1], None, path, self.ancestors + [self])
          yield child
          os.unlink(path)
    elif self.type == "tar":
      with tarfile.open(self.basepath) as t:
        for ti in t.getmembers():
          if not ti.isfile():
            continue
          (fd, path) = tempfile.mkstemp()  # TODO: insecure
          os.close(fd)
          with open(path, "w") as f:       # TODO: do this piecewise
            f.write(t.extractfile(ti).read())
          os.utime(path, (ti.mtime, ti.mtime))
          child = LocalDocument(self.repo, os.path.split(ti.name)[1], None, path, self.ancestors + [self])
          yield child
          os.unlink(path)
  

class RemoteDocument(LocalDocument):
  def __init__(self, repo, name, url, ancestors = []):
    self.download(url)
    super(RemoteDocument, self).__init__(repo, name, url, self.basepath, ancestors)

  def download(self, url):
    (fd, self.basepath) = tempfile.mkstemp()  # TODO: insecure
    os.close(fd)
    f = open(self.basepath, "w")

    response = requests.get(url, stream = True, verify = False)
    if response.status_code != 200:
      raise Exception("can't download")
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

    mtime = calendar.timegm(time.strptime(response.headers["Last-Modified"],
                                          "%a, %d %b %Y %H:%M:%S %Z"))
    os.utime(self.basepath, (mtime, mtime))

  def done(self):
    os.unlink(self.basepath)


class Spider(workerpool.WorkerPool):
  def __init__(self, repo, threadcount = 4):
    self.repo = repo
    super(Spider, self).__init__(threadcount)

  def init_worker(self):
    self.repo.init_worker()
    self.ctx.db = db.DB(".db")

  def deinit_worker(self):
    self.repo.deinit_worker()
    self.ctx.db.close()

  def index(self):
    self.start_threads()

    now = math.floor(time.time())

    for doc in self.repo.walk():
      self.enqueue([self.index_doc, doc])

    self.stop_threads()

    self.ctx.db.execute("DELETE FROM documents WHERE repo = ? AND indextime < ?",
                        [self.repo.name, now])
    self.ctx.db.commit()

  def touch(self, doc):
    self.ctx.db.execute("UPDATE documents SET indextime = STRFTIME('%s', 'now') WHERE url = ?", [doc.url])
    self.ctx.db.commit()

  def fresh(self, doc):
    c = self.ctx.db.execute("SELECT mtime FROM documents WHERE url = ?", [doc.url])
    r = c.fetchone()
    return r and r[0] == doc.mtime()

  def index_doc(self, doc):
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
      self.ctx.db.rollback()

    self.ctx.db.commit()

  def do_index(self, doc):
    if not doc.interesting():
      return

    if doc.url:
      print doc.url
    else:
      print "  " * len(doc.ancestors) + doc.name

    c = self.ctx.db.execute("INSERT OR REPLACE INTO documents(repo, name, url, mtime, indextime) VALUES (?, ?, ?, ?, STRFTIME('%s', 'now'))", [doc.repo.name, doc.name, doc.url, doc.mtime()])
    doc.id = c.lastrowid

    if doc.ancestors:
      self.ctx.db.executemany("INSERT INTO documents_tree VALUES (?, ?, ?)",
                              [[a.id, doc.id, len(doc.ancestors) - i] for (i, a) in enumerate(doc.ancestors)])

    doc.read()
    if doc.text:
      self.ctx.db.execute("INSERT INTO documents_fts(rowid, content) VALUES (?, ?)", [doc.id, doc.text])

    for child in doc.children():
      self.do_index(child)
        
    doc.done()


class Repo(object):
  def __init__(self):
    self.ctx = threading.local()
    self.init_worker()

  def init_worker(self):
    pass

  def deinit_worker(self):
    pass

class PntRepo(Repo):
  name = "pnt"

  def walk(self):
    base = config.get("pnt-filebase")
    for dirpath, dirnames, filenames in os.walk(base):
      if dirpath == base:
        dirnames[:] = [d for d in dirnames if d != "Archive"]

      dirnames[:] = sorted(dirnames)

      for f in sorted(filenames):
        p = os.path.join(dirpath, f)
        url = os.path.join(config.get("pnt-urlbase"),
                           os.path.relpath(p, base))

        yield LocalDocument(self, f, url, p)


def main():
  Spider(PntRepo()).index()

if __name__ == "__main__":
  main()
