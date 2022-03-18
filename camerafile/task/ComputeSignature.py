from camerafile.core.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.metadata.MetadataSignature import MetadataSignature


class ComputeSignature:

    @staticmethod
    def execute(batch_element: BatchElement):
        signature_metadata: MetadataSignature = batch_element.args
        try:
            signature_metadata.compute_value()
        except BaseException as e:
            if Configuration.get().exit_on_error:
                pass  # TODO : put full stacktrace in batch_element.error
            else:
                batch_element.error = "ComputeSignature: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = signature_metadata
        return batch_element
