#!/usr/bin/python

import calendar
import time

def parsetime(string, format):
  return calendar.timegm(time.strptime(string, format))
