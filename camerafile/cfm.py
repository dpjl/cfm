import argparse
import logging.config
import os
import sys
from multiprocessing.process import current_process
from multiprocessing.spawn import freeze_support
from textwrap import dedent

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import CopyMode

COMMAND = "command"
ANALYZE_CMD = "analyze"
ORGANIZE_CMD = "organize"
RECOGNIZE_CMD = "recognize"
CUSTOM_CMD = "custom"

LOGGER = logging.getLogger(__name__)


def create_main_args_parser():
    parser = argparse.ArgumentParser(description=dedent("This command line tool can be used to easily execute some "
                                                        "actions on media files. CFM includes and calls "
                                                        "three external free tools: exiftool, ffmpeg and dlib."))

    parser.add_argument('-w', '--workers', type=int,
                        help="maximum number of CFM workers that can be run simultaneously. 0 means that only main CFM "
                             "process is used. Default: number of CPU.", metavar="N")

    parser.add_argument('-c', '--cache-path', type=str,
                        help='Specify a cache directory path. Default is empty.'
                             'If empty, one cache folder called ".cfm" is created in each media set directory',
                        default=None,
                        metavar="<path>")

    parser.add_argument('-i', '--ignore', action='append', default=None,
                        help='Specify filename patterns to ignore. This option can be used multiple times.')

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

    p = sp_list.add_parser(ANALYZE_CMD, aliases=["a"], help='Analyze a media set')
    p.set_defaults(command=ANALYZE_CMD)
    p.add_argument('dir1', metavar='dir1', type=str, default=None, help='Check for duplicates')
    p.add_argument('dir2', nargs='?', metavar='dir2', type=str, default=None,
                   help='Check for duplicates / differences with dir1')
    p.add_argument('-g', '--generate-pdf', action='store_true', help='Generate pdf reports using thumbnails')
    p.add_argument('-n', '--no-internal-read', action='store_true', help='Do not read internal metadata at all')

    desc = 'Fill and organize <dir2> in order for it to contain exactly one version ' \
           'of each distinct media files of <dir1>'
    p = sp_list.add_parser(ORGANIZE_CMD, aliases=["o"], description=desc, help=desc)
    p.set_defaults(command=ORGANIZE_CMD)
    p.add_argument('dir1', metavar='dir1', type=str, default=None, help='Origin media set directory')
    p.add_argument('dir2', metavar='dir2', type=str, default=None, help='Destination media set directory')
    p.add_argument('-f', '--format', metavar='<format>', type=str, help='format to use for organization')
    p.add_argument('-m', '--mode', metavar="<mode>", type=CopyMode.argparse, choices=list(CopyMode),
                   help='S: Soft Link, H: Hard Link, C: Copy. Default: H (Hard Link)')

    p = sp_list.add_parser(RECOGNIZE_CMD, aliases=["r"], help="Recognize faces on images")
    p.set_defaults(command=RECOGNIZE_CMD)
    p.add_argument('dir1', metavar='dir1', type=str, default=None, help='Delete all duplicates from d1')
    p.add_argument('-e', '--extract-faces', action='store_true', help='Extract the faces from the images')
    p.add_argument('-l', '--learn-faces', action='store_true', help='Learn to recognize the extracted faces')
    p.add_argument('-i', '--identify-faces', action='store_true', help='Identity the extracted faces')
    p.add_argument('-k', '--keep-size', action='store_true', help='Keep original size for face detection')

    p = sp_list.add_parser(CUSTOM_CMD, aliases=["c"], help='Execute a custom processor')
    p.set_defaults(command=CUSTOM_CMD)
    p.add_argument('processor', type=str, help='Name of the processor to execute')
    p.add_argument('args', nargs='*', metavar='arguments', type=str, help='Arguments of the custom processor')

    return parser


def execute(args):
    from camerafile.core.MediaSet import MediaSet
    from camerafile.processor.BatchComputeCm import BatchComputeCm
    from camerafile.processor.BatchComputeNecessarySignatures import \
        BatchComputeNecessarySignaturesMultiProcess
    from camerafile.processor.BatchCopy import BatchCopy
    from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd
    from camerafile.processor.CompareMediaSets import CompareMediaSets
    from camerafile.processor.SearchForDuplicates import SearchForDuplicates

    if args.command == CUSTOM_CMD:
        import importlib
        processor_class = getattr(importlib.import_module("camerafile.processor." + args.processor), args.processor)
        processor_class(*tuple(args.args))
        return

    media_set1 = MediaSet.load_media_set(args.dir1)
    media_set2 = None
    other_md_needed = ()
    if args.dir2 is not None:
        media_set2 = MediaSet.load_media_set(args.dir2, Configuration.get().org_format)
        other_md_needed = media_set2.state.get_metadata_needed_by_format()

    BatchReadInternalMd(media_set1, other_md_needed).execute()
    BatchComputeCm(media_set1).execute()

    if media_set2:
        BatchReadInternalMd(media_set2, ()).execute()
        BatchComputeCm(media_set2).execute()

    if args.command == ANALYZE_CMD:
        SearchForDuplicates.execute(media_set1)

        if media_set2:
            SearchForDuplicates.execute(media_set2)
            CompareMediaSets.execute(media_set1, media_set2)

    if args.command == ORGANIZE_CMD:

        if media_set2.org_format is None:
            print("\n!!!!!!!!!!!!!!!!!!!")
            print("Format is not already configured for " + args.dir2 + ", you have to define it using -f option.")
            print('Example: -f "{date:%Y}/{date:%m[%B]}/{cm:Unknown}"')
            print("!!!!!!!!!!!!!!!!!!!")
        else:
            copy_mode = args.mode if args.mode is not None else CopyMode.HARD_LINK
            BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()
            BatchCopy(media_set1, media_set2, copy_mode).execute()

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

    from camerafile.core.Configuration import Configuration
    from camerafile.core.Logging import init_logging
    from camerafile.core.Resource import Resource

    Resource.init()
    init_logging()
    Resource.extract_exiftool()
    LOGGER.info("Starting Camera Files Manager - version 0.3 - DpjL (pid: {pid})".format(pid=current_process().pid))
    Configuration.get().init(args)
    execute(args)


if __name__ == '__main__':
    main()
