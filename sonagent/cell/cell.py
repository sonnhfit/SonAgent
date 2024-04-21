import logging
import threading
import time

logger = logging.getLogger(__name__)


class BaseCell(threading.Thread):
    def __init__(self, thread_name):
        super().__init__()
        self.thread_name = thread_name

    def run(self):
        print(f"{self.thread_name} start.")
        # simulate some work
        for i in range(5):
            print(f"{self.thread_name}: job {i}")
            time.sleep(1)
        print(f"{self.thread_name} done.")
