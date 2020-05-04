import logging
import os
import shutil
import threading
import time
import sys

REFRESH_DELAY = 0.1
SPACE = ' '
BAR_CHAR = '#'
DEFIL_CHARACTERS = ["/", "-", "\\", "|"]


class StdWrapper(object):

    def __init__(self, std_stream, console_width):
        self.console_width = console_width
        self.stream = std_stream

    def write(self, data):
        if data != os.linesep and data != "\n":
            self.fill_line(SPACE)
        self.stream.write(data)
        self.stream.flush()

    def writelines(self, datas):
        self.fill_line(SPACE)
        self.stream.writelines(datas)
        self.stream.flush()

    def flush(self):
        self.stream.flush()

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

    def unwrap(self):
        sys.stdout = self.stream
        self.unwrap_log()


class StderrWrapper(StdWrapper):

    def __init__(self, console_width):
        super(StderrWrapper, self).__init__(sys.stderr, console_width)

    def wrap(self):
        sys.stderr = self
        self.wrap_log()

    def unwrap(self):
        sys.stderr = self.stream
        self.unwrap_log()


class ConsoleProgressBar:

    def __init__(self, max_count, title="", clear_screen=False):

        self.console_width = shutil.get_terminal_size((80, 20)).columns - 1
        self.title = title
        self.defil_position = 0
        self.position = 0
        self.max = max_count
        self.run = True
        self.start_time = time.time()
        self.remaining_time = ""
        self.clear_screen = clear_screen
        self.lock_increment = threading.Lock()
        self.stdout = StdoutWrapper(self.console_width)
        self.stderr = StderrWrapper(self.console_width)
        self.stdout.wrap()
        self.stderr.wrap()

        thread = threading.Thread(None, self.auto_refresh, None, [], {})
        thread.start()

    def compute_remaining_time(self):

        if self.position > 0:
            current_time = time.time()
            rem_time = ((current_time - self.start_time) / self.position) * (self.max - self.position)

            hour = int(rem_time / 3600)
            minutes = int((rem_time - hour * 3600) / 60)
            seconds = int((rem_time - hour * 3600) % 60)

            if hour != 0:
                self.remaining_time = "{h: >4}h".format(h=hour)
            elif minutes != "00":
                self.remaining_time = "{m: >4}m".format(m=minutes)
            else:
                self.remaining_time = "{s: >4}s".format(s=seconds)

    def increment(self):
        with self.lock_increment:
            self.position += 1
            self.compute_remaining_time()

            if self.position >= self.max:
                self.run = False
                time.sleep(2 * REFRESH_DELAY)

    def auto_refresh(self):
        while self.run:
            time.sleep(REFRESH_DELAY)
            self.refresh()

        self.refresh()

        if self.clear_screen:
            print("")

        self.stdout.unwrap()
        self.stderr.unwrap()

        if not self.clear_screen:
            print("")

    def stop(self):
        self.run = False
        time.sleep(2 * REFRESH_DELAY)

    def refresh(self):

        self.console_width = shutil.get_terminal_size((80, 20)).columns - 1
        self.stdout.console_width = self.console_width
        self.stderr.console_width = self.console_width

        if self.max == 0:
            return

        self.defil_position += 1
        position_100 = self.position * 100 / self.max

        before = "{title} [".format(
            title=self.title)

        after = "] {position:{position_len}}/{max} | {percent: >3}% {remaining: >4} ".format(
            position=self.position, position_len=len(str(self.max)),
            max=self.max,
            percent=str(int(position_100))[:3],
            remaining=self.remaining_time[:5])

        progress_bar_size = self.console_width - len(before) - len(after)
        position_progress_bar = int(position_100 * progress_bar_size / 100) + 1
        present_size = position_progress_bar - 1
        future_size = progress_bar_size - present_size - 1
        defil_char = DEFIL_CHARACTERS[self.defil_position % len(DEFIL_CHARACTERS)]
        if present_size == progress_bar_size:
            defil_char = ''
            future_size = 0
        bar = "{present:{c1}<{l1}}{now}{future:{c3}<{l3}}".format(
            present='', c1=BAR_CHAR, l1=present_size,
            now=defil_char,
            future='', c3=SPACE, l3=future_size)

        sys.stdout.write("{bef}{b}{af}".format(bef=before, b=bar, af=after))


if __name__ == "__main__":

    progress_bar = ConsoleProgressBar(10)

    for i in range(1, 11):
        time.sleep(1)
        progress_bar.increment()
