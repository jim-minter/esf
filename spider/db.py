#!/usr/bin/python

import argparse
import sqlite3
import os

class DB(object):
  def __init__(self, name):
    self.name = name
    self.connect()

  def checkpoint(self, mode):
    if mode.upper() not in ["", "FULL", "PASSIVE", "RESTART"]:
      raise Exception

    self.execute("PRAGMA wal_checkpoint(%s)" % mode)

  def close(self):
    self.db.close()

  def commit(self):
    self.db.commit()

  def connect(self):
    self.db = sqlite3.connect(self.name)
    self.db.text_factory = str
    self.execute("PRAGMA recursive_triggers = 1")

  def create(self, sql_script):
    self.close()
    os.unlink(self.name)
    self.connect()
    self.executescript(sql_script)
    
  def execute(self, sql, *parameters):
    while True:
      try:
        rv = self.db.execute(sql, *parameters)
      except sqlite3.OperationalError, e:
        if e.message == "database is locked":
          continue
        raise
      return rv

  def executemany(self, sql, *parameters):
    while True:
      try:
        rv = self.db.executemany(sql, *parameters)
      except sqlite3.OperationalError, e:
        if e.message == "database is locked":
          continue
        raise
      return rv

  def executescript(self, sql_script):
    self.db.executescript(sql_script)

  def rollback(self):
    self.db.rollback()

def parse_args():
  ap = argparse.ArgumentParser()
  sp = ap.add_subparsers()
  checkpointparser = sp.add_parser("checkpoint")
  checkpointparser.set_defaults(cmd = "checkpoint")
  createparser = sp.add_parser("create")
  createparser.set_defaults(cmd = "create")
  queryparser = sp.add_parser("query")
  queryparser.set_defaults(cmd = "query")
  queryparser.add_argument("querystring")
  return ap.parse_args()

def main():
  args = parse_args()
  db = DB(".db")

  if args.cmd == "checkpoint":
    db.checkpoint("RESTART")

  elif args.cmd == "create":
    with open("db-schema.sql") as f:
      sql = f.read()

    db.create(sql)

  elif args.cmd == "query":
    for row in db.execute("SELECT DISTINCT url FROM documents, documents_fts WHERE documents.rowid = documents_fts.rowid AND content MATCH ? ORDER BY url", [args.querystring]):
      print row[0]

if __name__ == "__main__":
  main()
