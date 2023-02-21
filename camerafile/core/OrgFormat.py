import re
from datetime import datetime
from unittest.mock import patch

import camerafile
from camerafile.core.MediaFile import MediaFile
from camerafile.mdtools.MdConstants import MetadataNames


class OrgFormat:

    def __init__(self, format_description: str):
        self.format_description = format_description
        self.fields = re.findall(r'({.*?:.*?})', format_description)
        self.contents = []
        self.duplicates = {}
        for field in self.fields:
            self.contents.append(re.findall(r'{(.*?):(.*?)}', field)[0])

    def init_duplicates(self, media_set: "MediaSet"):
        self.duplicates = media_set.duplicates_map()

    def get_formatted_string(self, media: MediaFile):
        result = self.format_description
        media_date = None
        for field, (name, argument) in zip(self.fields, self.contents):
            if name == "cm":
                cm = media.get_camera_model()
                if cm is None:
                    cm = argument
                else:
                    cm = cm.replace(" ", "-")
                result = result.replace(field, cm)
            elif name == "date":
                if media_date is None:
                    media_date = media.get_date()
                formatted_date = media_date.strftime(argument)
                result = result.replace(field, formatted_date)
            elif name == "dup-id":
                result = result.replace(field, str(self.duplicates[media][2]))
            elif name == "dup-nb":
                result = result.replace(field, str(self.duplicates[media][0]))
            elif name == "dup-group":
                result = result.replace(field, str(self.duplicates[media][1]))
            elif name == "extension":
                result = result.replace(field, media.get_extension())
            else:
                pass
        return result

    def get_metadata_list(self):
        result = []
        for name, argument in self.contents:
            result.append(MetadataNames.from_str(name))
        return result


if __name__ == '__main__':
    org = OrgFormat("{date:%Y}/{date:%m[%B]}/{cm:Unknown}")
    with patch("camerafile.core.MediaFile.MediaFile", ) as mock:
        f = mock.return_value
        f.get_camera_model.return_value = "CamCam"
        f.get_date.return_value = datetime.now()
        print(org.get_formatted_string(camerafile.core.MediaFile.MediaFile(None, None, None)))
