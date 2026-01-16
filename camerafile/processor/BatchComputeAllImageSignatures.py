from datetime import datetime, timedelta
from typing import Optional

from camerafile.core.Constants import SIGNATURE, IMAGE_TYPE
from camerafile.core.Logging import Logger
from camerafile.core.MediaSet import MediaSet
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.processor.BatchTool import BatchElement
from camerafile.processor.CFMBatch import CFMBatch
from camerafile.task.ComputeSignature import ComputeSignature

LOGGER = Logger(__name__)


class BatchComputeAllImageSignatures(CFMBatch):
    """
    Computes signatures for ALL image files in a MediaSet that have an EXIF date
    within a specified date range. Unlike BatchComputeNecessarySignatures which only
    computes signatures when needed to resolve ambiguities, this batch computes all
    signatures to enable WhatsApp-sent files matching with their originals.
    
    Videos are excluded because their signature (file size) is not useful after
    WhatsApp recompression.
    """

    def __init__(self, media_set: MediaSet, date_start: Optional[datetime] = None, date_end: Optional[datetime] = None):
        """
        Args:
            media_set: The MediaSet to process
            date_start: Only compute signatures for files with EXIF date >= this (optional)
            date_end: Only compute signatures for files with EXIF date <= this (optional)
        """
        self.media_set = media_set
        self.date_start = date_start
        self.date_end = date_end
        CFMBatch.__init__(
            self,
            batch_title="Compute all image signatures for WhatsApp matching",
            stderr_file=OutputDirectory.get(self.media_set.root_path).batch_stderr,
            stdout_file=OutputDirectory.get(self.media_set.root_path).batch_stdout
        )

    def initialize(self):
        if self.date_start is not None or self.date_end is not None:
            self.batch_title = f"{self.batch_title} ({self._format_date_range()})"
        LOGGER.write_title(self.media_set, self.update_title())

    def task_getter(self):
        return ComputeSignature.execute

    def arguments(self):
        args_list = []
        processed_system_ids = set()
        
        for media_file in self.media_set.media_file_list:
            # Skip non-images (videos use file size as signature, not useful after WhatsApp recompression)
            if media_file.file_desc.extension not in IMAGE_TYPE:
                continue
            
            # Skip if signature already computed
            if media_file.metadata[SIGNATURE].value is not None:
                continue
            
            # Skip if no EXIF date
            exif_date = media_file.get_exif_date()
            if exif_date is None:
                continue
            
            # Check date range if specified
            if self.date_start is not None or self.date_end is not None:
                try:
                    file_date = datetime.strptime(exif_date, '%Y/%m/%d %H:%M:%S.%f')
                    if self.date_start is not None and file_date < self.date_start:
                        continue
                    if self.date_end is not None and file_date > self.date_end:
                        continue
                except ValueError:
                    continue
            
            # Deduplicate by system_id to avoid processing the same physical file multiple times
            system_id = media_file.file_desc.system_id
            if system_id is not None:
                if system_id in processed_system_ids:
                    continue
                processed_system_ids.add(system_id)
            
            args_list.append(BatchElement(
                (media_file.parent_set.root_path, media_file.file_desc, media_file.metadata[SIGNATURE]),
                media_file.get_path()
            ))
        
        return args_list

    def post_task(self, result, progress_bar, replace=False):
        media_id, result_signature_metadata = result
        original_media = self.media_set.get_media(media_id)
        if original_media is not None:
            original_media.metadata[SIGNATURE] = result_signature_metadata
            # Reindex the file now that a signature has been computed
            self.media_set.indexer.add_media_file(original_media)
        progress_bar.increment()

    def finalize(self):
        pass

    def _format_date_range(self) -> str:
        if self.date_start is not None and self.date_end is not None:
            return f"from {self.date_start.strftime('%Y-%m-%d')} to {self.date_end.strftime('%Y-%m-%d')}"
        if self.date_start is not None:
            return f"from {self.date_start.strftime('%Y-%m-%d')}"
        return f"until {self.date_end.strftime('%Y-%m-%d')}"
