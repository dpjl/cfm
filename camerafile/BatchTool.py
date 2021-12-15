import atexit
import os
import shutil
from functools import wraps
from multiprocessing import Pool
from multiprocessing import cpu_count
from camerafile.ConsoleProgressBar import ConsoleProgressBar
from camerafile.ExifTool import ExifTool
from camerafile.Logging import init_only_console_logging, Logger
from camerafile.Resource import Resource
from camerafile.StandardOutputWrapper import StdoutRecorder

LOGGER = Logger(__name__)


def with_progression(title="", short_title=""):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args, progress_bar=None):

            display_starting_line()
            progress_bar = ConsoleProgressBar(len(input_list), "", False)
            LOGGER.info(">>>> {title}".format(title=title))
            try:
                ret = f(input_list, *args, progress_bar)
            finally:
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("{nb_elements} files processed in {duration}"
                            .format(nb_elements=progress_bar.position,
                                    duration=progress_bar.processing_time))
            return ret

        return with_progression_inner

    return with_progression_outer


def execute_batch(task, args, post_task, progress_bar):
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
    stdout_recorder = StdoutRecorder().start()
    if Resource.current_multiprocess_task is None:
        print("Multi-processing: no task defined in sub-process.")
    result = Resource.current_multiprocess_task(*args)
    return result, stdout_recorder.stop()


def execute_multiprocess_batch(nb_process, task, args, post_task, progress_bar):
    pool = Pool(nb_process, on_worker_start, (task,))
    try:
        res_list = pool.imap_unordered(execute_task, args)
        for res in res_list:
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

    def __init__(self, batch_title="", nb_sub_process=cpu_count()):
        self.batch_title = batch_title
        self.nb_sub_process = nb_sub_process

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
                execute_batch(task, args, self.post_task, progress_bar)

            self.finalize()

            LOGGER.info("{nb_elements} files processed in {duration}"
                        .format(nb_elements=progress_bar.position,
                                duration=progress_bar.processing_time))
        else:
            LOGGER.info("Nothing to do")
        return None
