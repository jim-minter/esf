#!/usr/bin/python

import calendar
import os
import tempfile
import zipfile

def iter(f):
  with zipfile.ZipFile(f) as z:
    for zi in z.infolist():
      (fd, path) = tempfile.mkstemp()  # TODO: insecure
      os.close(fd)
      with open(path, "w") as f:       # TODO: do this piecewise
        f.write(z.read(zi))
      mtime = calendar.timegm(zi.date_time)
      os.utime(path, (mtime, mtime))
      yield (zi.filename, path)
