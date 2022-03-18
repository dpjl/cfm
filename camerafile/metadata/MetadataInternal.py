import logging

from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.metadata.Metadata import Metadata

LOGGER = logging.getLogger(__name__)


class MetadataInternal(Metadata):
    md_needed = None

    def __init__(self, file_access: FileAccess):
        super().__init__(None)
        self.file_access = file_access
        self.thumbnail = None
        self.call_info = None

    def get_md_value(self, md_name):
        if self.value is not None:
            if md_name.value in self.value:
                return self.value[md_name.value]
        return None

    def get_date(self):
        return self.get_md_value(MetadataNames.CREATION_DATE)

    def get_last_modification_date(self):
        return self.get_md_value(MetadataNames.MODIFICATION_DATE)

    def load_internal_metadata(self):

        args = MetadataInternal.md_needed

        self.call_info, result = self.file_access.read_md(args)

        orientation = result[MetadataNames.ORIENTATION] if MetadataNames.ORIENTATION in result else None
        width = result[MetadataNames.WIDTH] if MetadataNames.WIDTH in result else None
        height = result[MetadataNames.HEIGHT] if MetadataNames.HEIGHT in result else None
        date = result[MetadataNames.CREATION_DATE] if MetadataNames.CREATION_DATE in result else None
        thumbnail = result[MetadataNames.THUMBNAIL] if MetadataNames.THUMBNAIL in result else None
        camera_model = result[MetadataNames.MODEL] if MetadataNames.MODEL in result else None

        if orientation is not None and (orientation == 6 or orientation == 8):
            old_width = width
            width = height
            height = old_width

        last_modified_date = self.file_access.get_last_modification_date()

        if date is None:
            date = last_modified_date

        if date is not None:
            date = date.strftime("%Y/%m/%d %H:%M:%S.%f")

        if last_modified_date is not None:
            last_modified_date = last_modified_date.strftime("%Y/%m/%d %H:%M:%S.%f")

        # if camera_model is not None and camera_model != "" and self.file_access.extension in Constants.VIDEO_TYPE:
        #    print(str(self.file_access.relative_path) + ":" + camera_model)

        self.thumbnail = thumbnail
        self.value = {MetadataNames.MODEL.value: camera_model,
                      MetadataNames.CREATION_DATE.value: date,
                      MetadataNames.MODIFICATION_DATE.value: last_modified_date,
                      MetadataNames.WIDTH.value: width,
                      MetadataNames.HEIGHT.value: height,
                      MetadataNames.ORIENTATION.value: orientation}


if __name__ == '__main__':
    from camerafile.fileaccess.StandardFileAccess import StandardFileAccess

    m = MetadataInternal(StandardFileAccess(
        'E:/data/photos-all/depuis-samsung-T5/photos/2010/photos balade 18\\u00e8me/Photos Iphone/IMG_0158.MOV'.encode().decode(
            'unicode-escape')))
    m.load_internal_metadata()
    print(m.value)
