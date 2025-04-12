import re
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

from camerafile.core.MediaDuplicateManager import MediaDuplicateManager
from camerafile.core.MediaFile import MediaFile
from camerafile.mdtools.MdConstants import MetadataNames

if TYPE_CHECKING:
    from camerafile.core.MediaSet import MediaSet


class OrgFormat:

    def __init__(self, format_description: str):
        self.format_description = format_description
        self.fields = re.findall(r'({.*?:.*?})', format_description)
        self.contents = []
        self.duplicates = {}
        for field in self.fields:
            self.contents.append(re.findall(r'{(.*?):(.*?)}', field)[0])

    def init_duplicates(self, media_set: "MediaSet"):
        self.duplicates = MediaDuplicateManager.duplicates_info(media_set)

    def get_formatted_string(self, media: MediaFile):
        result = self.format_description
        for field, (name, argument) in zip(self.fields, self.contents):
            if name == "cm":
                result = result.replace(field, self.__get_cm(media, argument))
            elif name == "date":
                result = result.replace(field, self.__get_date(media, argument))
            elif name == "dup-id":
                result = result.replace(field, self.__get_dup_id(media, argument))
            elif name == "dup-nb":
                result = result.replace(field, self.__get_dup_nb(media, argument))
            elif name == "dup-group":
                result = result.replace(field, self.__get_dup_group(media, argument))
            elif name == "extension":
                result = result.replace(field, self.__get_extension(media, argument))
            elif name == "filename":
                result = result.replace(field, self.__get_filename(media, argument))
            else:
                pass
        return result

    @staticmethod
    def __get_extension(media, arg):
        return media.get_extension()

    @staticmethod
    def __get_filename(media, arg):
        return media.file_desc.name

    def __get_dup_id(self, media, arg):
        return str(self.duplicates[media][2])

    def __get_dup_nb(self, media, arg):
        return str(self.duplicates[media][0])

    def __get_dup_group(self, media, arg):
        return str(self.duplicates[media][1])

    @staticmethod
    def __get_cm(media, arg):
        cm = media.get_camera_model()
        if cm is None:
            cm = arg
        else:
            cm = cm.replace(" ", "-")
        return cm

    @staticmethod
    def __get_date(media, arg):
        return media.get_date().strftime(arg)

    def get_metadata_list(self):
        result = []
        for name, argument in self.contents:
            m = MetadataNames.from_str(name)
            if m is not None:
                result.append(m)
        return result


if __name__ == '__main__':
    org = OrgFormat("{date:%Y}/{date:%m[%B]}/{cm:Unknown}")
    with patch("camerafile.core.MediaFile.MediaFile", ) as mock:
        f = mock.return_value
        f.get_camera_model.return_value = "CamCam"
        f.get_date.return_value = datetime.now()
        # print(org.get_formatted_string(camerafile.core.MediaFile.MediaFile(None, None, None)))
