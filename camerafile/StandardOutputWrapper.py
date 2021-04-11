import builtins
import logging
import os
from io import StringIO

import sys

SPACE = ' '


class StdWrapper(object):

    def __init__(self, std_stream, console_width=0):
        self.console_width = console_width
        self.stream = std_stream
        self.default_print = builtins.print

    def wrapped_print(self, *args, sep=' ', end='\n', file=None):
        if file is None:
            self.write(sep.join(args) + end)
        else:
            self.default_print(*args, sep=sep, end=end, file=file)

    def write(self, data):
        if data != os.linesep and data != "\n":
            self.fill_line(SPACE)
        self.stream.write("\r" + data)
        self.stream.flush()

    def writelines(self, datas):
        for data in datas:
            self.write(data)
        #self.fill_line(SPACE)
        #self.stream.writelines(datas)
        #self.stream.flush()

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

    def fill_line(self, char, end='', content=''):
        blanks = '\r{text:{fill}{align}{width}}\r'.format(
            text=content,
            fill=char,
            align='<',
            width=self.console_width,
        )
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
