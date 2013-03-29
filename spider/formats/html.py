#!/usr/bin/python

import lxml.html
import re

ws = re.compile("(\s|\xa0)+")

# br, option added
block_tags = ["address", "blockquote", "br", "div", "dd", "dl", "dt",
              "fieldset", "form", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
              "li", "noscript", "ol", "option", "p", "pre", "table", "tbody",
              "td", "tfoot", "th", "thead", "tr", "ul"]

def strip_ws(s):
  lines = s.split("\n")
  for i in range(len(lines)):
    lines[i] = ws.sub(" ", lines[i]).strip()
  return "\n".join([l for l in lines if l])

def render(e):
  def _render(e):
    if isinstance(e, lxml.html.HtmlComment):
      return
    if e.tag == "div" and e.get("class") == "mcePaste":
      return
    if e.tag in ["object", "script", "title", "video"]:
      return

    if e.tag in block_tags:
      yield "\n"

    if e.text:
      yield e.text.replace("\n", " ")

    for _e in e:
      for t in _render(_e):
        yield t

    if e.tag in block_tags:
      yield "\n"

    if e.tail:
      yield e.tail.replace("\n", " ")

  return strip_ws("".join(_render(e)))
