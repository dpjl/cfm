from camerafile.core.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.metadata.MetadataFaces import MetadataFaces


class ComputeFaceBoxes:

    @staticmethod
    def execute(batch_element: BatchElement):
        metadata_face: MetadataFaces = batch_element.args
        try:
            metadata_face.compute_face_boxes()
        except BaseException as e:
            if Configuration.get().exit_on_error:
                pass  # TODO : put full stacktrace in batch_element.error
            else:
                batch_element.error = "ComputeFaceBoxes: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = metadata_face
        return batch_element
