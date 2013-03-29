#!/usr/bin/python

def read(f):
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
