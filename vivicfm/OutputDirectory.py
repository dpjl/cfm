
import os
import uuid
from pathlib import Path


class OutputDirectory:

    FILE_WITH_INPUT_PATH = "input_path.txt"
    path = None

    @staticmethod
    def init(base_output_path, input_path):
        os.makedirs(base_output_path, exist_ok=True)
        OutputDirectory.path = None
        files_and_dirs = os.listdir(base_output_path)
        for file_or_dir in files_and_dirs:
            if os.path.isdir(Path(base_output_path) / file_or_dir):
                dir_path = Path(base_output_path) / file_or_dir
                file_with_input_path = dir_path / OutputDirectory.FILE_WITH_INPUT_PATH
                if os.path.exists(file_with_input_path):
                    with open(file_with_input_path, "r") as f:
                        line = f.readline().strip()
                        if line == str(input_path):
                            OutputDirectory.path = dir_path
                            break
        if OutputDirectory.path is None:
            OutputDirectory.path = base_output_path / (input_path.name + "-" + uuid.uuid4().hex[:8])
            OutputDirectory.path.mkdir(parents=True, exist_ok=True)
            file_with_input_path = OutputDirectory.path / OutputDirectory.FILE_WITH_INPUT_PATH
            with open(file_with_input_path, "w") as f:
                f.write(str(input_path))


