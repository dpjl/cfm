import io
from datetime import datetime

from PIL import ExifTags, TiffImagePlugin
from PIL.Image import Exif

from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.mdtools.kaitai.avi import Avi


class AVIMdReader:

    def __init__(self, file):
        self.file = file
        self.metadata = {}
        self.read_metadata()

    def read_metadata(self):
        avi = Avi.from_file(self.file)
        self.read_blocks(avi.data)

    def read_blocks(self, blocks: Avi.Blocks):
        for block in blocks.entries:
            if block.four_cc == Avi.ChunkType.list:
                self.read_blocks(block.data.data)
            elif block.four_cc == Avi.ChunkType.avih:
                self.parse_avih(block)
            elif block.four_cc == Avi.ChunkType.strd:
                self.parse_strd(block)
            elif block.four_cc == Avi.ChunkType.idit:
                self.metadata['DateTimeOriginal'] = block.data

    def parse_avih(self, block: Avi.Block):
        width = block.data.width
        if width != 0:
            self.metadata["width"] = width
        height = block.data.height
        if height != 0:
            self.metadata["height"] = height

    def parse_strd(self, block: Avi.Block):
        # AVIF: exif format
        if block.data[0:4] != b'AVIF':
            return
        exif = Exif()
        info = TiffImagePlugin.ImageFileDirectory_v2(b"\x49\x49\x2a\x00\x08\x00\x00\x00")
        exif.endian = info._endian
        exif.load_from_fp(io.BytesIO(block.data[8:]), 0)

        for tag, value in exif.items():
            if isinstance(value, str):
                value = value.strip("\u0000").strip(" ")
            self.metadata[ExifTags.TAGS[tag]] = value
        for tag, value in exif.get_ifd(0x8769).items():
            if isinstance(value, str):
                value = value.strip("\u0000").strip(" ")
            self.metadata[ExifTags.TAGS[tag]] = value

    def load_from_result(self, metadata_name):
        if metadata_name == MetadataNames.CREATION_DATE and 'DateTimeOriginal' in self.metadata:
            try:
                return datetime.strptime(self.metadata['DateTimeOriginal'], "%a %b %d %H:%M:%S %Y")
            except:
                return datetime.strptime(self.metadata['DateTimeOriginal'], "%Y:%m:%d %H:%M:%S")
        if metadata_name == MetadataNames.THUMBNAIL:
            return self.read_thumbnail()
        if metadata_name == MetadataNames.WIDTH and 'width' in self.metadata:
            return self.metadata['width']
        if metadata_name == MetadataNames.HEIGHT and 'height' in self.metadata:
            return self.metadata['height']
        if metadata_name == MetadataNames.ORIENTATION:
            return None
        if metadata_name == MetadataNames.MODEL and 'Model' in self.metadata:
            return self.metadata['Model']
        else:
            return None

    def get_metadata(self, *args):
        return {metadata_name: self.load_from_result(metadata_name) for metadata_name in args}


if __name__ == '__main__':
    #r = AVIMdReader(r"P:\arbo\perso\cfm\tests\data/camera4/15mai 071.avi")
    r = AVIMdReader(r"P:\arbo\perso\cfm\tmp\test-data\mada - avril 2012\113___04\MVI_1768.AVI")
    print(str(r.metadata))
