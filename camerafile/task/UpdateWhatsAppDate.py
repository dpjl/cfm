import os
from datetime import datetime
from pathlib import Path

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.processor.BatchTool import BatchElement


class UpdateWhatsAppDate:
    """
    Task to update the modification date of a file based on WhatsApp metadata.
    """

    @staticmethod
    def execute(batch_element: BatchElement):
        """
        Update the modification date of a file if it's a WhatsApp file.
        
        Args:
            batch_element: Contains (root_path, file_desc) as args
            
        Returns:
            BatchElement with result: (file_id, status, whatsapp_date)
            - status can be: "Updated", "Already correct", "Not a WhatsApp file", "No date found"
        """
        root_path, file_desc = batch_element.args
        result = file_desc.id, "Not a WhatsApp file", None
        
        try:
            file_access = FileAccessFactory.get(root_path, file_desc)
            whatsapp_date, camera_model = file_access.read_whatsapp_info()
            
            if whatsapp_date is not None:
                file_path = file_access.get_path()
                current_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                
                # Round to seconds for comparison (filesystem precision)
                whatsapp_timestamp = int(whatsapp_date.timestamp())
                current_timestamp = int(current_mtime.timestamp())
                
                if whatsapp_timestamp != current_timestamp:
                    # Update the modification time
                    os.utime(file_path, (whatsapp_timestamp, whatsapp_timestamp))
                    result = file_desc.id, "Updated", whatsapp_date
                else:
                    result = file_desc.id, "Already correct", whatsapp_date
            else:
                result = file_desc.id, "No date found", None
                
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = f"UpdateWhatsAppDate: [{batch_element.info}] - {str(e)}"
        
        batch_element.args = None
        batch_element.result = result
        return batch_element
