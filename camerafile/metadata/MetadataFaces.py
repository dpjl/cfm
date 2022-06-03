import os

import cv2
import dlib
import numpy
import time
from PIL.Image import Image

from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import Logger
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.metadata.Metadata import Metadata
from camerafile.tools.CFMImage import CFMImage

# from deepface.detectors import FaceDetector

LOGGER = Logger(__name__)


class MetadataFaces(Metadata):
    face_rec_lib = None
    numpy_lib = None
    faceCascade = None
    # predictor_path = "camerafile/data/models/shape_predictor_68_face_landmarks.dat"
    predictor_path = "camerafile/data/models/shape_predictor_68_face_landmarks_GTX.dat"
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(predictor_path)

    def __init__(self, file_access: FileAccess, knn_clf):
        super().__init__(None)
        self.file_access = file_access
        self.knn_clf = knn_clf

    def set_value(self, value):
        self.value = value

    def compute_face_boxes(self):
        if self.value is None:
            self.value, self.binary_value, det_dur, enc_dur = self.static_compute_face_boxes()
            return enc_dur, det_dur

    def static_compute_face_boxes_deepface(self):

        img = self.file_access.get_cv2_image()
        # backends = ['opencv', 'ssd', 'dlib', 'mtcnn', 'retinaface', 'mediapipe']

        resize_image = True
        if resize_image:
            height_resize = 800
            frame_resize_scale = float(img.shape[0]) / height_resize
            (width, height) = (img.shape[1] // frame_resize_scale, img.shape[0] // frame_resize_scale)
            img = cv2.resize(img, (int(width), int(height)))

        detector_name = "retinaface"
        detector = FaceDetector.build_model(detector_name)
        faces = FaceDetector.detect_faces(detector, detector_name, img)

        locations = []
        for f in faces:
            [x, y, w, h] = f[1]
            locations += [(int(x), int(y), int(w), int(h))]

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            image = self.file_access.get_image()
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces_opencv(locations).save(file)

        return {"locations": locations, "names": []}, None, 0, 0

    def static_compute_face_boxes_mtcnn(self):

        locations = []
        img = self.file_access.get_cv2_image()
        resize_image = True

        if resize_image:
            height_resize = 1500
            frame_resize_scale = float(img.shape[0]) / height_resize
            (width, height) = (img.shape[1] // frame_resize_scale, img.shape[0] // frame_resize_scale)
            img = cv2.resize(img, (int(width), int(height)))

        faces = self.detector.detect_faces(img)
        # print(str(faces))
        for f in faces:
            (x, y, w, h) = f.box
            locations += [(int(x), int(y), int(w), int(h))]

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            image = self.file_access.get_image()
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces_opencv(locations).save(file)

        return {"locations": locations, "names": []}, None, 0, 0

    # opencv_haar
    def static_compute_face_boxes_opencv_haar(self):

        if MetadataFaces.faceCascade is None:
            # MetadataFaces.faceCascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')
            # MetadataFaces.faceCascade = cv2.cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            MetadataFaces.faceCascade = cv2.cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')

        locations = []
        img = self.file_access.get_cv2_image()
        resize_image = True

        if resize_image:
            height_resize = 1500
            frame_resize_scale = float(img.shape[0]) / height_resize
            (width, height) = (img.shape[1] // frame_resize_scale, img.shape[0] // frame_resize_scale)
            img = cv2.resize(img, (int(width), int(height)))
        # 475 faces détectées en 2 minutes
        # faces = MetadataFaces.faceCascade.detectMultiScale(img, 1.3, 4)
        # 640 en 3 minutes
        # faces = MetadataFaces.faceCascade.detectMultiScale(img, 1.2, 3)
        # 533 en 1min56
        faces = MetadataFaces.faceCascade.detectMultiScale(img, 1.3, 3)
        for (x, y, w, h) in faces:
            locations += [(int(x), int(y), int(w), int(h))]

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            image = self.file_access.get_image()
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces_opencv(locations).save(file)

        return {"locations": locations, "names": []}, None, 0, 0

    def static_compute_face_boxes(self):

        image = self.file_access.get_image()
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
        dets = self.detector(img, 0)

        encodings = []
        locations = []
        for k, d in enumerate(dets):
            locations += [(d.top(), d.right(), d.bottom(), d.left())]

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]
            img = numpy.array(original_data)

        for d in locations:
            encodings += [self.predictor(img, dlib.rectangle(d[0], d[1], d[2], d[3]))]

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces(locations).save(file)

        return {"locations": locations, "names": []}, encodings, 0, 0

    @staticmethod
    def static_compute_face_boxes_dlib(image: CFMImage):

        # We do this to not have to import face_recognition if it's not necessary at the load of the program
        # (but still only one time)
        if MetadataFaces.face_rec_lib is None and MetadataFaces.numpy_lib is None:
            LOGGER.debug("Load face_recognition and numpy modules")
            import face_recognition
            import numpy
            MetadataFaces.face_rec_lib = face_recognition
            MetadataFaces.numpy_lib = numpy

        start_time = time.time()
        data = image.image_data
        original_data = data
        image_height = image.image_data.height
        resize_image = not Configuration.get().face_detection_keep_image_size or image_height < 1000

        if resize_image:
            height_resize = 1000
            frame_resize_scale = float(image.image_data.height) / height_resize
            (width, height) = (data.width // frame_resize_scale, data.height // frame_resize_scale)
            data: Image = image.image_data.resize((int(width), int(height)))
            # data = ImageOps.grayscale(data)

        img = MetadataFaces.numpy_lib.array(data)
        locations = MetadataFaces.face_rec_lib.face_locations(img, number_of_times_to_upsample=0)
        end_face_locations_time = time.time()

        if resize_image:
            locations = [tuple([int(frame_resize_scale * pos) for pos in loc]) for loc in locations]
            img = MetadataFaces.numpy_lib.array(original_data)

        if Configuration.get().debug:
            face_debug_path = Configuration.get().first_output_directory.path / "face-debug"
            os.makedirs(face_debug_path, exist_ok=True)
            with open(face_debug_path / image.filename, "wb") as file:
                image.get_image_with_faces(locations).save(file)

        encoding = MetadataFaces.face_rec_lib.face_encodings(img, known_face_locations=locations)
        end_encoding_time = time.time()

        det_duration = end_face_locations_time - start_time
        enc_duration = end_encoding_time - end_face_locations_time
        return {"locations": locations, "names": []}, encoding, det_duration, enc_duration

    def recognize_faces(self):
        if self.knn_clf is None:
            return
        if self.binary_value is None:
            return
        if self.value is None:
            self.value = {"locations": [], "names": []}
        else:
            self.value["names"] = []
        distance_threshold = 0.6
        for face_encoding in self.binary_value:
            closest_distances = self.knn_clf.kneighbors([face_encoding], n_neighbors=1)
            if closest_distances[0][0][0] <= distance_threshold:
                [face_name] = self.knn_clf.predict([face_encoding])
            else:
                face_name = "unrecognized"
            self.value["names"].append(face_name)
