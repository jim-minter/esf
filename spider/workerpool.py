#!/usr/bin/python

import config
import multiprocessing
import utils


class Worker(object):
  def init_worker(self):
    pass

  def deinit_worker(self):
    pass


class WorkerPool(Worker):
  def __init__(self, processcount = None, maxsize = 0):
    if not processcount or processcount < 1:
      processcount = multiprocessing.cpu_count()

    if maxsize is None:
      maxsize = 4 * processcount

    self.queue = multiprocessing.Queue(maxsize)
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

  def do_work(self, item):
    pass

  def worker(self):
    self.init_worker()

    for item in iter(self.queue.get, None):
      try:
        self.do_work(item)
      except Exception:
        utils.log.exception("")
        if config.getboolean("errors-fatal"):
          raise SystemExit
      except KeyboardInterrupt:
        utils.log.exception("")
        raise SystemExit

    self.deinit_worker()

  def enqueue(self, item):
    self.queue.put(item)
