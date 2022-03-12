import atexit
import traceback
from multiprocessing import Pool, Manager, cpu_count
from multiprocessing import current_process
from multiprocessing.queues import Queue

from typing import List

from camerafile.console.ConsoleProgressBar import ConsoleProgressBar
from camerafile.console.StandardOutputWrapper import StdoutRecorder
from camerafile.mdtools.ExifToolReader import ExifTool

DEFAULT_NB_SUB_PROCESS = cpu_count()


class BatchArgs:

    def __init__(self, args, info):
        self.args = args
        self.info = info


class TaskWithProgression:
    current_multiprocess_task = None
    queue = None

    def __init__(self, batch_title="", nb_sub_process=None, on_worker_start=None, on_worker_end=None):
        self.batch_title = batch_title
        self.nb_sub_process = nb_sub_process
        self.custom_ows = on_worker_start
        self.custom_owe = on_worker_end
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

    def arguments(self) -> List[BatchArgs]:
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
        return None

    def execute_uni_process_batch(self, task, batch_args_list: List[BatchArgs], post_task, progress_bar):
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
    def execute_task(batch_args: BatchArgs):
        try:
            queue: Queue = TaskWithProgression.queue
            if queue is not None:
                queue.put([current_process().pid, batch_args.info])
            stdout_recorder = StdoutRecorder().start()
            if TaskWithProgression.current_multiprocess_task is None:
                print("Multi-processing: no task defined in sub-process.")
                return None, stdout_recorder.stop()
            result = TaskWithProgression.current_multiprocess_task(batch_args.args)
            return result, stdout_recorder.stop()
        except BaseException as e:
            return None, traceback.format_exc()

    @staticmethod
    def on_worker_start(task, queue, custom_ows=None, custom_owe=None):
        stdout_recorder = StdoutRecorder().start()
        TaskWithProgression.current_multiprocess_task = task
        TaskWithProgression.queue = queue
        atexit.register(TaskWithProgression.on_worker_end, queue, custom_owe)
        if custom_ows:
            custom_ows()
        queue.put(stdout_recorder.stop())

    @staticmethod
    def on_worker_end(queue, custom_owe=None):
        stdout_recorder = StdoutRecorder().start()
        if custom_owe:
            custom_owe()
        queue.put(stdout_recorder.stop())

    def execute_multiprocess_batch(self, nb_process, task, args_list: List[BatchArgs], post_task, progress_bar):
        m = Manager()
        queue = m.Queue()
        nb_elements = len(args_list)
        nb_process = min(nb_process, nb_elements)
        pool = Pool(nb_process, self.on_worker_start, (task, queue, self.custom_ows, self.custom_owe))
        nb_processed_elements = 0
        terminate_correctly = False
        try:

            for i in range(nb_process):
                on_worker_start_stdout = queue.get(block=True, timeout=5)
                if on_worker_start_stdout != "":
                    print(on_worker_start_stdout.strip())

            res_list = pool.imap_unordered(self.execute_task, args_list)

            for i in range(nb_process):
                [n, detail] = queue.get(block=True, timeout=5)
                progress_bar.set_detail(n, detail)
                nb_processed_elements += 1

            for res in res_list:
                if nb_processed_elements < nb_elements:
                    [n, detail] = queue.get(block=True, timeout=5)
                    progress_bar.set_detail(n, detail)
                    nb_processed_elements += 1
                result, stdout = res
                if stdout and stdout.strip() != "":
                    print(stdout.strip())
                if result is not None:
                    post_task(result, progress_bar, replace=True)
                else:
                    progress_bar.increment()
                    print("One element has not been processed correctly")

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
                    for i in range(nb_process):
                        on_worker_end_stdout = queue.get(block=True, timeout=5)
                        if on_worker_end_stdout != "":
                            print(on_worker_end_stdout.strip())
                else:
                    pool.terminate()

            except KeyboardInterrupt:
                print("Interrupted by user (Ctrl-C) 3")
