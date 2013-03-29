#!/usr/bin/python

import config
import multiprocessing
import traceback

class WorkerPool(object):
  def __init__(self, processcount = 4):
    self.queue = multiprocessing.Queue()
    self.processcount = processcount
    self.processs = []

  def start_processes(self):
    for i in range(self.processcount):
      p = multiprocessing.Process(target = self.worker)
      p.start()
      self.processs.append(p)

  def stop_processes(self):
    for p in self.processs:
      self.queue.put(None)

    self.queue.close()
    self.queue.join_thread()

    for p in self.processs:
      p.join()

    self.processs = []

  def init_worker(self):
    pass

  def deinit_worker(self):
    pass

  def do_work(self, item):
    pass

  def worker(self):
    self.init_worker()

    for item in iter(self.queue.get, None):
      try:
        self.do_work(item)
      except Exception, e:
        print "ERROR: %s" % e.message
        traceback.print_exc()
        if config.get("errors-fatal"):
          raise

    self.deinit_worker()

  def enqueue(self, item):
    if self.processcount:
      self.queue.put(item)
    else:
      self.do_work(item)
