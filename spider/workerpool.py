#!/usr/bin/python

import Queue
import threading

class WorkerPool(object):
  def __init__(self, threadcount = 4):
    self.ctx = threading.local()
    self.queue = Queue.Queue()
    self.sentinel = object()
    self.threadcount = threadcount
    self.threads = []

  def start_threads(self):
    for i in range(self.threadcount):
      t = threading.Thread(target = self.worker, name = i)
      t.daemon = True
      t.start()
      self.threads.append(t)

  def stop_threads(self):
    for t in self.threads:
      self.queue.put(self.sentinel)

    for t in self.threads:
      while t.isAlive():
        t.join(1)

    self.threads = []

  def init_worker(self):
    pass

  def deinit_worker(self):
    pass

  def do_work(self, item):
    item[0](*item[1:])

  def worker(self):
    self.init_worker()

    for item in iter(self.queue.get, self.sentinel):
      try:
        self.do_work(item)
      except Exception, e:
        print "ERROR: %s" % e.message
        traceback.print_exc()
      self.queue.task_done()
    self.queue.task_done()

    self.deinit_worker()

  def enqueue(self, item):
    if self.threadcount:
      self.queue.put(item)
    else:
      self.do_work(item)
