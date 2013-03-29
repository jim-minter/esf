#!/usr/bin/python

import tarfile
import zipfile

import docx
import html
import odx
import pdf
import pptx
import tar
import zip

# txt, html
# audio/video: m4v, mov, mp[34], og[agvx]
# legacy MS formats: doc, ppt
# spreadsheets(?): ods, xls[mx]?
# templates(?): ot[pst]

def iter(f, _type = None):
  if not _type:
    _type = type(f)

  if _type == "zip":
    for (filename, path) in zip.iter(f):
      yield (filename, path)
  elif _type == "tar":
    for (filename, path) in tar.iter(f):
      yield (filename, path)

def read(f, _type = None):
  if not _type:
    _type = type(f)

  if _type == "docx":
    return docx.read(f)
  elif _type == "pdf":
    return pdf.read(f)
  elif _type == "pptx":
    return pptx.read(f)
  elif _type in ["odp", "odt"]:
    return odx.read(f)
  else:
    return None

def type(f):
  with open(f, "r") as _f:
    buf = _f.read(4)

  if buf[:4] == "%PDF":
    return "pdf"
  elif zipfile.is_zipfile(f):
    with zipfile.ZipFile(f) as z:
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
  elif tarfile.is_tarfile(f):
    return "tar"
  else:
    return None
