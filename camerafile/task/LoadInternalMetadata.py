from camerafile.core.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration


class LoadInternalMetadata:

    @staticmethod
    def execute(batch_element: BatchElement):
        internal_metadata = batch_element.args
        try:
            internal_metadata.load_internal_metadata()
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "LoadInternalMetadata: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = internal_metadata
        return batch_element
