#!/usr/bin/python

import lxml.etree
import zipfile

def read(f):
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
