import argparse
import logging.config
import os
import sys
from camerafile.api.ManagementApi import ManagementApi
from fastapi import FastAPI
import uvicorn
import threading
from multiprocessing.process import current_process
from multiprocessing.spawn import freeze_support
from textwrap import dedent

from camerafile.core.Configuration import Configuration
from camerafile.fileaccess.FileAccess import CopyMode
from camerafile.monitor.Watcher import Watcher
from camerafile.task.CopyFile import CollisionPolicy

VERSION = 0.3
COMMAND = "command"
ANALYZE_CMD = "analyze"
ORGANIZE_CMD = "organize"
RECOGNIZE_CMD = "recognize"
CUSTOM_CMD = "custom"

LOGGER = logging.getLogger(__name__)


def create_main_args_parser():
    parser = argparse.ArgumentParser(add_help=False,
                                     description=dedent("This command line tool can be used to easily execute some "
                                                        "actions on media files. CFM includes and calls "
                                                        "three external free tools: exiftool, ffmpeg and dlib."))

    parser.add_argument('-w', '--workers', type=int,
                        help="Maximum number of CFM workers that can be run simultaneously. 0 means that only main CFM "
                             "process is used. Default: number of CPU.", metavar="N")

    parser.add_argument('-c', '--cache-path', type=str,
                        help='Specify a cache directory path. Default is empty. '
                             'If empty, one cache folder called ".cfm" is created in each media set directory',
                        default=None,
                        metavar="<path>")

    parser.add_argument('-i', '--ignore', action='append',
                        help='Specify filename patterns to ignore. This option can be used multiple times.')

    parser.add_argument('-np', '--no-progress', action='store_true',
                        help='Do not display progress bar with tasks progression.')

    parser.add_argument('-n', '--thumbnails', action='store_true',
                        help='Load all thumbnails from exif data, and save them in cache.')

    parser.add_argument('-u', '--use-dump', action='store_true', default=True,
                        help='Use python dump to store media set information.')

    parser.add_argument('-s', '--save-db', action='store_true', default=False,
                        help='Save sqlite db on disk, each time cfm is executed. This db is NOT used to load data.')

    parser.add_argument('-x', '--exit-on-error', action='store_true', default=False,
                        help='Exit current process in case of error (should be used only to debug).')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Display debug information.')

    parser.add_argument('-v', '--version', action='version',
                        version=f'%(prog)s {VERSION}', help="Show program's version number and exit.")

    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Show this help message and exit.')

    parser.add_argument('-ui', '--ui', action='store_true', help='Start management UI.')

    parser.add_argument('-w1', '--whatsapp', action='store_true',
                        help='Deduce date from WhatsApp filename. '
                             'Does not work for some old files without date in their name.')

    parser.add_argument('-w2', '--whatsapp-db', type=str,
                        help='Specify a decrypted WhatsApp db file, in order to detect WhatsApp files and recover '
                             'their sending/receiving dates. More reliable than --whatsapp.',
                        default=None,
                        metavar="<path>")

    parser.add_argument('-w3', '--whatsapp-date-update', action='store_true',
                        help="Modify computed destination file's modification date (only for Whatsapp files).")

    sp_list = parser.add_subparsers(title="Commands list",
                                    description="Use 'cfm <command> -h' to display the help of a specific command",
                                    metavar="<command>")

    p = sp_list.add_parser(ANALYZE_CMD, add_help=False, aliases=["a"], help='Analyze a media set.')
    p.set_defaults(command=ANALYZE_CMD)
    p.add_argument('dir1', metavar='dir1', type=str, default=None, help='Check for duplicates')
    p.add_argument('dir2', nargs='?', metavar='dir2', type=str, default=None,
                   help='Check for duplicates / differences with dir1.')
    p.add_argument('-g', '--generate-pdf', action='store_true', default=False,
                   help='Generate pdf reports using thumbnails.')
    p.add_argument('-n', '--no-internal-read', action='store_true', help='Do not read internal metadata at all.')
    p.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                   help='Show this help message and exit.')

    desc = 'Copy all media files of <dir1> into <dir2>, using a customizable organization format.'
    p = sp_list.add_parser(ORGANIZE_CMD, add_help=False, aliases=["o"], description=desc, help=desc)
    p.set_defaults(command=ORGANIZE_CMD)
    p.add_argument('dir1', metavar='dir1', type=str, default=None, help='Origin media set directory.')
    p.add_argument('dir2', metavar='dir2', type=str, default=None, help='Destination media set directory.')
    p.add_argument('-f', '--format', metavar='<format>', type=str, default=os.getenv("ORG_FORMAT"),
                   help='Format to use for organization.')
    p.add_argument('-d', '--delete-in-target', action='store_true', help='If set, delete files from destination folder if they are not anymore in origin folder.')
    p.add_argument('-i', '--ignore-duplicates', action='store_true', help='If set, duplicates are not copied.')
    p.add_argument('-w', '--watch', action='store_true', help='Watch continuously <dir1> and keep organized <dir2>.')
    p.add_argument('-s', '--sync-delay', type=int, default=os.getenv("SYNC_DELAY"), metavar="N",
                   help='Used only if -w is defined. Number of seconds to wait before processing after a change has been detected.')
    p.add_argument('-pps', '--post-processing-script', metavar="<path>", type=str, default=os.getenv("PP_SCRIPT"),
                   help="Script that will be called at the end of each process triggered when watching.")
    p.add_argument('-m', '--mode', metavar="<mode>", type=CopyMode.argparse, choices=list(CopyMode),
                   default=str(CopyMode.HARD_LINK),
                   help=f'{list(CopyMode)} - Default: {CopyMode.HARD_LINK}. '
                        f'Warning: {CopyMode.HARD_LINK} and {CopyMode.SOFT_LINK} modes are not available in '
                        f'the following cases: '
                        f'(1) on some file systems, notably fat32 '
                        f'(2) if <dir1> and <dir2> are not on the same drive '
                        f'(3) for zipped files of dir1. '
                        f'In these cases, only {CopyMode.COPY} (corresponding to an extraction in case of zipped files) '
                        f'can be used but it can be very long, so always prefer default mode when possible '
                        f'(for example, organize first on the same drive, and then copy/paste the organized folder '
                        f'when you are satisfied.)')
    p.add_argument('-c', '--collision-policy', metavar='<policy>', type=CollisionPolicy.argparse,
                   choices=list(CollisionPolicy), default=str(CollisionPolicy.RENAME_PARENT),
                   help=f'{list(CollisionPolicy)} - Default: {CollisionPolicy.RENAME_PARENT}. '
                        f'For {CollisionPolicy.RENAME} and {CollisionPolicy.RENAME_PARENT}, "~i" is added to the '
                        f'file/directory name, where i is a number incremented for each collision.')
    p.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                   help='Show this help message and exit.')

    p = sp_list.add_parser(CUSTOM_CMD, add_help=False, aliases=["c"], help='Execute a custom processor.')
    p.set_defaults(command=CUSTOM_CMD)
    p.add_argument('processor', type=str, help='Name of the processor to execute.')
    p.add_argument('args', nargs='*', metavar='arguments', type=str, help='Arguments of the custom processor.')
    p.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                   help='Show this help message and exit.')

    return parser

