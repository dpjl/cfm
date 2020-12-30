import hashlib
import math
import os
import pickle
from pathlib import Path

from sklearn import neighbors

from camerafile.Image import Image
from camerafile.Metadata import FACES
from camerafile.OutputDirectory import OutputDirectory

INDEX = "index"
ENCODINGS = "encodings"
IMAGES = "images"


class FaceRecognition:

    def __init__(self, media_set):
        self.media_set = media_set
        self.training_path = OutputDirectory.base_path / "training_examples"
        self.all_encoding_ids = {}
        self.training_data = {}
        self.load_training_data()

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
                for face in media_file.metadata[FACES].value:
                    face_coord = media_file.metadata[FACES].value[n_face]
                    encoding_content = media_file.metadata[FACES].binary_value[n_face]
                    if self.get_encoding_id(encoding_content) not in self.all_encoding_ids:
                        image = Image(media_file.path)
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
                    n_face = n_face + 1

    def train(self):
        X = []
        y = []
        for name in self.training_data:
            for encoding in self.training_data[name][ENCODINGS]:
                X.append(encoding)
                y.append(name)

        n_neighbors = int(round(math.sqrt(len(X))))
        print("Chose n_neighbors automatically:", n_neighbors)

        knn_algo = "ball_tree"
        knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
        knn_clf.fit(X, y)

        with open(self.training_path / "model.bin", 'wb') as f:
            pickle.dump(knn_clf, f)
