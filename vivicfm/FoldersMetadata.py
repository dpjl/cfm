from pathlib import Path
import json


class FoldersMetadata:

    def __init__(self, title):
        self.title = title
        self.directories = {}

    def add_model_from_file(self, filename, model):
        file_path = Path(filename)
        self.add_model_to_directory(file_path.parent, model)

    def add_model_to_directory(self, directory_path, model):
        if str(directory_path) not in self.directories:
            self.directories[str(directory_path)] = []
        if model not in self.directories[str(directory_path)]:
            self.directories[str(directory_path)].append(model)
        if directory_path.parent != directory_path:
            self.add_model_to_directory(directory_path.parent, model)

    def get_model(self, directory_path):
        if str(directory_path) in self.directories:
            if len(self.directories[str(directory_path)]) == 1:
                return self.directories[str(directory_path)][0]
            else:
                return None
        else:
            if directory_path.parent != directory_path:
                return self.get_model(directory_path.parent)
            else:
                return None

    def save(self, dir_path):
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / "camera-model-of-directories.json"
        with open(file_path, 'w') as f:
            json.dump(self.directories, f, indent=4)
        print("=> list of computed camera models of directories saved in : " + str(file_path.resolve()))
        print("")

    def print(self):
        print("=================================")
        print("| " + self.title)
        print("=================================")
        for filepath, modelList in self.directories.items():
            print(str(filepath) + ":" + str(modelList))