def start_ui(media_set1, media_set2):
    if Configuration.get().ui:
        from camerafile.processor.BatchGenerateThumbnails import BatchGenerateThumbnails
        api_instance = ManagementApi(media_set1, media_set2)
        app = api_instance.get_app()
        if Configuration.get().watch:
            server_thread = threading.Thread(target=start_management_server,args=(app,), daemon=True)
            server_thread.start()
        else:
            start_management_server(app)
        #BatchGenerateThumbnails(media_set1).execute()
        #BatchGenerateThumbnails(media_set2).execute()


def execute(args):
    from camerafile.core.MediaSet import MediaSet
    from camerafile.processor.BatchComputeCm import BatchComputeCm
    from camerafile.processor.BatchReadInternalMd import BatchReadInternalMd
    from camerafile.processor.CompareMediaSets import CompareMediaSets
    from camerafile.processor.SearchForDuplicates import SearchForDuplicates
    from camerafile.core.MediaDuplicateManager import MediaDuplicateManager

    if Configuration.get().get_command() == CUSTOM_CMD:
        import importlib
        processor_class = getattr(importlib.import_module("camerafile.processor." + args.processor), args.processor)
        processor_class(*tuple(args.args))
        return

    media_set1 = MediaSet.load_media_set(Configuration.get().get_dir1())
    media_set2 = None
    other_md_needed = ()
    if Configuration.get().get_dir2() is not None:
        media_set2 = MediaSet.load_media_set(Configuration.get().get_dir2(), Configuration.get().org_format)
        other_md_needed = media_set2.state.get_metadata_needed_by_format()

    BatchReadInternalMd(media_set1, other_md_needed).execute()
    BatchComputeCm(media_set1).execute()

    if media_set2:
        # Synchronize metadata from media_set1 to media_set2 before reading internal metadata
        media_set1.synchronize_metadata(media_set2)
        #MediaDuplicateManager.propagate_camera_model(media_set2)
        BatchReadInternalMd(media_set2, ()).execute()
        BatchComputeCm(media_set2).execute()

    if Configuration.get().get_command() == ANALYZE_CMD:
        SearchForDuplicates.execute(media_set1)

        if media_set2:
            SearchForDuplicates.execute(media_set2)
            CompareMediaSets.execute(media_set1, media_set2)

    if Configuration.get().get_command() == ORGANIZE_CMD:
        execute_organize(args, media_set1, media_set2)

    print("")
    save(media_set1, media_set2)
    start_ui(media_set1, media_set2)
    watch_if_required(media_set1, media_set2)


