import hashlib
import math
import os
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from camerafile.tools.CFMImage import CFMImage
from camerafile.core.Constants import FACES


if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet

INDEX = "index"
ENCODINGS = "encodings"
IMAGES = "images"


class FaceRecognition:

    def __init__(self, media_set: "MediaSet", output_directory):
        self.media_set = media_set
        self.training_path = output_directory.path / "training_examples"
        self.all_encoding_ids = {}
        self.training_data = {}
        self.load_training_data()
        self.knn_clf = None
        self.load_model()

    @staticmethod
    def get_encoding_id(enc):
        return hashlib.sha224(str(enc).encode('utf-8')).hexdigest()

    def add_encoding_id(self, enc):
        self.all_encoding_ids[self.get_encoding_id(enc)] = None

    def load_training_data(self):
        for (name_dir_path, folder_names, file_names) in os.walk(self.training_path):
            for file_name in file_names:
                [index, extension] = os.path.splitext(file_name)
                if extension == ".encoding":
                    name = Path(name_dir_path).name
                    with open(self.encoding_file_name(name, int(index)), mode='rb') as file:
                        encoding_content = pickle.load(file)
                    if name not in self.training_data:
                        self.training_data[name] = {INDEX: [], ENCODINGS: [], IMAGES: []}
                    self.add_encoding_id(encoding_content)
                    self.training_data[name][INDEX].append(int(index))
                    self.training_data[name][ENCODINGS].append(encoding_content)
                    self.training_data[name][IMAGES].append(None)

    def get_training_path(self, name):
        return self.training_path / name

    def encoding_file_name(self, name, n):
        return self.get_training_path(name) / (str(n) + ".encoding")

    def image_file_name(self, name, n):
        return self.get_training_path(name) / (str(n) + ".jpg")

    def save_training_data(self):
        for name, data_list in self.training_data.items():
            os.makedirs(self.get_training_path(name), exist_ok=True)
            for index, encoding, face_image in zip(data_list[INDEX], data_list[ENCODINGS], data_list[IMAGES]):
                if not os.path.exists(self.encoding_file_name(name, index)):
                    with open(self.encoding_file_name(name, index), 'wb') as f:
                        pickle.dump(encoding, f)
                if not os.path.exists(self.image_file_name(name, index)):
                    face_image.save(self.image_file_name(name, index), "JPEG")

    def add_training_data(self):
        for media_file in self.media_set:
            if media_file.metadata[FACES].value is not None:
                n_face = 0
                print(media_file)
                for face in media_file.metadata[FACES].value["locations"]:
                    face_coord = media_file.metadata[FACES].value["locations"][n_face]
                    encoding_content = media_file.metadata[FACES].binary_value[n_face]
                    if self.get_encoding_id(encoding_content) not in self.all_encoding_ids:
                        if self.knn_clf is None or self.predict(encoding_content) == "unrecognized":
                            image = CFMImage(media_file.path)
                            face_image = image.display_face(face)
                            print("Image: {image_path}".format(image_path=media_file.path))
                            print("Face coordinates: {coord}".format(coord=str(face_coord)))
                            print('Enter a name if you want to add this face to training data: ')
                            name = input()
                            if name == "s":
                                return
                            if name == "i" or name == "":
                                name = ".ignored"
                            if name not in self.training_data:
                                self.training_data[name] = {INDEX: [], ENCODINGS: [], IMAGES: []}
                            index = 0
                            if len(self.training_data[name][INDEX]) != 0:
                                index = max(self.training_data[name][INDEX]) + 1
                            self.add_encoding_id(encoding_content)
                            self.training_data[name][INDEX].append(index)
                            self.training_data[name][ENCODINGS].append(encoding_content)
                            self.training_data[name][IMAGES].append(face_image)
                        else:
                            print("Automatically recognized")
                    n_face = n_face + 1

    def train(self):
        from sklearn import neighbors
        X = []
        y = []
        for name in self.training_data:
            if name != ".ignored":
                for encoding in self.training_data[name][ENCODINGS]:
                    X.append(encoding)
                    y.append(name)

        n_neighbors = int(round(math.sqrt(len(X))))
        print("Chose n_neighbors automatically:", n_neighbors)

        knn_algo = "ball_tree"
        self.knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
        self.knn_clf.fit(X, y)
        self.save_model()

    def save_model(self):
        with open(self.training_path / "model.bin", 'wb') as f:
            pickle.dump(self.knn_clf, f)

    def load_model(self):
        if os.path.exists(self.training_path / "model.bin"):
            with open(self.training_path / "model.bin", 'rb') as f:
                self.knn_clf = pickle.load(f)

    def predict(self, face_encoding, distance_threshold=0.6):
        closest_distances = self.knn_clf.kneighbors([face_encoding], n_neighbors=1)
        if closest_distances[0][0][0] <= distance_threshold:
            return self.knn_clf.predict([face_encoding])
        else:
            return "unrecognized"
