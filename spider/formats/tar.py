#!/usr/bin/python

import calendar
import os
import tarfile
import tempfile

def iter(f):
  with tarfile.open(f) as t:
    for ti in t.getmembers():
      if not ti.isfile():
        continue
      (fd, path) = tempfile.mkstemp()  # TODO: insecure
      os.close(fd)
      with open(path, "w") as f:       # TODO: do this piecewise
        f.write(t.extractfile(ti).read())
      os.utime(path, (ti.mtime, ti.mtime))
      yield (ti.name, path)
