#!/usr/bin/python

def read(f):
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
