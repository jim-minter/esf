#!/usr/bin/python

import lxml.html
import os
import requests
import urlparse
import weakref

import config
import formats
import spider
import utils


class DrupalConnection(object):
  def __init__(self):
    self.s = requests.session()

  def url(self, href):
    return urlparse.urljoin(config.get("drupal-url"), href)

  def request(self, method, href, data = None, headers = None):
    return self.s.request(method, self.url(href), data = data,
                          headers = headers)

  def login(self, username, password):
    r = self.request("GET", "/user")
    html = lxml.html.fromstring(r.text)

    data = {}
    for i in html.xpath("//form[@id = 'user-login']//input"):
      data[i.get("name")] = i.get("value")

    data.update({"name": username, "pass": password})

    self.request("POST", "/user", data = data)

  def __getstate__(self):
    return { k: self.__dict__[k] for k in self.__dict__.keys() if k != "s" }


class DrupalRepo(object):
  name = "intranet"

  def __init__(self):
    self.conn = DrupalConnection()
    self.conn.login(config.get("drupal-user"),
                    config.get("drupal-pass").decode("base64"))

  def walk(self):
    href = "/admin/content"
    while href:
      response = self.conn.request("GET", href)
      html = lxml.html.fromstring(response.text)

      for row in html.xpath("//div[@class = 'content']//tbody//tr"):
        _name = row[1][0].text
        _href = row[1][0].get("href")
        _url = self.conn.url(_href)
        _type = row[2].text
        _mtime = utils.parsetime(row[5].text, "%Y-%m-%d %H:%M")
        yield DrupalPage(self, _name, _url, _type, _mtime)
      
      href = html.xpath("//li[@class = 'pager-next']/a/@href")
      if href:
        href = href[0]


class DrupalPage(spider.RemoteDocument):
  def __init__(self, repo, name, url, _type, mtime):
    super(DrupalPage, self).__init__(repo, name, url)
    self.type = _type
    self._mtime = mtime

  def mtime(self):
    return self._mtime

  def read(self):
    html = lxml.html.parse(self.basepath)

    if self.type in ["Department", "Office", "Project", "Wiki Page"]:
      self.text = body(html)
    elif self.type == "Webform":
      self.text = formats.html.strip_ws(body(html) + form(html))
    elif self.type == "Filedepot Folder":
      self.text = ""
    else:
      raise Exception("unknown content type %s" % self.type)

    if self.type == "Filedepot Folder":
      self.hrefs = filedepot_folder_files(html)
    else:
      self.hrefs = field_file_attachments(html)

    for href in self.hrefs:
      self.children.append(spider.RemoteDocument(self.repo, os.path.split(href)[1], href, self.ancestors + [weakref.ref(self)]))


def body(xml):
  _body = xml.xpath("//div[starts-with(@class, 'field field-name-body ')]")
  if _body:
    return formats.html.render(_body[0])
  else:
    return ""

def form(xml):
  _form = xml.xpath("//form[@class = 'webform-client-form']")
  if _form:
    return formats.html.render(_form[0])
  else:
    return ""

def field_file_attachments(xml):
  return xml.xpath("//div[starts-with(@class, 'field field-name-field-file-attachments ')]//div[starts-with(@class, 'field-item ')]//a/@href")

def filedepot_folder_files(xml):
  return xml.xpath("//div[starts-with(@class, 'field field-name-filedepot-folder-file ')]//div[starts-with(@class, 'field-item ')]//a/@href")
