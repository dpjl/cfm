from quicktimeparser.parse import Mov

from camerafile.mdtools.kaitai.quicktime_mov import QuicktimeMov


class QTMdReader(Mov):

    def __init__(self, file):
        self._f = None
        super().__init__(None)
        self.read_metadata(file)

    def read_metadata(self, file, fsize=None):
        if isinstance(file, str):
            self._fn = file
            self.parse()
        if fsize is not None:
            self._f = file
            self._parse(fsize)

    def get_metadata(self, *args):
        # retrieve the creation-time as a string (the actual creation time, not the file-system creation time)
        date = self.metadata["creation time"]

        # traverse all key-value pairs of the metadata
        for key in self.metadata.keys():
            print(key + ": " + str(self.metadata[key]))


def print_atom_list(atom_list):
    for atom in atom_list.items:
        # print(str(atom.atom_type))
        if atom.atom_type == QuicktimeMov.AtomType.tkhd:
            print("-" + str(atom.body.width.int_part) + "." + str(atom.body.width.frac_part) + "-")
            print("-" + str(atom.body.height.int_part) + "." + str(atom.body.height.frac_part) + "-")
        if isinstance(atom.body, QuicktimeMov.AtomList):
            print_atom_list(atom.body)
        elif atom.atom_type == QuicktimeMov.AtomType.meta:
            print(str(atom.body))


if __name__ == '__main__':
    QTMdReader(r"P:\arbo\perso\cfm\tests\data\iphone\backup\IMG_0719.MOV").get_metadata()

    data = QuicktimeMov.from_file(r"P:\arbo\perso\cfm\tests\data\iphone\backup\IMG_0719.MOV")
    print_atom_list(data.atoms)
