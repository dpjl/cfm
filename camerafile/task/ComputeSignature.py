from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory


class ComputeSignature:

    @staticmethod
    def execute(batch_element: BatchElement):
        root_path, file_desc, signature_metadata = batch_element.args
        try:
            ComputeSignature.compute_value(root_path, file_desc, signature_metadata)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "ComputeSignature: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = file_desc.get_id(), signature_metadata
        return batch_element

    @staticmethod
    def compute_value(root_path, file_desc, signature_metadata):
        file_access = FileAccessFactory.get(root_path, file_desc)
        if signature_metadata.value is None:
            signature_metadata.value = file_access.hash()
