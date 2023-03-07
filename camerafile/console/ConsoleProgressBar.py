import datetime
import os
import shutil
import threading

import humanize
import sys
import time

from camerafile.console.StandardOutputWrapper import StdoutWrapper, StderrWrapper
from camerafile.core.Configuration import Configuration

REFRESH_DELAY = 0.1
SPACE = ' '
BAR_CHAR = '#'
DEFIL_CHARACTERS = ["/", "-", "\\", "|"]


class ConsoleProgressBar:

    def __init__(self, max_count, title="", clear_screen=False):
        self.activated = Configuration.get().progress
        try:
            self.console_width = os.get_terminal_size().columns - 1
        except OSError:
            self.console_width = shutil.get_terminal_size((80, 50))
        self.title = title
        self.defil_position = 0
        self.position = 0
        self.max = max_count
        self.run = True
        self.start_time = time.time()
        self.remaining_time = ""
        self.processing_time = ""
        self.item_text = None
        self.clear_screen = clear_screen
        self.lock_increment = threading.Lock()
        self.details = {}
        self.status = []

        if self.activated:
            self.stdout = StdoutWrapper(self.console_width)
            self.stderr = StderrWrapper(self.console_width)
            self.stdout.wrap()
            self.stderr.wrap()
            self.thread = threading.Thread(None, self.auto_refresh, None, [], {})
            self.thread.start()

    @staticmethod
    def __get_duration_string(duration):
        result = ""
        hours = int(duration / 3600)
        minutes = int((duration - hours * 3600) / 60)
        seconds = int((duration - hours * 3600) % 60)

        if hours != 0:
            result += "{num}h".format(num=hours)
        if minutes != 0:
            result += "{num}m".format(num=minutes)
        if seconds != 0 or result == "":
            result += "{num}s".format(num=seconds)
        return result

    def __compute_remaining_time(self):
        if self.position > 0:
            current_time = time.time()
            rem_time = ((current_time - self.start_time) / self.position) * (self.max - self.position)
            # self.remaining_time = self.get_duration_string(rem_time)
            self.remaining_time = humanize.naturaldelta(datetime.timedelta(seconds=rem_time))

    def set_detail(self, key, text):
        with self.lock_increment:
            self.details[key] = text

    def set_status(self, status):
        with self.lock_increment:
            self.status = status

    def set_item_text(self, item_text):
        with self.lock_increment:
            self.item_text = item_text

    def increment(self):
        with self.lock_increment:
            self.position += 1
            self.__compute_remaining_time()

            if self.position >= self.max:
                self.run = False
                time.sleep(2 * REFRESH_DELAY)

    def auto_refresh(self):
        while self.run:
            time.sleep(REFRESH_DELAY)
            self.refresh()

        self.refresh()

        self.stdout.clean_lines()
        self.details = {}
        # self.status = None
        self.refresh()
        if self.clear_screen:
            pass
            # self.stdout.writelines_tmp(self.stdout.blanks(SPACE) * 4)
            # print("\r", end='')

        self.stdout.unwrap()
        self.stderr.unwrap()

        if not self.clear_screen:
            print("")
            for _ in self.status:
                print("")

    def stop(self):
        self.run = False
        self.processing_time = self.__get_duration_string(time.time() - self.start_time)
        if self.activated:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                print("Warning: ConsoleProgressBar.thread could not be stopped.")

    def cut_to_screen_size(self, content, other_content_len=0):
        line_size = len(content) + other_content_len
        if line_size > self.console_width:
            decal = line_size - self.console_width + 4
            return "..." + content[decal:]
        else:
            return content

    def refresh(self):
        self.console_width = self.stdout.console_width

        if self.max == 0:
            return

        self.defil_position += 1
        position_100 = self.position * 100 / self.max

        if self.item_text is None:

            before_bar = "{title}|".format(title=self.title)

            after_bar = "| {position:{position_len}}/{max} | {percent: >3}% | ~ {remaining}".format(
                position=self.position, position_len=len(str(self.max)),
                max=self.max,
                percent=str(int(position_100))[:3],
                remaining=self.remaining_time)

            # progress_bar_size = self.console_width - len(before_bar) - len(after_bar)
            progress_bar_size = 32
            current_position_progress_bar = int(position_100 * progress_bar_size / 100) + 1
            past_size = current_position_progress_bar - 1
            future_size = progress_bar_size - past_size - 1
            defil_char = DEFIL_CHARACTERS[self.defil_position % len(DEFIL_CHARACTERS)]

            if past_size == progress_bar_size:
                defil_char = ''
                future_size = 0

            bar = "{past:{c1}<{l1}}{now}{future:{c3}<{l3}}".format(
                past='', c1=BAR_CHAR, l1=past_size,
                now=defil_char,
                future='', c3=SPACE, l3=future_size)

            line = "{before}{progress_bar}{after}".format(before=before_bar, progress_bar=bar, after=after_bar)
            lines = []
            if self.status:
                lines += self.status
            for key in self.details.keys():
                start_of_line = "[" + str(key) + "] "
                lines.append(start_of_line + self.cut_to_screen_size(self.details[key], len(start_of_line)))
            lines.append(line[0:self.console_width])
            self.stdout.writelines_with_lock(lines, tmp=True)
        else:
            stats = "{title} | {position:{position_len}}/{max} | {percent: >3}% {remaining} - ".format(
                title=self.title,
                position=self.position, position_len=len(str(self.max)),
                max=self.max,
                percent=str(int(position_100))[:3],
                remaining=self.remaining_time[:5])
            line_size = len(stats) + len(self.item_text)
            decal = 0
            if line_size > self.console_width:
                decal = line_size - self.console_width
            line = stats + "{item}".format(item=self.item_text[decal:])
            sys.stdout.write(line[0:self.console_width])


if __name__ == "__main__":

    progress_bar = ConsoleProgressBar(10)

    for i in range(1, 11):
        time.sleep(1)
        progress_bar.increment()
