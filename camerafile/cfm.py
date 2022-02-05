import argparse
import logging.config
from multiprocessing.spawn import freeze_support
from pathlib import Path

import camerafile.core.Configuration
from camerafile.core import Configuration
from camerafile.core.Logging import init_logging
from camerafile.core.MediaSet import MediaSet
from camerafile.core.Resource import Resource
from camerafile.fileaccess.FileAccess import FileAccess
from camerafile.processor.BatchComputeCm import BatchComputeCm
from camerafile.processor.BatchComputeMissingThumbnails import BatchComputeMissingThumbnails
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess
from camerafile.processor.BatchCopy import BatchCopy
from camerafile.processor.BatchCreatePdf import BatchCreatePdf
from camerafile.processor.BatchDelete import BatchDelete
from camerafile.processor.BatchDetectFaces import BatchDetectFaces
from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd
from camerafile.processor.BatchRecoFaces import BatchRecoFaces
from camerafile.processor.CompareMediaSets import CompareMediaSets
from camerafile.processor.SearchForDuplicates import SearchForDuplicates

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
                        help='copy all files of directory1 into directory2')

    parser.add_argument('-d', '--delete-files', action='store_true',
                        help='delete duplicates or all files not in directory1 from directory2')

    parser.add_argument('-S', '--sym-links', action='store_true',
                        help='copy will create symbolic links instead of file duplication')

    parser.add_argument('-H', '--hard-links', action='store_true',
                        help='copy will create hard links instead of file duplication')

    parser.add_argument('-w', '--workers', type=int,
                        help='maximum number of CFM workers that can be run simultaneously')

    parser.add_argument('-f', '--org-format', type=str,
                        help='format to use for organization')

    parser.add_argument('-p', '--password', type=str,
                        help='password of the cfm zip sync file (contains deleted and unknown files)')

    parser.add_argument('-x', '--exec', type=str,
                        help='exec another processor')

    parser.add_argument('-v', '--version', action='store_true',
                        help='print version number')

    parser.add_argument('dir1', metavar='directory1', type=str, help='first media directory path')
    parser.add_argument('dir2', metavar='directory2', nargs='?', type=str,
                        help='second media directory path, required only with options -c, optional otherwise')

    return parser


def configure(args):
    if args.workers is not None:
        camerafile.core.Configuration.NB_SUB_PROCESS = args.workers

    if args.password:
        Configuration.CFM_SYNC_PASSWORD = args.password.encode()

    Configuration.initialized = True


def execute(args):
    if args.org_format:
        pass

    media_set1 = MediaSet.load_media_set(args.dir1)
    media_set2 = None
    if args.dir2:
        media_set2 = MediaSet.load_media_set(args.dir2)

    BatchReadInternalMd(media_set1).execute()
    BatchComputeCm(media_set1).execute()

    if media_set2:
        BatchReadInternalMd(media_set2).execute()
        BatchComputeCm(media_set2).execute()

    if args.exec:
        import importlib
        ProcessorClass = getattr(importlib.import_module("camerafile.processor." + args.exec), args.exec)
        ProcessorClass(media_set1).execute()

        if media_set2:
            ProcessorClass(media_set2).execute()

    if args.analyse:
        SearchForDuplicates.execute(media_set1)

        if media_set2:
            SearchForDuplicates.execute(media_set2)
            CompareMediaSets.execute(media_set1, media_set2)

    if args.generate_album:
        BatchComputeMissingThumbnails(media_set1).execute()
        BatchCreatePdf(media_set1).execute()

    if args.extract_faces:
        BatchDetectFaces(media_set1).execute()

    if args.learn_faces:
        media_set1.train()

    if args.identify_faces:
        BatchRecoFaces(media_set1).execute()

    copy_mode = FileAccess.FULL_COPY

    if args.sym_links:
        copy_mode = FileAccess.SYM_LINKS

    if args.hard_links:
        copy_mode = FileAccess.HARD_LINKS

    if args.copy_files or args.delete_files:
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()

    if args.copy_files:
        BatchCopy(media_set1, media_set2, copy_mode).execute()

    if args.delete_files:
        if media_set2:
            BatchDelete(media_set1, media_set2, copy_mode).execute()

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
    configure(args)
    execute(args)


if __name__ == '__main__':
    main()
