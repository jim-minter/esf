#!/usr/bin/python

import calendar
import functools
import logging
import os
import requests
import tempfile
import time
import weakref

import spider


class DownloadException(Exception):
  pass


def download(url):
  response = spider.s.get(url, stream = True)
  if response.status_code != 200:
    raise DownloadException()

  (fd, path) = tempfile.mkstemp()
  f = os.fdopen(fd, "w")

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
    os.unlink(path)
    raise Exception("short read")

  mtime = parsetime(response.headers["Last-Modified"],
                    "%a, %d %b %Y %H:%M:%S %Z")
  os.utime(path, (mtime, mtime))

  return path

def simple_memo(f):
  cache = weakref.WeakKeyDictionary()
  @functools.wraps(f)
  def wrap(self):
    if self not in cache:
      cache[self] = f(self)
    return cache[self]
  return wrap

def parsetime(string, format):
  return calendar.timegm(time.strptime(string, format))

def init_log():
  log = logging.getLogger()
  logging.basicConfig(format = "%(processName)s %(asctime)s %(levelname)s %(message)s", datefmt = "%Y/%b/%d-%H:%M:%S")
  log.setLevel(0)
  return log

log = init_log()
