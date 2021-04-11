import atexit
import logging
import multiprocessing
import shutil
import signal
from datetime import datetime
from functools import wraps
from multiprocessing import Pool
from multiprocessing import cpu_count

from camerafile import Constants
from camerafile.ConsoleProgressBar import ConsoleProgressBar
from camerafile.ExifTool import ExifTool
from camerafile.Logging import init_only_console_logging
from camerafile.Resource import Resource
from camerafile.StandardOutputWrapper import StdoutRecorder

LOGGER = logging.getLogger(__name__)


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
                LOGGER.info("|___ {nb_elements} files processed in {duration}".format(nb_elements=progress_bar.position,
                                                                                      duration=progress_bar.processing_time))
            return ret

        return with_progression_inner

    return with_progression_outer


def on_worker_start(task):
    print("Start init worker")
    #multiprocessing.set_start_method("spawn")
    #multiprocessing.set_forkserver_preload()
    #multiprocessing.spawn.is_forking()
    #import _winapi
    #_winapi.CreateProcess
    #pathos.multiprocessing.freeze_support()
    atexit.register(on_worker_end)
    Constants.task = task
    Resource.init()
    init_only_console_logging()
    signal.signal(signal.SIGINT, Constants.original_sigint_handler)
    print("End init worker")



def on_worker_end():
    ExifTool.stop()


def execute_task(*args):
    stdout_recorder = StdoutRecorder().start()
    result = Constants.task(*args)
    return result, stdout_recorder.stop()


def with_progression_multi_process(batch_title="", nb_process=cpu_count()):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args):
            display_starting_line()
            task, arguments, post_task = f(input_list, *args)
            args = arguments()
            LOGGER.info(">>>> {title} ({nb_process} sub-processes)".format(title=batch_title, nb_process=nb_process))
            if len(args) != 0:
                progress_bar = ConsoleProgressBar(len(args), "", False)
                pool = None
                sigint_stopper = signal.signal(signal.SIGINT, signal.SIG_IGN)
                try:
                    pool = Pool(nb_process, on_worker_start, (task(),))
                except:
                    LOGGER.info("Interrupted by user (Ctrl-C) 0")
                try:
                    res_list = pool.imap_unordered(execute_task, args)
                    print("End create multiprocesses tasks")
                    signal.signal(signal.SIGINT, Constants.original_sigint_handler)
                    # TODO : use a queue to know when processes are started correctly
                    # Before that, we should perform a non blocking wait, otherwise a Ctrl-C is badly managed
                    multiprocessing.Event().wait(10)
                    for res in res_list:
                        result, stdout = res
                        if stdout.strip() != "":
                            print(stdout.strip())
                        post_task(result, progress_bar)
                except KeyboardInterrupt:
                    try:
                        LOGGER.info("Interrupted by user (Ctrl-C)")
                        pool.terminate()
                    except:
                        LOGGER.info("Interrupted by user (Ctrl-C) 2")
                finally:
                    try:
                        pool.close()
                        pool.join()
                        progress_bar.stop()
                        ExifTool.stop()
                        LOGGER.info(
                            "|___ {nb_elements} files processed in {duration}".format(nb_elements=progress_bar.position,
                                                                                      duration=progress_bar.processing_time))
                    except:
                        LOGGER.info("Interrupted by user (Ctrl-C) 3")
            else:
                LOGGER.info("|___ Nothing to do")
            return None

        return with_progression_inner

    return with_progression_outer


def display_starting_line():
    console_width = shutil.get_terminal_size((80, 20)).columns - 1
    line = '{text:{fill}{align}{width}}'.format(
        text='', fill='-', align='<', width=console_width,
    )
    print(line)


def display_ending_line():
    console_width = shutil.get_terminal_size((80, 20)).columns - 1
    line = '{text:{fill}{align}{width}}\n'.format(
        text='', fill='-', align='<', width=console_width,
    )
    print(line)


class StatusLine:
    def __init__(self, message, update_freq=1):
        self.starting_time = datetime.now().strftime('%H:%M:%S')
        self.message = message
        self.nb_update = 0
        self.update_freq = update_freq

    def update(self, **args):
        if self.nb_update % self.update_freq == 0:
            print("\r[" + self.starting_time + "] " + self.message.format(**args), end='')
        self.nb_update += 1

    def end(self, **args):
        print("\r[" + self.starting_time + "] " + self.message.format(**args))
