import logging
import shutil
from datetime import datetime

from camerafile.tools.ExifTool import ExifTool
from camerafile.core.OutputDirectory import OutputDirectory
from camerafile.core.Resource import Resource


def init_logging(base_path):
    output_directory = OutputDirectory(base_path)
    logging_handlers = Resource.logging_configuration["handlers"]
    info_file = logging_handlers["info_file_handler"]["filename"]
    error_file = logging_handlers["error_file_handler"]["filename"]
    logging_handlers["info_file_handler"]["filename"] = str(output_directory.path / info_file)
    logging_handlers["error_file_handler"]["filename"] = str(output_directory.path / error_file)
    logging.config.dictConfig(Resource.logging_configuration)

    ExifTool.init(stdout_file_path=output_directory.path / "exif-stdout.txt",
                  stderr_file_path=output_directory.path / "exif-stderr.txt")


def init_only_console_logging():
    Resource.logging_configuration["root"]["handlers"] = ["console"]
    logging.config.dictConfig(Resource.logging_configuration)


class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.status_line = None

    def write_title(self, mediaset, step_title):
        self.write_title_2(directory=str(mediaset.root_path), step_title=step_title)

    def write_title_2(self, directory, step_title):
        self.display_starting_line()
        print("█ [{dir}] > {title}]".format(dir=directory, title=step_title))
        self.logger.info("{dir}] > {title}".format(dir=directory, title=step_title))

    def info(self, log_content):
        print(datetime.now().strftime("[%H:%M:%S] "), end="")
        print(log_content)
        self.logger.info(log_content)

    def debug(self, log_content):
        # print(datetime.now().strftime("[%H:%M:%S] "), end="")
        # print(log_content)
        self.logger.debug(log_content)

    def info_indent(self, log_content, prof=1):
        print(datetime.now().strftime("[%H:%M:%S] "), end="")
        print(self.get_indented_message(log_content, prof))
        self.logger.info(log_content)

    def get_indented_message(self, message, prof=1):
        result = ""
        if prof != 0:
            for i in range(prof - 1):
                result += "     "
            result += "|___ "
        return result + message

    def start(self, log_content, update_freq=1, prof=0):
        self.status_line = StatusLine(self.get_indented_message(log_content, prof), update_freq)

    def update(self, **args):
        self.status_line.update(**args)

    def end(self, **args):
        self.status_line.end(**args)

    def display_starting_line(self):
        # console_width = shutil.get_terminal_size((80, 20)).columns - 1
        # line = '{text:{fill}{align}{width}}'.format(
        #    text='', fill='-', align='<', width=console_width,
        # )
        print("")

    def display_ending_line(self):
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        line = '{text:{fill}{align}{width}}\n'.format(
            text='', fill='-', align='<', width=console_width,
        )
        print(line)


class StatusLine:
    def __init__(self, message, update_freq=1):
        self.console_width = shutil.get_terminal_size((80, 20)).columns - 1
        self.starting_time = datetime.now().strftime('%H:%M:%S')
        self.message = message
        self.nb_update = 0
        self.update_freq = update_freq

    def update(self, **args):
        if self.nb_update % self.update_freq == 0:
            line = "\r[" + self.starting_time + "] " + self.message.format(**args)
            print(line[0:self.console_width], end='')
        self.nb_update += 1

    def end(self, **args):
        line = "\r[" + self.starting_time + "] " + self.message.format(**args)
        print(line[0:self.console_width])