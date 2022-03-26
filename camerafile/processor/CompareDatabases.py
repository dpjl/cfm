import os

from PIL import Image

from camerafile.core.Constants import FACES
from camerafile.core.MediaSet import MediaSet


class CompareDatabases:

    def __init__(self, media_dir_1, db_file_1, media_dir_2, db_file_2):
        self.media_set_1 = MediaSet.load_media_set(media_dir_1, db_file=db_file_1)
        self.media_set_2 = MediaSet.load_media_set(media_dir_2, db_file=db_file_2)

        face_debug_path = self.media_set_1.output_directory.path / "face-diff"
        os.makedirs(face_debug_path, exist_ok=True)
        height_resize = 480

        for filename in self.media_set_1.filename_map:
            if filename not in self.media_set_2.filename_map:
                print(filename + " is in (1) but not in (2)")
                continue

            media1 = self.media_set_1.filename_map[filename]
            media2 = self.media_set_2.filename_map[filename]

            faces1 = media1.metadata[FACES].value
            faces2 = media2.metadata[FACES].value
            if faces1 and faces2:
                if len(faces1["locations"]) != len(faces2["locations"]):
                    print("Not same number of faces for : " + filename)
                    with open(face_debug_path / media1.file_access.name, "wb") as file:
                        with media1.file_access.get_image() as im1:
                            with media2.file_access.get_image() as im2:
                                im1: Image.Image = im1.get_image_with_faces(faces1["locations"])
                                im2 = im2.get_image_with_faces(faces2["locations"])

                                # frame_resize_scale = float(im1.height) / height_resize
                                # new_size = (int(im1.width // frame_resize_scale), int(im1.height // frame_resize_scale))
                                # im1 = im1.resize(new_size)
                                # im2 = im2.resize(new_size)

                                im_1_2: Image.Image = Image.new('RGB', (im1.width + im2.width, im1.height))
                                im_1_2.paste(im1, (0, 0))
                                im_1_2.paste(im2, (im1.width, 0))
                                im_1_2.save(file)
