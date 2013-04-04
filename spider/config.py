#!/usr/bin/python

import ConfigParser

defaults = { "errors-fatal": "false" }

class Config:
  def __init__(self, section = "config"):
    self.config = ConfigParser.RawConfigParser(defaults)
    self.config.read(".config")
    self.section = section

  def get(self, option):
    return self.config.get(self.section, option)

  def getboolean(self, option):
    return self.config.getboolean(self.section, option)

config = Config()
