from typing import List
import os
from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.GenerateThumbnail import GenerateThumbnail

LOGGER = Logger(__name__)


class BatchGenerateThumbnails(CFMBatch):

    def __init__(self, media_set: MediaSet):
        self.media_set = media_set
        self.thb_errors = []
        self.thb_dir = OutputDirectory.get(self.media_set.root_path).path / "thb"
        os.makedirs(self.thb_dir, exist_ok=True)
        CFMBatch.__init__(self, "Generate all thumbnails",
                          stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
                          stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout)

    def initialize(self):
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return GenerateThumbnail.execute

    def arguments(self) -> List[BatchElement]:
        args_list = []
        media_file: MediaFile
        for media_file in self.media_set:
            thb_path = self.thb_dir / f"{media_file.file_desc.id}.thb"
            if not thb_path.exists():
                args_list.append(BatchElement((self.media_set.root_path, media_file.file_desc, thb_path), media_file.get_path()))
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        progress_bar.increment()

    def finalize(self):
        pass
