#!/usr/bin/python

import ConfigParser

def get(option):
  return config.get("config", option)

def getboolean(option):
  return config.getboolean("config", option)

config = ConfigParser.RawConfigParser()
config.read(".config")
