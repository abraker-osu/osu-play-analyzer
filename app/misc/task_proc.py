import multiprocessing
import time


# Thanks: https://stackoverflow.com/a/35574016
class TaskProc():

    def __init__(self, num_workers=4):
        self.queue = multiprocessing.JoinableQueue()
        self.processes = [ multiprocessing.Process(target=self.process) for _ in range(num_workers) ]
        self.task = lambda item: None
    
    
    # Thanks: https://stackoverflow.com/a/65749012
    def __getstate__(self):
        # capture what is normally pickled
        state = self.__dict__.copy()

        # remove unpicklable/problematic variables 
        state['processes'] = None
        return state


    def start(self, task):
        self.task = task
        for p in self.processes:
            p.start()


    def add(self, item):
        self.queue.put(item)


    def process(self):
        while True:
            item = self.queue.get()
            if item is None:
                time.sleep(0.1)
                continue

            self.task(item)
            self.queue.task_done()


    def end(self):
        """ wait until queue is empty and terminate processes """
        self.queue.join()

        for p in self.processes:
            p.terminate()
