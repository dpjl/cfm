import io
from datetime import datetime, timedelta
from io import BytesIO

import pytz

from camerafile.mdtools.JPEGMdReader import JPEGMdReader
from camerafile.mdtools.MdConstants import MetadataNames
from camerafile.mdtools.kaitai.quicktime_mov import QuicktimeMov


class QTMdReader:

    def __init__(self, file):
        self.file = file
        self.metadata = {}
        self.read_metadata()

    def read_metadata(self):
        parsed_data = QuicktimeMov.from_file(self.file)
        self.read_atoms(parsed_data.atoms)

    def read_atoms(self, atom_list):
        for atom in atom_list.items:
            if isinstance(atom.body, QuicktimeMov.AtomList):
                self.read_atoms(atom.body)
            elif atom.atom_type == QuicktimeMov.AtomType.tkhd:
                self.parse_tkhd(atom.body)
            elif atom.atom_type == QuicktimeMov.AtomType.meta:
                self.parse_meta(atom.body)
            elif atom.atom_type == QuicktimeMov.AtomType.udta:
                self.parse_udta(atom.body)
            elif atom.atom_type == QuicktimeMov.AtomType.mvhd:
                self.parse_mvhd(atom.body)

    def parse_mvhd(self, parsed_atom):
        if parsed_atom.creation_time != 0:
            date = datetime(1904, 1, 1)
            delta = timedelta(seconds=parsed_atom.creation_time)
            self.metadata['creationdate'] = (date + delta).replace(tzinfo=pytz.utc)

    def read_array(self, content, max_size):
        bin_data = BytesIO(content)
        b = bin_data.read(1)
        array = []
        size = 0
        while b != b"" and size != max_size:
            item = ""
            while b != b"" and b != b'\x00':
                item += b.decode("latin1")
                b = bin_data.read(1)
            array.append(item.strip())
            size += 1
            while b != b'' and b == b'\x00':
                b = bin_data.read(1)
        return array

    def parse_udta(self, parsed_atom):
        pos = 0
        while pos < len(parsed_atom):
            size = int.from_bytes(parsed_atom[pos: pos + 4], "big")
            if size == 0:
                break
            pos += 4
            tag = parsed_atom[pos:pos + 4]
            pos += 4
            content = parsed_atom[pos:pos + size - 8]
            if b"DMC-GX80" in content:
                print(str(int.from_bytes(content[0: 4], "little")))
                print(tag)
                print(content[92:200])
            if tag == b"TAGS":
                array = self.read_array(content, 2)
                if len(array) > 1:
                    self.metadata["make"] = array[0]
                    self.metadata["model"] = array[1]
            elif tag == b"CNTH":
                self.parse_cnth(content)
            elif tag == b"CNCV":
                self.metadata["compressor"] = content.decode().strip("\x00")
            elif tag == b"CNMN":
                self.metadata["model"] = content.decode().strip("\x00")
            elif tag == b"CNFV":
                self.metadata["firmware"] = content.decode().strip("\x00")
            pos += size - 8

    def parse_cnth(self, parsed_atom):
        pos = 0
        while pos < len(parsed_atom):
            size = int.from_bytes(parsed_atom[pos: pos + 4], "big")
            if size == 0:
                break
            pos += 4
            tag = parsed_atom[pos:pos + 4]
            pos += 4
            content = parsed_atom[pos:pos + size - 8]
            if tag == b"CNDA":
                m = JPEGMdReader(io.BytesIO(content)).get_metadata(MetadataNames.ORIENTATION, MetadataNames.MODEL, MetadataNames.CREATION_DATE)
                self.metadata[MetadataNames.ORIENTATION] = m[MetadataNames.ORIENTATION]
                self.metadata['model'] = m[MetadataNames.MODEL]
                self.metadata[MetadataNames.CREATION_DATE] = m[MetadataNames.CREATION_DATE]
            pos += size - 8

    def parse_tkhd(self, parsed_atom):
        width = float(str(parsed_atom.width.int_part) + "." + str(parsed_atom.width.frac_part))
        if width != 0:
            self.metadata["width"] = width
        height = float(str(parsed_atom.height.int_part) + "." + str(parsed_atom.height.frac_part))
        if height != 0:
            self.metadata["height"] = height
        duration = parsed_atom.duration
        if height != 0:
            self.metadata["duration"] = duration

        return self.metadata

    def parse_meta(self, bin_string):

        bin_data = BytesIO(bin_string)
        bin_data.seek(16, 1)
        header_version = bin_data.read(4).decode("latin1")
        if header_version != "mdta":
            return
        bin_data.seek(33, 1)

        keys = []
        values = []
        l = bin_data.read(1)
        h = bin_data.read(4).decode("latin1")
        while h == "mdta":
            data = ""
            b = bin_data.read(1)
            while b != b'\x00':
                data += b.decode("latin1")
                b = bin_data.read(1)
            keys.append(data.lower().strip())
            while b == b'\x00':
                b = bin_data.read(1)
            l = b
            h = bin_data.read(4).decode("latin1")

        i = 0
        while i < len(keys):
            h = ""
            while h != "data":
                b = bin_data.read(1)
                while b == b'\x00':
                    b = bin_data.read(1)
                b = bin_data.read(1)
                if b != b'\x00':
                    h = b.decode("latin1")
                    h += bin_data.read(3).decode("latin1")
            bin_data.seek(8, 1)
            data = ""
            b = bin_data.read(1)
            while b != b'\x00' and b != b'':
                data += b.decode("latin1")
                b = bin_data.read(1)
            values.append(data.strip())
            i += 1

        for i in range(0, min(len(keys), len(values))):

            key = keys[i]
            if key.startswith("com.apple.quicktime."):
                key = key[20:]

            if key == "creationdate":
                self.metadata[key] = datetime.strptime(values[i], "%Y-%m-%dT%H:%M:%S%z").astimezone(pytz.UTC)
            else:
                self.metadata[key] = values[i]

        return self.metadata

    def load_from_result(self, metadata_name):
        # by default, we return the creation date of the exif thumbnail if it exists, because on other dates, there is
        # a uncertainty about the zone (should be UTC, but not always)
        if metadata_name == MetadataNames.CREATION_DATE and MetadataNames.CREATION_DATE in self.metadata:
            return self.metadata[MetadataNames.CREATION_DATE]
        if metadata_name == MetadataNames.CREATION_DATE and 'creationdate' in self.metadata:
            # Only for non regression because it was not returned by exif tool
            return None
            #return self.metadata['creationdate']
        if metadata_name == MetadataNames.THUMBNAIL:
            return None
        if metadata_name == MetadataNames.WIDTH and 'width' in self.metadata:
            return int(self.metadata['width'])
        if metadata_name == MetadataNames.HEIGHT and 'height' in self.metadata:
            return int(self.metadata['height'])
        if metadata_name == MetadataNames.ORIENTATION and MetadataNames.ORIENTATION in self.metadata:
            return self.metadata[MetadataNames.ORIENTATION]
        if metadata_name == MetadataNames.MODEL and 'model' in self.metadata:
            return self.metadata['model']
        else:
            return None

    def get_metadata(self, *args):
        return {metadata_name: self.load_from_result(metadata_name) for metadata_name in args}


