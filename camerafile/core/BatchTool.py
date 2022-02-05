import atexit
import os
from multiprocessing import Pool, Manager
from multiprocessing import current_process
from multiprocessing.queues import Queue

import camerafile.core.Configuration
from camerafile.console.ConsoleProgressBar import ConsoleProgressBar
from camerafile.console.StandardOutputWrapper import StdoutRecorder
from camerafile.core.Logging import init_only_console_logging, Logger
from camerafile.core.Resource import Resource
from camerafile.tools.ExifTool import ExifTool

LOGGER = Logger(__name__)


def execute_uni_process_batch(task, args, post_task, progress_bar):
    try:
        for arg in args:
            post_task(task(arg), progress_bar, replace=False)
    finally:
        progress_bar.stop()
        ExifTool.stop()


def on_worker_start(task):
    atexit.register(on_worker_end)
    Resource.init()
    Resource.current_multiprocess_task = task
    init_only_console_logging()
    LOGGER.debug("Start sub-process : " + str(os.getpid()))


def on_worker_end():
    ExifTool.stop()
    LOGGER.debug("Stop sub-process : " + str(os.getpid()))


def execute_task(*args):
    try:
        queue: Queue = args[0][0]
        queue.put([current_process().pid, args[0][1].file_access.relative_path])
        stdout_recorder = StdoutRecorder().start()
        if Resource.current_multiprocess_task is None:
            print("Multi-processing: no task defined in sub-process.")
        result = Resource.current_multiprocess_task(args[0][1])
        return result, stdout_recorder.stop()
    except BaseException as e:
        print(e)


def execute_multiprocess_batch(nb_process, task, args, post_task, progress_bar):
    m = Manager()
    queue = m.Queue()
    pool = Pool(nb_process, on_worker_start, (task,))
    nb_processed_elements = 0
    nb_elements = len(args)
    try:
        args = [(queue,) + (arg,) for arg in args]
        res_list = pool.imap_unordered(execute_task, args)

        for i in range(min(nb_process, nb_elements)):
            [n, detail] = queue.get(block=True, timeout=5)
            progress_bar.set_detail(n, detail)
            nb_processed_elements += 1

        for res in res_list:
            if nb_processed_elements < nb_elements:
                [n, detail] = queue.get(block=True, timeout=5)
                progress_bar.set_detail(n, detail)
                nb_processed_elements += 1

            result, stdout = res
            if stdout.strip() != "":
                print(stdout.strip())
            post_task(result, progress_bar, replace=True)
    except KeyboardInterrupt:
        try:
            LOGGER.info("Interrupted by user (Ctrl-C)")
            pool.terminate()
        except KeyboardInterrupt:
            LOGGER.info("Interrupted by user (Ctrl-C) 2")
    finally:
        try:
            pool.close()
            pool.join()
            progress_bar.stop()
            ExifTool.stop()
        except KeyboardInterrupt:
            LOGGER.info("Interrupted by user (Ctrl-C) 3")


class TaskWithProgression:

    def __init__(self, batch_title="", nb_sub_process=None):
        self.batch_title = batch_title
        self.nb_sub_process = nb_sub_process
        if self.nb_sub_process is None:
            self.nb_sub_process = camerafile.core.Configuration.NB_SUB_PROCESS

    def update_title(self, ):
        if self.nb_sub_process != 0:
            self.batch_title += " (max. {nb_sub_process} sub-processes)".format(nb_sub_process=self.nb_sub_process)
        return self.batch_title

    def initialize(self):
        pass

    def task_getter(self):
        def empty_task():
            pass

        return empty_task

    def post_task(self, **args):
        pass

    def arguments(self):
        return ()

    def finalize(self):
        pass

    def execute(self):
        self.initialize()
        task = self.task_getter()
        args = self.arguments()
        if len(args) != 0:
            progress_bar = ConsoleProgressBar(len(args), "", False)
            if self.nb_sub_process != 0:
                execute_multiprocess_batch(self.nb_sub_process, task, args, self.post_task, progress_bar)
            else:
                execute_uni_process_batch(task, args, self.post_task, progress_bar)

            self.finalize()

            LOGGER.info("{nb_elements} files processed in {duration}"
                        .format(nb_elements=progress_bar.position,
                                duration=progress_bar.processing_time))
        else:
            LOGGER.info("Nothing to do")
        return None
