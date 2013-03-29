#!/usr/bin/python

# requires minimum pypoppler-0.12.1-22

import poppler

def read(f):
  doc = poppler.document_new_from_file("file://" + f, None)
  pages = []
  for i in range(doc.get_n_pages()):
    page = doc.get_page(i)
    pages.append(unicode(page.get_text()))
  return "".join(pages)
