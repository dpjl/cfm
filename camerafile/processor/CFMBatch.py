import logging
import os

from camerafile.core.Configuration import Configuration
from camerafile.core.Resource import Resource
from camerafile.mdtools.ExifToolReader import ExifTool
from camerafile.processor.BatchTool import TaskWithProgression

LOGGER = logging.getLogger(__name__)


class CFMBatch(TaskWithProgression):

    def __init__(self, batch_title="", nb_sub_process=None, stderr_file=None, stdout_file=None):
        if nb_sub_process is None:
            nb_sub_process = Configuration.get().nb_sub_process
        TaskWithProgression.__init__(self, batch_title, nb_sub_process,
                                     on_worker_start=CFMBatch.on_sub_cfm_start,
                                     on_worker_end=CFMBatch.on_sub_cfm_end,
                                     stderr_file=stderr_file,
                                     stdout_file=stdout_file)

    @staticmethod
    def init_sub_cfm():
        if not Configuration.get().initialized:
            from camerafile.cfm import create_main_args_parser
            parser = create_main_args_parser()
            args = parser.parse_args()
            Resource.init()
            Configuration.get().init(args)

    @staticmethod
    def on_sub_cfm_start():
        CFMBatch.init_sub_cfm()
        LOGGER.debug("Start sub-process : " + str(os.getpid()))

    @staticmethod
    def on_sub_cfm_end():
        LOGGER.debug("Stop sub-process : " + str(os.getpid()))
        ExifTool.stop()
