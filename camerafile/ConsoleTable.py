import shutil


class ConsoleTable:

    def __init__(self):
        console_width = shutil.get_terminal_size((80, 20)).columns - 1
        self.width = max(60, int(console_width / 2))

    def print_bar(self, char, *args):
        number_of_columns = len(args)
        for _ in args:
            bar = '+{col:{fill}^{col_width}}'.format(
                col='', fill=char, col_width=str(int(self.width / number_of_columns)))
            print(bar, end='')
        print("|")

    def print_line_content(self, *args):
        number_of_columns = len(args)
        for val in args:
            line = '|{col: ^{col_width}}'.format(
                col=val[0:self.width - 2], col_width=str(int(self.width / number_of_columns)))
            print(line, end='')
        print("|")

    def print_line(self, *args):
        self.print_line_content(*args)
        self.print_bar('-', *args)

    def print_multi_line(self, *args):
        max_line = max(map(len, args))
        for i in range(max_line):
            line_args = ()
            for arg in args:
                if len(arg) > i:
                    line_args += (arg[i],)
                else:
                    line_args += ("", )
            self.print_line_content(*line_args)
        self.print_bar('-', *line_args)

    def print_1_column(self, col_value):
        line = '|{col: ^{col_width}}|'.format(
            col=col_value[0:self.width - 2], col_width=self.width)
        print(line)

    def print_header(self, *args):
        self.print_bar('=', *args)
        self.print_line_content(*args)
        self.print_bar('=', *args)
