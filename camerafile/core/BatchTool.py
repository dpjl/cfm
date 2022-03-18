import atexit
import threading
import traceback
from multiprocessing import Pool, Manager, cpu_count
from multiprocessing import current_process
from multiprocessing.queues import Queue
from queue import Empty

from typing import List

from camerafile.console.ConsoleProgressBar import ConsoleProgressBar
from camerafile.console.StandardOutputWrapper import StdoutRecorder
from camerafile.mdtools.ExifToolReader import ExifTool

DEFAULT_NB_SUB_PROCESS = cpu_count()


class BatchElement:

    def __init__(self, args, info):
        self.args = args
        self.info = info
        self.error = None
        self.result = None


class TaskWithProgression:
    current_multiprocess_task = None
    queue = None

    def __init__(self, batch_title="", nb_sub_process=None, on_worker_start=None, on_worker_start_args=(),
                 on_worker_end=None, stderr_file=None, stdout_file=None):
        self.batch_title = batch_title
        self.nb_sub_process = nb_sub_process
        self.custom_ows = on_worker_start
        self.custo_ows_args = on_worker_start_args
        self.custom_owe = on_worker_end
        self.in_progress = False
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
            print("Nothing to do")
            self.finalize()
        return None

    def execute_uni_process_batch(self, task, batch_args_list: List[BatchElement], post_task, progress_bar):
        pid = current_process().pid
        try:
            for batch_args in batch_args_list:
                progress_bar.set_detail(pid, batch_args.info)
                result = task(batch_args.args)
                post_task(result, progress_bar, replace=False)
        finally:
            progress_bar.stop()
            ExifTool.stop()

    @staticmethod
    def execute_task(batch_element: BatchElement):
        try:
            queue: Queue = TaskWithProgression.queue
            if queue is not None:
                queue.put([current_process().pid, batch_element.info])
            stdout_recorder = StdoutRecorder().start()
            if TaskWithProgression.current_multiprocess_task is None:
                print("Multi-processing: no task defined in sub-process.")
                return None, stdout_recorder.stop()
            batch_element = TaskWithProgression.current_multiprocess_task(batch_element)
            return batch_element, stdout_recorder.stop()
        except BaseException as e:
            return batch_element, traceback.format_exc()

    @staticmethod
    def on_worker_start(task, queue, custom_ows=None, custom_ows_args=(), custom_owe=None):
        stdout_recorder = StdoutRecorder().start()
        TaskWithProgression.current_multiprocess_task = task
        TaskWithProgression.queue = queue
        atexit.register(TaskWithProgression.on_worker_end, queue, custom_owe)
        if custom_ows:
            custom_ows(*custom_ows_args)
        queue.put(stdout_recorder.stop())

    @staticmethod
    def on_worker_end(queue, custom_owe=None):
        stdout_recorder = StdoutRecorder().start()
        if custom_owe:
            custom_owe()
        queue.put(stdout_recorder.stop())

    def update_details(self, queue, progress_bar, max_iter):
        iter_nb = 0
        while iter_nb < max_iter and self.in_progress:
            iter_nb += 1
            try:
                val = queue.get(block=True, timeout=5)
            except Empty:
                continue
            if isinstance(val, str):
                worker_stdout = val
                if worker_stdout != "":
                    print(worker_stdout.strip())
            else:
                [n, detail] = val
                progress_bar.set_detail(n, detail)

        # Read all remaining elements and quit
        while iter_nb < max_iter:
            iter_nb += 1
            try:
                val = queue.get(block=False)
            except Empty:
                break
            if isinstance(val, str):
                worker_stdout = val
                if worker_stdout != "":
                    print(worker_stdout.strip())

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
            self.write_error(batch_element.error)

    def write_error(self, error):
        if self.stderr_file:
            with open(self.stderr_file, "a") as f:
                f.write(error.strip() + "\n")
        else:
            print(error.strip())

    def write_stdout(self, stdout):
        if stdout and stdout.strip() != "":
            self.stdout_nb_lines += stdout.count('\n') + 1
            if self.stdout_file:
                with open(self.stdout_file, "a") as f:
                    f.write(stdout)
            else:
                print(stdout.strip())

    def execute_multiprocess_batch(self, nb_process, task, args_list: List[BatchElement], post_task, progress_bar):
        m = Manager()
        queue = m.Queue()
        nb_elements = len(args_list)
        nb_process = min(nb_process, nb_elements)
        pool = Pool(nb_process, self.on_worker_start,
                    (task, queue, self.custom_ows, self.custo_ows_args, self.custom_owe))
        terminate_correctly = False
        self.in_progress = True
        det_threads = threading.Thread(target=self.update_details,
                                       args=(queue, progress_bar, 2 * nb_process + nb_elements))
        det_threads.start()
        self.nb_errors = 0
        self.stdout_nb_lines = 0
        self.update_status(progress_bar)

        try:
            res_list = pool.imap_unordered(self.execute_task, args_list)
            for res in res_list:
                batch_element, stdout = res
                self.write_stdout(stdout)
                if batch_element.error:
                    self.process_error(batch_element, progress_bar)
                post_task(batch_element.result, progress_bar, replace=True)
            terminate_correctly = True

        except KeyboardInterrupt:
            try:
                print("Interrupted by user (Ctrl-C)")
                pool.terminate()
            except KeyboardInterrupt:
                print("Interrupted by user (Ctrl-C) 2")
        except BaseException as e:
            print("Unexpected exception")
            traceback.print_exc()
        finally:
            try:
                pool.close()
                progress_bar.stop()
                if terminate_correctly:
                    pool.join()
                    self.in_progress = False
                    det_threads.join()
                else:
                    pool.terminate()

            except KeyboardInterrupt:
                print("Interrupted by user (Ctrl-C) 3")
