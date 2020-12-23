import logging
import shutil
import signal
from functools import wraps
from multiprocessing import Pool
from camerafile.ConsoleProgressBar import ConsoleProgressBar
from camerafile.ExifTool import ExifTool

LOGGER = logging.getLogger(__name__)


def with_progression(batch_title=""):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args, progress_bar=None):

            display_starting_line()
            progress_bar = ConsoleProgressBar(len(input_list), batch_title)
            LOGGER.info("Start batch <{title}>".format(title=batch_title))
            try:
                ret = f(input_list, *args, progress_bar)
            finally:
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("End batch <{title}>".format(title=batch_title))
                display_ending_line()
            return ret

        return with_progression_inner

    return with_progression_outer


def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def with_progression_thread(batch_title="", threads=1):
    def with_progression_outer(f):
        @wraps(f)
        def with_progression_inner(input_list, *args):

            display_starting_line()
            task, arguments, post_task = f(input_list, *args)
            args = arguments()
            progress_bar = ConsoleProgressBar(len(args), batch_title)
            LOGGER.info("Start batch (multi-process) <{title}>".format(title=batch_title))
            pool = Pool(threads, init_worker)
            try:
                res_list = pool.imap_unordered(task(), args)
                for res in res_list:
                    post_task(res, progress_bar)
            except KeyboardInterrupt:
                LOGGER.info("Interrupted by user (Ctrl-C)")
                pool.terminate()
            finally:
                pool.close()
                pool.join()
                progress_bar.stop()
                ExifTool.stop()
                LOGGER.info("End batch <{title}>".format(title=batch_title))
                display_ending_line()
            return None

        return with_progression_inner

    return with_progression_outer


def display_starting_line():
    console_width = shutil.get_terminal_size((80, 20)).columns - 1
    line = '\n{text:{fill}{align}{width}}'.format(
        text='', fill='-', align='<', width=console_width,
    )
    print(line)


def display_ending_line():
    console_width = shutil.get_terminal_size((80, 20)).columns - 1
    line = '{text:{fill}{align}{width}}\n'.format(
        text='', fill='-', align='<', width=console_width,
    )
    print(line)
