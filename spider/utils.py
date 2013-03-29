#!/usr/bin/python

import calendar
import functools
import os
import requests
import sys
import tempfile
import time

class DownloadException(Exception):
  pass


def download(url):
  response = requests.get(url, prefetch = False, verify = False)
  if response.status_code != 200:
    raise DownloadException()

  (fd, path) = tempfile.mkstemp()
  f = os.fdopen(fd)

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

def log(s):
  sys.stderr.write(s)

def memo(f):
  cache = {}
  @functools.wraps(f)
  def wrap(*args):
    if args not in cache:
      cache[args] = f(*args)
    return cache[args]
  return wrap

def parsetime(string, format):
  return calendar.timegm(time.strptime(string, format))
