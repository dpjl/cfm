import builtins
import logging
import os
import sys
import threading
from typing import List

SPACE = ' '
CURSOR_UP = "\x1b[1A"
CURSOR_LEFT = "\r"

threadLock = threading.Lock()


class StdWrapper(object):

    def __init__(self, std_stream, console_width=0):
        self.console_width = console_width
        self.stream = std_stream
        self.default_print = builtins.print
        self.current_tmp_lines = 0

    def wrapped_print(self, *args, sep=' ', end='\n', file=None):
        if file is None:
            self.write(sep.join(args) + end)
        else:
            self.default_print(*args, sep=sep, end=end, file=file)

    def clean_lines(self):
        if self.current_tmp_lines == 0:
            return
        else:
            clean_string = self.current_tmp_lines * '\r{text:{fill}{align}{width}}\n'.format(
                text='',
                fill=SPACE,
                align='<',
                width=self.console_width,
            ) + self.current_tmp_lines * CURSOR_UP + CURSOR_LEFT
            self.stream.write(clean_string)
            self.stream.flush()

    def write_with_blanks(self, data, end=''):
        self.stream.write(CURSOR_LEFT + self.with_blanks(SPACE, data) + end)
        self.stream.flush()

    def update_screen_size(self):
        windows_width = os.get_terminal_size().columns - 1
        if self.console_width != windows_width:
            self.console_width = windows_width

    def writelines_with_lock(self, datas: List[str], tmp=False):
        threadLock.acquire()
        if tmp:
            self.update_screen_size()
            for data in datas:
                self.write_with_blanks(data[0:self.console_width], end="\n")
            self.stream.write(len(datas) * CURSOR_UP)
            self.current_tmp_lines = len(datas)
        else:
            self.write_with_blanks("".join(datas))
            self.current_tmp_lines = 0

        threadLock.release()

    def write(self, data):
        # if data != os.linesep and data != "\n":
        #    self.fill_line(SPACE)
        self.writelines_with_lock([CURSOR_LEFT + data])

    def writelines(self, datas):
        for data in datas:
            self.write(data)
        # self.fill_line(SPACE)
        # self.stream.writelines(datas)
        # self.stream.flush()

    def flush(self):
        self.stream.flush()

    def wrap_print(self):
        builtins.print = self.wrapped_print

    def unwrap_print(self):
        builtins.print = self.default_print

    def wrap_log(self):
        for handler in logging.root.handlers:
            if handler.stream == self.stream:
                handler.stream = self

    def unwrap_log(self):
        for handler in logging.root.handlers:
            if handler.stream == self:
                handler.stream = self.stream

    def with_blanks(self, char, content=''):
        return '{text:{fill}{align}{width}}'.format(
            text=content,
            fill=char,
            align='<',
            width=self.console_width,
        )

    def fill_line(self, char, end='', content=''):
        blanks = self.with_blanks(char, content)
        self.stream.write(blanks + end)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class StdoutWrapper(StdWrapper):

    def __init__(self, console_width):
        super(StdoutWrapper, self).__init__(sys.stdout, console_width)

    def wrap(self):
        sys.stdout = self
        self.wrap_log()
        self.wrap_print()

    def unwrap(self):
        sys.stdout = self.stream
        self.unwrap_log()
        self.unwrap_print()


class StderrWrapper(StdWrapper):

    def __init__(self, console_width):
        super(StderrWrapper, self).__init__(sys.stderr, console_width)

    def wrap(self):
        sys.stderr = self
        self.wrap_log()

    def unwrap(self):
        sys.stderr = self.stream
        self.unwrap_log()


class StdRecorder(StdWrapper):
    str_stream = ""

    def __init__(self, std_stream):
        super(StdWrapper, self).__init__(self, std_stream)
        StdRecorder.str_stream = ""

    def write(self, data):
        StdRecorder.str_stream += data

    def writelines(self, datas):
        for data in datas:
            StdRecorder.str_stream += data

    def flush(self):
        pass

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class StdoutRecorder(StdRecorder):

    def __init__(self):
        super(StdRecorder, self).__init__(sys.stdout)
        StdRecorder.str_stream = ""

    def start(self):
        sys.stdout = self
        self.wrap_log()
        return self

    def stop(self):
        sys.stdout = self.stream
        self.unwrap_log()
        return StdRecorder.str_stream


class StdErrRecorder(StdRecorder):

    def __init__(self):
        super(StdRecorder, self).__init__(sys.stderr)

    def start(self):
        sys.stderr = self
        self.wrap_log()

    def stop(self):
        sys.stderr = self.stream
        self.unwrap_log()
        return StdRecorder.str_stream