if __name__ == '__main__':
    # r = QTMdReader(r"P:\arbo\perso\cfm\tests\data\iphone\backup\IMG_0719.MOV")
    # r =  QTMdReader(r"tests/data/iphone/backup/IMG_0719.MOV")
    # r = QTMdReader(r"tests/data/camera3-canon-reflex/MVI_0569.MOV")
    # r = QTMdReader(r"tests/data/iphone/backup/IMG_0858.MOV")
    # r = QTMdReader(r"P:/arbo/perso/cfm/tests/data/mov/MVI_0018.MOV")
    #r = QTMdReader(r"E:\data\photos-all\depuis-samsung-T5/photos/2006/photos mamie noel 2006/103NIKON/DSCN1587.MOV")
    #r = QTMdReader(r"E:\data\photos-all\canon 550D/videos/2012-07-01 powershot-sx230/MVI_0018.MOV")
    r = QTMdReader(r"E:\data\photos-all\poco-f1/panasonic/P1030001.MP4")

    # canon 550D/videos/2012-07-01 powershot-sx230/MVI_0018.MOV : mauvaise date
    # depuis-samsung-T5/photos/2006/photos mamie noel 2006/103NIKON/DSCN1587.MOV: manque le datamodel
    # poco-f1/panasonic/P1030001.MP4: missing model

    # r = QTMdReader(r"tests/data/whatsapp/Media/WhatsApp Video/Sent/VID-20210123-WA0000.mp4")
    print(str(r.metadata))

    # import av

    # a = av.open(r"P:\arbo\perso\cfm\tests\data\iphone\backup\IMG_0719.MOV")
    # v = a.streams.video[0]
    # print(a.streams.video[0])
    # for frame in a.decode(video=0):
    #    frame.to_image().save('frame-%04d.jpg' % frame.index)
    #    break
