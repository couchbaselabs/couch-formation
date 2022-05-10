##
##

import multiprocessing
import threading
from itertools import cycle
import time
import sys


class spinner(object):

    def __init__(self):
        self.run_flag = multiprocessing.Value('i')
        self.run_flag.value = 0
        self.sequence = ['-', '\\', '|', '/']
        self.char_cycle = cycle(self.sequence)
        self.run_thread = threading.Thread(target=self.run, args=(self.run_flag,))

    def run(self, run_flag):
        end_char = '\r'

        while run_flag.value == 1:
            print(f" please wait {next(self.char_cycle)}", end=end_char)
            time.sleep(0.5)

    def start(self):
        self.run_flag.value = 1
        self.run_thread.start()

    def stop(self):
        self.run_flag.value = 0
        self.run_thread.join()
        sys.stdout.write("\033[K")
