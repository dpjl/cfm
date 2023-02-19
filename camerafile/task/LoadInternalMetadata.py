import re
from datetime import datetime

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccessFactory import FileAccessFactory
from camerafile.fileaccess.FileDescription import FileDescription
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.metadata.Metadata import Metadata
from camerafile.processor.BatchTool import BatchElement


class LoadInternalMetadata:
    md_needed = None

    @staticmethod
    def execute(batch_element: BatchElement):
        root_dir, file_description, metadata = batch_element.args
        thumbnail = None
        try:
            thumbnail = LoadInternalMetadata.load_internal_metadata(root_dir, file_description, metadata)
        except BaseException as e:
            if Configuration.get().exit_on_error:
                raise
            else:
                batch_element.error = "LoadInternalMetadata: [{info}] - ".format(info=batch_element.info) + str(e)
        batch_element.args = None
        batch_element.result = (file_description.get_id(), thumbnail, metadata)
        return batch_element

    @staticmethod
    def load_internal_metadata(root_dir: str, file_description: FileDescription, metadata: Metadata):
        file_access = FileAccessFactory.get(root_dir, file_description)
        args = LoadInternalMetadata.md_needed
        metadata.call_info, result = file_access.read_md(args)

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

        if date is None and camera_model is None:
            date, camera_model = LoadInternalMetadata.parse_whatsapp_filename(file_description.name)

        last_modified_date = file_access.get_last_modification_date()

        if date is None:
            date = last_modified_date

        if date is not None:
            date = date.strftime("%Y/%m/%d %H:%M:%S.%f")

        if last_modified_date is not None:
            last_modified_date = last_modified_date.strftime("%Y/%m/%d %H:%M:%S.%f")

        # if camera_model is not None and camera_model != "" and self.file_access.extension in Constants.VIDEO_TYPE:
        #    print(str(self.file_access.relative_path) + ":" + camera_model)

        metadata.value = {MetadataNames.MODEL.value: camera_model,
                          MetadataNames.CREATION_DATE.value: date,
                          MetadataNames.MODIFICATION_DATE.value: last_modified_date,
                          MetadataNames.WIDTH.value: width,
                          MetadataNames.HEIGHT.value: height,
                          MetadataNames.ORIENTATION.value: orientation}

        return thumbnail

    @staticmethod
    def parse_whatsapp_filename(file_name):
        fields = re.findall(r'^(VID|IMG)-([0-9]{8})-WA[0-9]{4}\.(jpg|jpeg|mp4)$', file_name)
        if len(fields) == 1 and len(fields[0]) == 3:
            str_date = fields[0][1]
            date = None
            try:
                return datetime.strptime(str_date, '%Y%m%d'), "WhatsApp"
            except ValueError:
                pass
        return None, None


if __name__ == '__main__':
    from camerafile.fileaccess.StandardFileDescription import StandardFileDescription

    print(LoadInternalMetadata.parse_whatsapp_filename("VID-20210201-WA0000.mp4"))
    m = Metadata()
    file_desc = StandardFileDescription(
        "2010/photos balade 18\\u00e8me/Photos Iphone/IMG_0158.MOV".encode().decode('unicode-escape'))
    LoadInternalMetadata.load_internal_metadata("E:/data/photos-all/depuis-samsung-T5/photos/", file_desc, m)
    print(m.value)
