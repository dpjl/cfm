import argparse
import logging.config
from multiprocessing.spawn import freeze_support
from pathlib import Path
from textwrap import dedent

from camerafile.core import Configuration
from camerafile.core.Logging import init_logging
from camerafile.core.MediaSet import MediaSet
from camerafile.core.Resource import Resource
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.processor.BatchComputeCm import BatchComputeCm
from camerafile.processor.BatchCopy import BatchCopy
from camerafile.processor.BatchDelete import BatchDelete
from camerafile.processor.BatchDetectFaces import BatchDetectFaces
from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd
from camerafile.processor.BatchRecoFaces import BatchRecoFaces
from camerafile.processor.CompareMediaSets import CompareMediaSets
from camerafile.processor.SearchForDuplicates import SearchForDuplicates
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess

LOGGER = logging.getLogger(__name__)


def create_main_args_parser():
    parser = argparse.ArgumentParser(description=dedent("This command line tool can be used to easily execute some "
                                                        "actions on media files. CFM includes and calls "
                                                        "three external free tools: exiftool, ffmpeg and dlib."))

    parser.add_argument('-w', '--workers', type=int,
                        help="maximum number of CFM workers that can be run simultaneously. 0 means that only main CFM "
                             "process is used. Default: number of CPU.", metavar="N")

    parser.add_argument('-b', '--thumbnails', action='store_true',
                        help='load all thumbnails from exif data, and save them in cache')

    parser.add_argument('-d', '--use-db', action='store_true',
                        help='use sqlite db to store media set information')

    parser.add_argument('-u', '--use-dump', action='store_true',
                        help='use python dump to store media set informmation (faster than db)')

    parser.add_argument('-x', '--exit-on-error', action='store_true',
                        help='exit current process in case of error (should be used only to debug)')

    parser.add_argument('-p', '--password', type=str,
                        help='password of the CFM zip sync file (contains deleted and unknown files)', metavar="**")

    parser.add_argument('-v', '--version', action='store_true', help='print version number')

    sp_list = parser.add_subparsers(title="Commands list",
                                    description="Use 'cfm <command> -h' to display the help of a specific command",
                                    metavar="<command>", dest='command')

    p = sp_list.add_parser("analyze", aliases=["a"], help='Analyze a media set')
    p.add_argument('dir1', metavar='dir1', type=str, help='Check for duplicates')
    p.add_argument('dir2', nargs='?', metavar='dir2', type=str, help='Check for duplicates / differences with dir1')
    p.add_argument('-g', '--generate-pdf', action='store_true', help='Generate pdf reports using thumbnails')

    desc = 'Fill and organize <dir2> in order for it to contain exactly one version ' \
           'of each distinct media files of <dir1>'
    p = sp_list.add_parser("organize", aliases=["o"], description=desc, help=desc)
    p.add_argument('dir1', metavar='dir1', type=str, help='Origin media set directory')
    p.add_argument('dir2', metavar='dir2', type=str, help='Destination media set directory')
    p.add_argument('-f', '--format', metavar='<format>', type=str, help='format to use for organization')
    p.add_argument('-m', '--mode', metavar="<mode>", type=CopyMode.argparse, choices=list(CopyMode),
                   help='S: Soft Link, H: Hard Link, C: Copy. Default: H (Hard Link)')

    desc = 'Move to trash files from <dir2> that are not in <dir1>'
    p = sp_list.add_parser("delete", aliases=["d"], description=desc, help=desc)
    p.add_argument('dir1', metavar='dir1', type=str, help='Origin media set directory')
    p.add_argument('dir2', metavar='dir2', type=str, help='Destination media set directory')

    p = sp_list.add_parser("extract-faces", aliases=["e"], help='Extract the faces from the images')
    p.add_argument('dir1', metavar='dir1', type=str, help='Delete all duplicates from d1')
    p.add_argument('-k', '--keep-size', action='store_true', help='Keep original size for face detection')

    p = sp_list.add_parser("learn-faces", aliases=["l"], help='Learn to recognize the extracted faces')
    p.add_argument('dir1', metavar='dir1', type=str, help='Delete all duplicates from d1')

    p = sp_list.add_parser("identify-faces", aliases=["i"], help='Identity the extracted faces')
    p.add_argument('dir1', metavar='dir1', type=str, help='Delete all duplicates from d1')

    p = sp_list.add_parser("custom", aliases=["c"], help='Exexute a custom processor')
    p.add_argument('dir1', metavar='dir1', type=str, help='Delete all duplicates from d1')
    p.add_argument('dir2', nargs='?', metavar='dir2', type=str, help='Delete from d2 all files that are not in d1')
    p.add_argument('-x', '--exec', type=str, help='Name of the processor to execute')

    return parser


def configure(args):
    if args.workers is not None:
        Configuration.NB_SUB_PROCESS = args.workers

    if args.use_db:
        Configuration.USE_DB_FOR_CACHE = True

    if args.use_dump:
        Configuration.USE_DUMP_FOR_CACHE = True

    if args.password:
        Configuration.CFM_SYNC_PASSWORD = args.password.encode()

    if args.exit_on_error:
        Configuration.EXIT_ON_ERROR = True

    if "generate_pdf" in args and args.generate_pdf:
        Configuration.GENERATE_PDF = True

    if args.thumbnails:
        Configuration.THUMBNAILS = True

    if "keep_size" in args and args.keep_size:
        Configuration.FACE_DETECTION_KEEP_IMAGE_SIZE = True

    Configuration.initialized = True


def execute(args):
    media_set1 = MediaSet.load_media_set(args.dir1)
    media_set2 = None
    if "dir2" in args and args.dir2:
        media_set2 = MediaSet.load_media_set(args.dir2)

    BatchReadInternalMd(media_set1).execute()
    BatchComputeCm(media_set1).execute()

    if media_set2:
        BatchReadInternalMd(media_set2).execute()
        BatchComputeCm(media_set2).execute()

    if args.command in ["analyze", "a"]:
        SearchForDuplicates.execute(media_set1)

        if media_set2:
            SearchForDuplicates.execute(media_set2)
            CompareMediaSets.execute(media_set1, media_set2)

    if args.command in ["organize", "o"]:
        copy_mode = args.mode if args.mode is not None else CopyMode.HARD_LINK
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()
        BatchCopy(media_set1, media_set2, copy_mode).execute()

    if args.command in ["delete", "d"]:
        BatchDelete(media_set1, media_set2, None).execute()

    if args.command in ["extract-faces", "e"]:
        BatchDetectFaces(media_set1).execute()

    if args.command in ["learn-faces", "l"]:
        media_set1.train()

    if args.command in ["identify-faces", "i"]:
        BatchRecoFaces(media_set1).execute()

    if args.command in ["custom", "c"]:
        import importlib
        ProcessorClass = getattr(importlib.import_module("camerafile.processor." + args.exec), args.exec)
        ProcessorClass(media_set1).execute()

        if media_set2:
            ProcessorClass(media_set2).execute()

    media_set1.save_on_disk()
    media_set1.close_database()

    if media_set2:
        media_set2.save_on_disk()
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
