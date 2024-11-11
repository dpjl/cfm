import os
from threading import Event, Thread, Lock

from watchdog.observers import Observer

from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.monitor.MediaSetHandler import MediaSetHandler
from camerafile.processor.BatchComputeCm import BatchComputeCm
from camerafile.processor.BatchComputeNecessarySignatures import BatchComputeNecessarySignaturesMultiProcess
from camerafile.processor.BatchCopy import BatchCopy
from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd

LOGGER = Logger(__name__)


class Watcher(Thread):

    def __init__(self, media_set1: MediaSet, media_set2: MediaSet):
        LOGGER.write_title(media_set1, "Start monitoring")

        Thread.__init__(self)
        self.media_set1 = media_set1
        self.media_set2 = media_set2
        self.modified_paths = {media_set1: [], media_set2: []}
        self.other_md_needed = media_set2.state.get_metadata_needed_by_format()

        self.start_observer(media_set1)

        self.stop_required = False
        self.lock = Lock()
        self.something_happened = Event()

    def start_observer(self, media_set):
        LOGGER.info("Initiate observer...")
        observer = Observer()
        media_set1_handler = MediaSetHandler(media_set, self)
        observer.schedule(media_set1_handler, media_set.root_path, recursive=True)
        observer.start()
        LOGGER.info("Observer initiated correctly.")

    def wake_up(self, media_set: MediaSet, new_path: str):
        with self.lock:
            found = False
            for i, path in enumerate(self.modified_paths[media_set]):
                if new_path == path:
                    found = True
                elif new_path in path:
                    self.modified_paths[media_set][i] = new_path
                    found = True
                elif path in new_path:
                    found = True
            if not found:
                self.modified_paths[media_set].append(new_path)
        self.something_happened.set()

    def stop(self):
        self.stop_required = True

    def __execute_cfm(self):
        to_update = {}
        with self.lock:
            for media_set, modified_paths in self.modified_paths.items():
                if len(modified_paths) != 0:
                    to_update[media_set] = modified_paths
                    self.modified_paths[media_set] = []

        for media_set, modified_paths in to_update.items():
            for modified_path in modified_paths:
                LOGGER.write_title(media_set, f"Read changes from path {modified_path}")
                media_set.initialize_file_and_dir_list(modified_path)
                BatchReadInternalMd(media_set, self.other_md_needed).execute()
                BatchComputeCm(media_set).execute()
                
        # Watching MediaSet2 also would be better, but difficult, as org command will modify it also.
        # So for now, we reload mediaset 2 entirely, in case it has been modified before last loading.
        LOGGER.write_title(self.media_set2, f"Reload entire target media set")
        self.media_set2.initialize_file_and_dir_list()
        BatchReadInternalMd(self.media_set2, self.other_md_needed).execute()
        BatchComputeCm(self.media_set2).execute()

        BatchComputeNecessarySignaturesMultiProcess(self.media_set1, self.media_set2).execute()
        bc = BatchCopy(self.media_set1, self.media_set2, Configuration.get().copy_mode)
        bc.execute()
        print("")

        pp_script = Configuration.get().pp_script
        for path in to_update[self.media_set1]:
            LOGGER.info(f"This path has been modified in origin media set: {path}")
            if pp_script is not None:
                cmd_to_execute = f"{pp_script} o {path}"
                LOGGER.info(cmd_to_execute)
                os.system(cmd_to_execute)

        for path in bc.target_modified_paths:
            LOGGER.info(f"This path has been modified in target media set: {path}")
            if pp_script is not None:
                cmd_to_execute = f"{pp_script} d {path}"
                LOGGER.info(cmd_to_execute)
                os.system(cmd_to_execute)

        self.media_set1.save_on_disk()
        self.media_set1.close_database()
        self.media_set2.save_on_disk()
        self.media_set2.close_database()

        return True

    def run(self):
        LOGGER.info("Start thread in charge of watching changes")
        self.something_happened.wait()
        self.something_happened.clear()

        while True:
            if self.stop_required:
                LOGGER.info("Stop thread in charge of watching changes")
                return
            sync_delay = Configuration.get().sync_delay
            LOGGER.info("Watcher has been alerted of at least one change. "
                        f"Wait {sync_delay} seconds and update.")
            if not self.something_happened.wait(sync_delay):
                if self.__execute_cfm():
                    # if config.debug:
                    #    logger.print("Return from sync tool call")
                    LOGGER.write_title(self.media_set1, "Wait for next modification...")
                    self.something_happened.wait()
                else:
                    LOGGER.info(
                        "CFM call failed. Wait another iteration before retrying to call it.")
                    continue
            self.something_happened.clear()
