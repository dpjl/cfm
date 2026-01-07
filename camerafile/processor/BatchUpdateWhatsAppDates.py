from typing import List

from camerafile.console.ConsoleTable import ConsoleTable
from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.core.MediaFile import MediaFile
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.BatchTool import BatchElement
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.UpdateWhatsAppDate import UpdateWhatsAppDate

LOGGER = Logger(__name__)


class BatchUpdateWhatsAppDates(CFMBatch):
    """
    Batch processor to update file modification dates for WhatsApp files.
    
    This processor scans all files in a media set, identifies WhatsApp files,
    and updates their modification dates based on the date extracted from
    WhatsApp metadata (filename pattern or database).
    """
    
    BATCH_TITLE = "Update WhatsApp file modification dates"
    RESULT_COLUMN_STATUS = "Status"
    RESULT_COLUMN_NUMBER = "Number"
    EMPTY_STRING = ""

    def __init__(self, media_set: MediaSet):
        """
        Initialize the batch processor.
        
        Args:
            media_set: The MediaSet containing files to update
        """
        self.media_set = media_set
        CFMBatch.__init__(
            self,
            batch_title=self.BATCH_TITLE,
            stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
            stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout
        )
        self.result_stats = {}

    def initialize(self):
        """Initialize the batch processor."""
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        """Return the task function to execute for each file."""
        return UpdateWhatsAppDate.execute

    def increment_stats(self, status):
        """Increment statistics counter for a given status."""
        if status not in self.result_stats:
            self.result_stats[status] = 0
        self.result_stats[status] += 1

    def arguments(self) -> List[BatchElement]:
        """
        Build the list of arguments for the batch task.
        
        Returns:
            List of BatchElement, one for each file in the media set
        """
        args_list = []
        media_file: MediaFile
        
        for media_file in self.media_set:
            task_args = (self.media_set.root_path, media_file.file_desc)
            batch_element = BatchElement(task_args, media_file.get_path())
            args_list.append(batch_element)
        
        if not Configuration.get().watch and len(args_list) > 0:
            LOGGER.info(f"Checking {len(args_list)} files for WhatsApp dates...")
            
        return args_list

    def post_task(self, result, pb, replace=False):
        """
        Process the result of each task execution.
        
        Args:
            result: Tuple (file_id, status, whatsapp_date)
            pb: Progress bar instance
            replace: Whether this is a replacement call (multiprocessing)
        """
        file_id, status, whatsapp_date = result
        self.increment_stats(status)
        pb.increment()

    def finalize(self):
        """
        Finalize the batch processing and display statistics.
        """
        if len(self.result_stats) != 0:
            print(self.EMPTY_STRING)
            tab = ConsoleTable()
            tab.print_header(self.RESULT_COLUMN_STATUS, self.RESULT_COLUMN_NUMBER)
            
            # Display stats in a meaningful order
            status_order = ["Updated", "Already correct", "No date found", "Not a WhatsApp file"]
            for status in status_order:
                if status in self.result_stats:
                    tab.print_line(status, str(self.result_stats[status]))
            
            # Display any other statuses not in the predefined order
            for status in self.result_stats:
                if status not in status_order:
                    tab.print_line(status, str(self.result_stats[status]))
                    
            print(self.EMPTY_STRING)
