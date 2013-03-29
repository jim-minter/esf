#!/usr/bin/python

import config
import multiprocessing
import utils

class WorkerPool(object):
  def __init__(self, processcount = 4):
    self.queue = multiprocessing.Queue()
    self.processcount = processcount
    self.processes = []

  def start_processes(self):
    for i in range(self.processcount):
      p = multiprocessing.Process(target = self.worker, name = "p%u" % (i + 1))
      p.start()
      self.processes.append(p)

  def stop_processes(self):
    for p in self.processes:
      self.queue.put(None)

    self.queue.close()
    self.queue.join_thread()

    for p in self.processes:
      p.join()

    self.processes = []

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
      except Exception:
        utils.log.exception("")
        if config.get("errors-fatal"):
          raise SystemExit

    self.deinit_worker()

  def enqueue(self, item):
    if self.processcount:
      self.queue.put(item)
    else:
      self.do_work(item)
