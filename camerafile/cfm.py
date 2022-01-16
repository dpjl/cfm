import argparse
import logging.config
from multiprocessing.spawn import freeze_support
from pathlib import Path

from camerafile.CameraFilesProcessor import CameraFilesProcessor
from camerafile.Constants import HARD_LINKS, SYM_LINKS, FULL_COPY
from camerafile.Logging import init_logging
from camerafile.Resource import Resource

LOGGER = logging.getLogger(__name__)


def create_main_args_parser():
    parser = argparse.ArgumentParser(description='''Command line tool that can be used to easily execute some actions 
                                                 on batch of media files. Options are applied to one or 
                                                 two directories. CFM includes and calls automatically three 
                                                 (magical) tools: exiftool, ffmpeg and dlib.''')

    parser.add_argument('-a', '--analyse', action='store_true',
                        help='check for duplicates/differences')

    parser.add_argument('-g', '--generate-album', action='store_true',
                        help='generate a pdf file with all thumbnails')

    parser.add_argument('-e', '--extract-faces', action='store_true',
                        help='extract the faces from the images')

    parser.add_argument('-l', '--learn-faces', action='store_true',
                        help='learn to recognize the extracted faces')

    parser.add_argument('-i', '--identify-faces', action='store_true',
                        help='identity the persons of the extracted faces')

    parser.add_argument('-c', '--copy-files', action='store_true',
                        help='copy files from directory1 to directory2')

    parser.add_argument('-S', '--sym-links', action='store_true',
                        help='copy will create symbolic links instead of file duplication')

    parser.add_argument('-H', '--hard-links', action='store_true',
                        help='copy will create hard links instead of file duplication')

    parser.add_argument('-M', '--copy-metadata', action='store_true',
                        help='force copy of CFM metadata with -S and -H')

    parser.add_argument('-o', '--organize', action='store_true',
                        help='organize media according to a specific format')

    parser.add_argument('-f', '--org-format',
                        help='format to use for organization')

    parser.add_argument('-r', '--rm-duplicates', action='store_true',
                        help='remove duplicates')

    parser.add_argument('-w', '--workers',
                        help='maximum number of CFM workers that can be run simultaneously')

    parser.add_argument('-v', '--version', action='store_true',
                        help='print version number')

    parser.add_argument('dir1', metavar='directory1', type=str, help='first media directory path')
    parser.add_argument('dir2', metavar='directory2', nargs='?', type=str,
                        help='second media directory path, required only with options -c, optional otherwise')

    return parser


def execute(args):
    media_set1 = CameraFilesProcessor.load_media_set(args.dir1)
    media_set2 = None
    if args.dir2:
        media_set2 = CameraFilesProcessor.load_media_set(args.dir2)

    CameraFilesProcessor.BatchReadInternalMd(media_set1).execute()
    CameraFilesProcessor.BatchComputeCm(media_set1).execute()

    if media_set2:
        CameraFilesProcessor.BatchReadInternalMd(media_set2).execute()
        CameraFilesProcessor.BatchComputeCm(media_set2).execute()

    if args.analyse:
        CameraFilesProcessor.analyse_duplicates(media_set1)

        if media_set2:
            CameraFilesProcessor.analyse_duplicates(media_set2)
            CameraFilesProcessor.cmp(media_set1, media_set2)

    if args.generate_album:
        CameraFilesProcessor.BatchComputeMissingThumbnails(media_set1).execute()
        CameraFilesProcessor.BatchCreatePdf(media_set1).execute()

    if args.extract_faces:
        CameraFilesProcessor.BatchDetectFaces(media_set1).execute()

    if args.learn_faces:
        pass

    if args.identify_faces:
        CameraFilesProcessor.BatchRecoFaces(media_set1).execute()

    copy_mode = FULL_COPY

    if args.sym_links:
        copy_mode = SYM_LINKS

    if args.hard_links:
        copy_mode = HARD_LINKS

    if args.copy_files:
        CameraFilesProcessor.BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()
        CameraFilesProcessor.BatchCopy(media_set1, media_set2, copy_mode).execute()

    if args.copy_metadata:
        pass

    if args.organize:
        pass

    if args.org_format:
        pass

    if args.rm_duplicates:
        pass

    media_set1.save_database()
    media_set1.close_database()

    if media_set2:
        media_set2.save_database()
        media_set2.close_database()


def main():
    freeze_support()
    parser = create_main_args_parser()
    args = parser.parse_args()
    Resource.init()
    init_logging(Path(args.dir1))

    LOGGER.info("C a m e r a   F i l e s   M a n a g e r - version 0.1 - DpjL")
    execute(args)


if __name__ == '__main__':
    main()
