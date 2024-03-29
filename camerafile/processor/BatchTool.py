import threading
import traceback
from multiprocessing import Pool, cpu_count
from multiprocessing import Queue
from multiprocessing import current_process
from queue import Empty
from typing import List

from camerafile.console.ConsoleProgressBar import ConsoleProgressBar
from camerafile.console.StandardOutputWrapper import StdoutRecorder
from camerafile.core.Logging import Logger
from camerafile.mdtools.ExifToolReader import ExifTool

DEFAULT_NB_SUB_PROCESS = cpu_count()

LOGGER = Logger(__name__)


class BatchElement:

    def __init__(self, args, info):
        self.args = args
        self.info = info
        self.error = None
        self.result = None


class TaskWithProgression:
    current_multiprocess_task = None
    details_queue = None
    custom_owe = None
    stopped_update_details_thread = True

    def __init__(self, batch_title="", nb_sub_process=None, on_worker_start=None, on_worker_start_args=(),
                 on_worker_end=None, stderr_file=None, stdout_file=None):
        self.batch_title = batch_title
        self.nb_sub_process = nb_sub_process
        self.custom_ows = on_worker_start
        self.custo_ows_args = on_worker_start_args
        self.custom_owe = on_worker_end
        self.stderr_file = stderr_file
        self.stdout_file = stdout_file
        self.nb_errors = 0
        self.stdout_nb_lines = 0
        if self.nb_sub_process is None:
            self.nb_sub_process = DEFAULT_NB_SUB_PROCESS

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

    def arguments(self) -> List[BatchElement]:
        return []

    def finalize(self):
        pass

    def display_final_status(self, progress_bar):
        print("{nb_elements} elements processed in {duration}"
              .format(nb_elements=progress_bar.position, duration=progress_bar.processing_time))

    def execute(self):
        self.initialize()
        task = self.task_getter()
        args = self.arguments()
        if len(args) != 0:
            pb = ConsoleProgressBar(len(args))
            if self.nb_sub_process != 0:
                self.execute_multiprocess_batch(self.nb_sub_process, task, args, self.post_task, pb)
            else:
                self.execute_uni_process_batch(task, args, self.post_task, pb)
            self.finalize()
            self.display_final_status(pb)
        else:
            LOGGER.info("Nothing to do")
            self.finalize()
        return None

    def execute_uni_process_batch(self, task, args_list: List[BatchElement], post_task,
                                  progress_bar: ConsoleProgressBar):
        pid = current_process().pid
        try:
            for batch_element in args_list:
                progress_bar.set_detail(pid, batch_element.info)
                batch_element = task(batch_element)
                post_task(batch_element.result, progress_bar, replace=False)
        finally:
            progress_bar.stop()
            ExifTool.stop()

    @staticmethod
    def execute_task(batch_element: BatchElement):
        try:
            queue: Queue = TaskWithProgression.details_queue
            if queue is not None:
                queue.put([current_process().pid, batch_element.info])
            stdout_recorder = StdoutRecorder().start()
            if TaskWithProgression.current_multiprocess_task is None:
                print("Multi-processing: no task defined in sub-process.")
                return None, stdout_recorder.stop()
            batch_element = TaskWithProgression.current_multiprocess_task(batch_element)
            return batch_element, stdout_recorder.stop()
        except BaseException:
            return batch_element, traceback.format_exc()

    @staticmethod
    def on_worker_start(task, details_queue, custom_ows=None, custom_ows_args=(),
                        custom_owe=None):
        stdout_recorder = StdoutRecorder().start()
        TaskWithProgression.current_multiprocess_task = task
        TaskWithProgression.details_queue = details_queue
        TaskWithProgression.custom_owe = custom_owe
        if custom_ows:
            custom_ows(*custom_ows_args)
        if details_queue is not None:
            details_queue.put(stdout_recorder.stop())

    @staticmethod
    def on_worker_end(identifier):
        stdout_recorder = StdoutRecorder().start()
        LOGGER.debug(f"On worker end call with id: {identifier}")
        if TaskWithProgression.custom_owe:
            TaskWithProgression.custom_owe()
        if TaskWithProgression.details_queue is not None:
            TaskWithProgression.details_queue.put(stdout_recorder.stop())

    @staticmethod
    def update_details(queue: Queue, progress_bar: ConsoleProgressBar, max_iter):
        TaskWithProgression.stopped_update_details_thread = False
        if queue is None:
            return
        iter_nb = 0
        while iter_nb < max_iter and not TaskWithProgression.stopped_update_details_thread:
            try:
                val = queue.get(block=True, timeout=10)
            except Empty:
                continue
            except (OSError, ValueError):
                LOGGER.info(f"details_thread interrupted at iteration {iter_nb}")
                return
            iter_nb += 1
            if isinstance(val, str):
                worker_stdout = val
                if worker_stdout != "":
                    progress_bar.stdout.writelines_with_lock(worker_stdout.splitlines())
            else:
                [n, detail] = val
                progress_bar.set_detail(n, detail)

    def update_status(self, progress_bar):
        status_line_stdout = ">> Stdout redirected to {file} ({nb_lines} line(s))"
        status_line_stderr = ">> Stderr redirected to {file} ({nb_error} error(s))"
        status_lines = [status_line_stdout.format(nb_lines=self.stdout_nb_lines, file=self.stdout_file),
                        status_line_stderr.format(nb_error=self.nb_errors, file=self.stderr_file)]
        progress_bar.set_status(status_lines)

    def process_error(self, batch_element: BatchElement, progress_bar):
        self.nb_errors += 1
        self.update_status(progress_bar)
        if batch_element.error:
            self.write_error(f"{batch_element.info}: {batch_element.error}")

    def process_stdout(self, batch_element: BatchElement, stdout, progress_bar):
        if stdout and stdout.strip() != "":
            self.stdout_nb_lines += stdout.count('\n')
            self.update_status(progress_bar)
            self.write_stdout(f"{batch_element.info}: {stdout}")

    def write_error(self, error):
        if self.stderr_file:
            with open(self.stderr_file, "a") as f:
                f.write(error.strip() + "\n")
        else:
            print(error.strip())

    def write_stdout(self, stdout):
        if self.stdout_file:
            with open(self.stdout_file, "a") as f:
                f.write(stdout)
        else:
            print(stdout.strip())

    def execute_multiprocess_batch(self, nb_process, task, args_list: List[BatchElement], post_task, progress_bar):
        details_queue = Queue()
        nb_elements = len(args_list)
        nb_process = min(nb_process, nb_elements)
        pool = Pool(processes=nb_process,
                    initializer=self.on_worker_start,
                    initargs=(task, details_queue, self.custom_ows, self.custo_ows_args, self.custom_owe))
        details_thread = threading.Thread(target=self.update_details,
                                          args=(details_queue, progress_bar, 2 * nb_process + nb_elements))
        details_thread.start()
        self.nb_errors = 0
        self.stdout_nb_lines = 0
        self.update_status(progress_bar)
        try:
            res_list = pool.imap_unordered(self.execute_task, args_list)
            for res in res_list:
                batch_element, stdout = res
                self.process_stdout(batch_element, stdout, progress_bar)
                if batch_element.error:
                    self.process_error(batch_element, progress_bar)
                try:
                    post_task(batch_element.result, progress_bar, replace=True)
                except BaseException:
                    # print("Unexpected exception")
                    batch_element.error = traceback.format_exc()
                    self.process_error(batch_element, progress_bar)
        except BaseException:
            print("Unexpected exception")
            traceback.print_exc()
        finally:
            self.__send_ending_tasks(pool, nb_process)
            self.__stop_details_thread(details_thread)
            progress_bar.stop()
            LOGGER.debug("Try to close, terminate, and join the pool")
            pool.close()
            LOGGER.debug("Pool closed")
            pool.terminate()
            LOGGER.debug("Pool terminated")
            pool.join()
            LOGGER.debug("Pool joined")

    @staticmethod
    def __stop_details_thread(details_thread):
        details_thread.join(timeout=10)
        if not details_thread.is_alive():
            LOGGER.debug("details_thread joined")
        else:
            LOGGER.info("details_thread not joined after 10 seconds. Try to force it to stop.")
            TaskWithProgression.stopped_update_details_thread = True
            details_thread.join(timeout=20)
            if details_thread.is_alive():
                LOGGER.info("Warning: details_thread could not be stopped")
            else:
                LOGGER.info("details_thread stopped correctly")

    def __send_ending_tasks(self, pool: Pool, nb_process):
        LOGGER.debug("Send ending tasks to workers")
        result = pool.map_async(self.on_worker_end, range(nb_process))
        result.wait()