def watch_if_required(media_set1, media_set2):
    if Configuration.get().watch and media_set2.state.org_format is not None:
        watcher = Watcher(media_set1, media_set2)
        watcher.start()
        try:
            while True:
                watcher.join(60)
        finally:
            watcher.stop()
            watcher.join()


def save(media_set1, media_set2):
    media_set1.save_on_disk()
    if media_set2:
        media_set2.save_on_disk()


def execute_organize(args, media_set1, media_set2):
    if media_set2.state.org_format is None:
        print("\n!!!!!!!!!!!!!!!!!!!")
        print(f"Format is not already configured for {Configuration.get().get_dir2()}, you have to define it using -f option "
              f"or by defining ORG_FORMAT environment variable.")
        print('Example: -f "{date:%Y}/{date:%m[%B]}/{cm:Unknown}/{filename:x}"')
        print("!!!!!!!!!!!!!!!!!!!")
    else:
        from camerafile.processor.BatchComputeNecessarySignatures import BatchComputeNecessarySignaturesMultiProcess
        from camerafile.processor.BatchCopy import BatchCopy
        from camerafile.processor.BatchDelete import BatchDelete

        copy_mode = Configuration.get().copy_mode
        BatchComputeNecessarySignaturesMultiProcess(media_set1, media_set2).execute()
        BatchCopy(media_set1, media_set2, copy_mode).execute()
        #if Configuration.get().delete_in_target:
        #    BatchDelete(media_set1, media_set2).execute()

def start_management_server(app: FastAPI):
    uvicorn.run(app, host="0.0.0.0", port=5678)

def main():
    freeze_support()
    parser = create_main_args_parser()
    args = parser.parse_args()

    if COMMAND not in args and os.getenv("COMMAND") is None:
        parser.print_usage()
        print(os.linesep + "error: no commands supplied")
        sys.exit(1)

    from camerafile.core.Resource import Resource

    LOGGER.info("Starting Camera Files Manager - version %s - DpjL (pid: %s)", VERSION, current_process().pid)
    Resource.init()
    Configuration.get().init(args)
    execute(args)


if __name__ == '__main__':
    main()
