#!/usr/bin/python

import calendar
import httplib
import lxml.html
import os
import re
import time
import traceback
import urllib

import config
import spider


class Connection(object):
  def __init__(self):
    self.conn = httplib.HTTPSConnection(config.get("drupal-host"))
    self.cookie = None

  def request(self, method, url, body = None, headers = {}):
    if self.cookie:
      headers["Cookie"] = self.cookie
    self.conn.request(method, url, body, headers)

    response = self.conn.getresponse()
    if response.getheader("Set-Cookie"):
      self.cookie = response.getheader("Set-Cookie").split(";")[0]
    return response

  def login(self, username, password):
    response = self.request("GET", "/user")
    html = lxml.html.fromstring(response.read())

    params = {}
    for i in html.xpath("//form[@id = 'user-login']//input"):
      params[i.get("name")] = i.get("value")

    params.update({"name": username, "pass": password})

    self.request("POST", "/user", urllib.urlencode(params),
                 {"Content-Type": "application/x-www-form-urlencoded"})


class DrupalRepo(spider.Repo):
  name = "intranet"

  def __init__(self, username, password):
    super(DrupalRepo, self).__init__()

  def init_worker(self):
    self.ctx.conn = Connection()
    self.ctx.conn.login(username, password)

  def walk(self):
    href = "/admin/content"
    while href:
      response = self.ctx.conn.request("GET", href)
      html = lxml.html.fromstring(response.read())

      for row in html.xpath("//div[@class = 'content']//tbody//tr"):
        _name = row[1][0].text
        _href = row[1][0].get("href")
        _url = "https://" + config.get("drupal-host") + _href
        _type = row[2].text
        _mtime = calendar.timegm(time.strptime(row[5].text, "%Y-%m-%d %H:%M"))
        yield DrupalPage(self, _name, _url, _type, _mtime, _href)
      
      href = html.xpath("//li[@class = 'pager-next']/a/@href")
      if href:
        href = href[0]


class DrupalPage(spider.Document):
  def __init__(self, repo, name, url, _type, mtime, href):
    super(DrupalPage, self).__init__(repo, name, url)
    self.type = _type
    self._mtime = mtime
    self.href = href

  def mtime(self):
    return self._mtime

  def read(self):
    response = self.repo.ctx.conn.request("GET", self.href)
    html = lxml.html.fromstring(response.read())
    if self.type in ["Department", "Office", "Wiki Page"]:
      self.text = body(html)
    elif self.type == "Webform":
      self.text = strip_ws(body(html) + form(html))

    if self.type == "Filedepot Folder":
      self.hrefs = filedepot_folder_files(html)
    else:
      self.hrefs = field_file_attachments(html)

  def children(self):
    for href in self.hrefs:
      try:
        yield spider.RemoteDocument(self.repo, os.path.split(href)[1], href, self.ancestors + [self])
      except Exception, e:
        print "ERROR: %s on %s, continuing" % (e.message, href)
        traceback.print_exc()


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

def render_html(e):
  def _render_html(e):
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
      for t in _render_html(_e):
        yield t

    if e.tag in block_tags:
      yield "\n"

    if e.tail:
      yield e.tail.replace("\n", " ")

  return strip_ws("".join(_render_html(e)))

def body(xml):
  _body = xml.xpath("//div[starts-with(@class, 'field field-name-body ')]")
  if _body:
    return render_html(_body[0])
  else:
    return ""

def form(xml):
  _form = xml.xpath("//form[@class = 'webform-client-form']")
  if _form:
    return render_html(_form[0])
  else:
    return ""

def field_file_attachments(xml):
  return xml.xpath("//div[starts-with(@class, 'field field-name-field-file-attachments ')]//div[starts-with(@class, 'field-item ')]//a/@href")

def filedepot_folder_files(xml):
  return xml.xpath("//div[starts-with(@class, 'field field-name-filedepot-folder-file ')]//div[starts-with(@class, 'field-item ')]//a/@href")

if __name__ == "__main__":
  username = config.get("drupal-user")
  password = config.get("drupal-pass").decode("base64")

  spider.Spider(DrupalRepo(username, password), 0).index()
