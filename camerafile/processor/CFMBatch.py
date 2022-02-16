import os

from camerafile.core.BatchTool import TaskWithProgression
from camerafile.core.Configuration import Configuration
from camerafile.core.Logging import init_only_console_logging, Logger
from camerafile.core.Resource import Resource
from camerafile.tools.ExifTool import ExifTool

LOGGER = Logger(__name__)


class CFMBatch(TaskWithProgression):

    def __init__(self, batch_title="", nb_sub_process=None):
        if nb_sub_process is None:
            nb_sub_process = Configuration.get().nb_sub_process
        TaskWithProgression.__init__(self, batch_title, nb_sub_process,
                                     CFMBatch.on_sub_cfm_start, CFMBatch.on_sub_cfm_end)

    @staticmethod
    def init_sub_cfm():
        if not Configuration.get().initialized:
            from camerafile.cfm import create_main_args_parser
            parser = create_main_args_parser()
            args = parser.parse_args()
            Resource.init()
            init_only_console_logging()
            Configuration.get().init(args)

    @staticmethod
    def on_sub_cfm_start():
        CFMBatch.init_sub_cfm()
        LOGGER.debug("Start sub-process : " + str(os.getpid()))

    @staticmethod
    def on_sub_cfm_end():
        ExifTool.stop()
        LOGGER.debug("Stop sub-process : " + str(os.getpid()))
