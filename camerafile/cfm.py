import argparse
import logging.config
import os
from multiprocessing.spawn import freeze_support
from pathlib import Path
from textwrap import dedent

import sys

from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import init_logging
from camerafile.core.MediaSet import MediaSet
from camerafile.core.Resource import Resource
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.processor.BatchComputeCm import BatchComputeCm
from camerafile.processor.BatchComputeNecessarySignaturesMultiProcess import BatchComputeNecessarySignaturesMultiProcess
from camerafile.processor.BatchCopy import BatchCopy
from camerafile.processor.BatchDetectFaces import BatchDetectFaces
from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd
from camerafile.processor.BatchRecoFaces import BatchRecoFaces
from camerafile.processor.CompareMediaSets import CompareMediaSets
from camerafile.processor.SearchForDuplicates import SearchForDuplicates

COMMAND = "command"

LOGGER = logging.getLogger(__name__)


def create_main_args_parser():
    parser = argparse.ArgumentParser(description=dedent("This command line tool can be used to easily execute some "
                                                        "actions on media files. CFM includes and calls "
                                                        "three external free tools: exiftool, ffmpeg and dlib."))

    parser.add_argument('-w', '--workers', type=int,
                        help="maximum number of CFM workers that can be run simultaneously. 0 means that only main CFM "
                             "process is used. Default: number of CPU.", metavar="N")

    parser.add_argument('-n', '--thumbnails', action='store_true',
                        help='load all thumbnails from exif data, and save them in cache')

    parser.add_argument('-b', '--use-db', action='store_true',
                        help='use sqlite db to store media set information')

    parser.add_argument('-u', '--use-dump', action='store_true',
                        help='use python dump to store media set informmation (faster than db)')

    parser.add_argument('-x', '--exit-on-error', action='store_true',
                        help='exit current process in case of error (should be used only to debug)')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='display debug information')

    parser.add_argument('-p', '--password', type=str,
                        help='password of the CFM zip sync file (contains deleted and unknown files)', metavar="**")

    parser.add_argument('-v', '--version', action='store_true', help='print version number')

    sp_list = parser.add_subparsers(title="Commands list",
                                    description="Use 'cfm <command> -h' to display the help of a specific command",
                                    metavar="<command>")

    p = sp_list.add_parser("analyze", aliases=["a"], help='Analyze a media set')
    p.set_defaults(command="analyze")
    p.add_argument('dir1', metavar='dir1', type=str, help='Check for duplicates')
    p.add_argument('dir2', nargs='?', metavar='dir2', type=str, help='Check for duplicates / differences with dir1')
    p.add_argument('-g', '--generate-pdf', action='store_true', help='Generate pdf reports using thumbnails')

    desc = 'Fill and organize <dir2> in order for it to contain exactly one version ' \
           'of each distinct media files of <dir1>'
    p = sp_list.add_parser("organize", aliases=["o"], description=desc, help=desc)
    p.set_defaults(command="organize")
    p.add_argument('dir1', metavar='dir1', type=str, help='Origin media set directory')
    p.add_argument('dir2', metavar='dir2', type=str, help='Destination media set directory')
    p.add_argument('-f', '--format', metavar='<format>', type=str, help='format to use for organization')
    p.add_argument('-m', '--mode', metavar="<mode>", type=CopyMode.argparse, choices=list(CopyMode),
                   help='S: Soft Link, H: Hard Link, C: Copy. Default: H (Hard Link)')

    p = sp_list.add_parser("recognize", aliases=["r"], help="Recognize faces on images")
    p.set_defaults(command="recognize")
    p.add_argument('dir1', metavar='dir1', type=str, help='Delete all duplicates from d1')
    p.add_argument('-e', '--extract-faces', action='store_true', help='Extract the faces from the images')
    p.add_argument('-l', '--learn-faces', action='store_true', help='Learn to recognize the extracted faces')
    p.add_argument('-i', '--identify-faces', action='store_true', help='Identity the extracted faces')
    p.add_argument('-k', '--keep-size', action='store_true', help='Keep original size for face detection')

    p = sp_list.add_parser("custom", aliases=["c"], help='Exexute a custom processor')
    p.set_defaults(command="custom")
    p.add_argument('processor', type=str, help='Name of the processor to execute')
    p.add_argument('args', nargs='*', metavar='arguments', type=str, help='Arguments of the custom processor')

    return parser


def execute(args):
    if args.command == "custom":
        import importlib
        ProcessorClass = getattr(importlib.import_module("camerafile.processor." + args.processor), args.processor)
        p = ProcessorClass()
        p.execute(*tuple(args.args))
        return

    media_set1 = MediaSet.load_media_set(args.dir1)
    media_set2 = None
    if "dir2" in args and args.dir2:
        media_set2 = MediaSet.load_media_set(args.dir2)

    BatchReadInternalMd(media_set1).execute()
    BatchComputeCm(media_set1).execute()

    if media_set2:
        BatchReadInternalMd(media_set2).execute()
        BatchComputeCm(media_set2).execute()

    if args.command == "analyze":
        SearchForDuplicates.execute(media_set1)

        if media_set2:
            SearchForDuplicates.execute(media_set2)
            CompareMediaSets.execute(media_set1, media_set2)

    if args.command == "organize":
        copy_mode = args.mode if args.mode is not None else CopyMode.HARD_LINK
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()
        BatchCopy(media_set1, media_set2, copy_mode).execute()

    if args.command == "recognize":
        if args.extract_faces:
            BatchDetectFaces(media_set1).execute()
        if args.learn_faces:
            media_set1.train()
        if args.identify_faces:
            BatchRecoFaces(media_set1).execute()

    print("")

    media_set1.save_on_disk()
    media_set1.close_database()

    if media_set2:
        media_set2.save_on_disk()
        media_set2.close_database()


def main():
    freeze_support()
    parser = create_main_args_parser()
    args = parser.parse_args()

    if COMMAND not in args:
        parser.print_usage()
        print(os.linesep + "error: no commands supplied")
        sys.exit(1)

    Resource.init()
    if args.command != "custom":
        init_logging(Path(args.dir1))
    LOGGER.info("C a m e r a   F i l e s   M a n a g e r - version 0.1 - DpjL")
    Configuration.get().init(args)
    execute(args)


if __name__ == '__main__':
    main()
