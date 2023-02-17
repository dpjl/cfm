import os

import numpy

from camerafile.processor.BatchTool import BatchElement
from camerafile.core.Configuration import Configuration
from camerafile.core.Resource import Resource
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from PIL.Image import Image
from dlib import rectangle


class ComputeFaceBoxes:
    predictor = None
    detector = None

    @staticmethod
    def execute(batch_element: BatchElement):
        root_path, file_desc, metadata_face = batch_element.args
        enc_dur = None
        det_dur = None
        try:
            det_dur, enc_dur = ComputeFaceBoxes.compute_face_boxes(root_path, file_desc, metadata_face)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "ComputeFaceBoxes: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = file_desc.get_id(), metadata_face, enc_dur, det_dur
        return batch_element

    @staticmethod
    def compute_face_boxes(root_path, file_desc, metadata_face):

        file_access = FileAccessFactory.get(root_path, file_desc)

        if ComputeFaceBoxes.predictor is None or ComputeFaceBoxes.detector is None:
            import dlib
            print("Loading " + Resource.dlib_predictor + "...")
            ComputeFaceBoxes.detector = dlib.get_frontal_face_detector()
            ComputeFaceBoxes.predictor = dlib.shape_predictor(Resource.dlib_predictor)

        image = file_access.get_image()
        data = image.image_data

        original_data = data
        image_height = image.image_data.height
        resize_image = not Configuration.get().face_detection_keep_image_size and image_height < 900

        if resize_image:
            height_resize = 1500
            frame_resize_scale = float(image.image_data.height) / height_resize
            (width, height) = (data.width // frame_resize_scale, data.height // frame_resize_scale)
            data: Image = image.image_data.resize((int(width), int(height)))
            # data = ImageOps.grayscale(data)

        # img = dlib.load_rgb_image(self.file_access.path)
        img = numpy.array(data)
        dets = ComputeFaceBoxes.detector(img, 0)

        encodings = []
        locations = []
        for k, d in enumerate(dets):
            locations += [(d.top(), d.right(), d.bottom(), d.left())]

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]
            img = numpy.array(original_data)

        for d in locations:
            encodings += [ComputeFaceBoxes.predictor(img, rectangle(d[0], d[1], d[2], d[3]))]

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces(locations).save(file)

        metadata_face.value = {"locations": locations, "names": []}
        metadata_face.binary_value = encodings
        return 0, 0
