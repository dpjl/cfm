import argparse
import logging
import logging.config

from camerafile.AviMetaEdit import AviMetaEdit
from camerafile.CameraFilesProcessor import CameraFilesProcessor
from camerafile.ExifTool import ExifTool
from camerafile.OutputDirectory import OutputDirectory
from camerafile.Resource import Resource

LOGGER = logging.getLogger(__name__)


def init_logging():
    logging_handlers = Resource.logging_configuration["handlers"]
    info_file = logging_handlers["info_file_handler"]["filename"]
    error_file = logging_handlers["error_file_handler"]["filename"]
    logging_handlers["info_file_handler"]["filename"] = str(OutputDirectory.base_path / info_file)
    logging_handlers["error_file_handler"]["filename"] = str(OutputDirectory.base_path / error_file)
    logging.config.dictConfig(Resource.logging_configuration)

    ExifTool.init(stdout_file_path=OutputDirectory.base_path / "exif-stdout.txt",
                  stderr_file_path=OutputDirectory.base_path / "exif-stderr.txt")

    AviMetaEdit.init(stdout_file_path=OutputDirectory.base_path / "avimetaedit-stdout.txt",
                     stderr_file_path=OutputDirectory.base_path / "avimetaedit-stderr.txt")


def create_cm_find_sub_parser(sp_list):
    p = sp_list.add_parser('find', help='Search for camera models and try to recover missing ones')
    p.set_defaults(command=CameraFilesProcessor.find_cm)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_cm_reset_sub_parser(sp_list):
    p = sp_list.add_parser('reset', help='Remove all found camera models from cache and json metadata')
    p.set_defaults(command=CameraFilesProcessor.reset_cm)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_cm_sub_parser(sp_list):
    p = sp_list.add_parser('cm', help='Manage camera models')
    sp_list = p.add_subparsers()
    create_cm_find_sub_parser(sp_list)
    create_cm_reset_sub_parser(sp_list)


def create_sig_compute_sub_parser(sp_list):
    p = sp_list.add_parser('compute', help='Compute all signatures')
    p.set_defaults(command=CameraFilesProcessor.compute_signature)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_sig_reset_sub_parser(sp_list):
    p = sp_list.add_parser('reset', help='Remove all computed signatures from cache and json metadata')
    p.set_defaults(command=CameraFilesProcessor.reset_signature)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_sig_sub_parser(sp_list):
    p = sp_list.add_parser('sig', help='Manage signatures')
    sp_list = p.add_subparsers()
    create_sig_compute_sub_parser(sp_list)
    create_sig_reset_sub_parser(sp_list)


def create_media_cp_sub_parser(sp_list):
    p = sp_list.add_parser('cp', help='Copy media files from first directory to second directory')
    p.set_defaults(command=CameraFilesProcessor.copy_media)
    p.add_argument('--new', action='store_true', help='Copy only media files that are not already in second directory')
    p.add_argument('dir1', metavar='directory1[>create-json-metadata]', type=str, help='First media directory path')
    p.add_argument('dir2', metavar='directory2[>create-json-metadata]', type=str, help='Second media directory path')


def create_media_org_sub_parser(sp_list):
    p = sp_list.add_parser('org', help='Organize new copied media files of media directory')
    p.set_defaults(command=CameraFilesProcessor.organize_media)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Media directory path')


def create_media_cmp_sub_parser(sp_list):
    p = sp_list.add_parser('cmp', help='Compare files of two media directories, using their signatures')
    p.set_defaults(command=CameraFilesProcessor.cmp)
    p.add_argument('--new', action='store_true', help='Copy only media files that are not already in second directory')
    p.add_argument('dir1', metavar='directory1[>create-json-metadata]', type=str, help='First media directory path')
    p.add_argument('dir2', metavar='directory2[>create-json-metadata]', type=str, help='Second media directory path')


def create_media_dup_sub_parser(sp_list):
    p = sp_list.add_parser('dup', help='Find an display duplicated files of one directory')
    p.set_defaults(command=CameraFilesProcessor.dup)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_media_sub_parser(sp_list):
    p = sp_list.add_parser('media', help='Manage media files')
    sp_list = p.add_subparsers()
    create_media_cp_sub_parser(sp_list)
    create_media_org_sub_parser(sp_list)
    create_media_cmp_sub_parser(sp_list)
    create_media_dup_sub_parser(sp_list)


def create_jm_remove_sub_parser(sp_list):
    p = sp_list.add_parser('rm', help='Delete all json metadata files from a media directory')
    p.set_defaults(command=CameraFilesProcessor.delete_metadata)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_jm_sub_parser(sp_list):
    p = sp_list.add_parser('jm', help='Manage json metadata files')
    sp_list = p.add_subparsers()
    create_jm_remove_sub_parser(sp_list)


def create_cache_remove_parser(sp_list):
    p = sp_list.add_parser('rm', help='Delete all json metadata files from a media directory')
    p.set_defaults(command=CameraFilesProcessor.delete_metadata_cache)
    p.add_argument('dir1', metavar='directory[>create-json-metadata]', type=str, help='Root media directory')


def create_cache_sub_parser(sp_list):
    p = sp_list.add_parser('cache', help='Manage application cache')
    sp_list = p.add_subparsers()
    create_cache_remove_parser(sp_list)


def create_main_args_parser():
    parser = argparse.ArgumentParser(description='Performs various actions on media files')
    sp_list = parser.add_subparsers()
    create_media_sub_parser(sp_list)
    create_cm_sub_parser(sp_list)
    create_sig_sub_parser(sp_list)
    create_jm_sub_parser(sp_list)
    create_cache_sub_parser(sp_list)
    return parser


def main():
    OutputDirectory.init("cfm-wip")
    Resource.init()
    init_logging()
    parser = create_main_args_parser()
    args = parser.parse_args()

    params = ()
    for param_name in ['dir1', 'dir2']:
        if param_name in args:
            params += (args.__getattribute__(param_name),)
    args.command(*params)


if __name__ == '__main__':
    main()
