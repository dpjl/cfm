from reprint import output
import time

filenames = [
'File_1',
'SomeFileWithAVeryLongNameWhichMakeitToANewLineWhichMayInfluenceTheReprintModuleButActuallyNot.exe',
'File_3',
'File_4',
]

if __name__ == "__main__":
    with output(initial_len=2) as output_lines:
        for i in range(4):
            output_lines[0] = filenames[i]
            for progress in range(100):
                output_lines[1] = "[{done}{padding}] {percent}%".format(
                    done = "#" * int(progress/10),
                    padding = " " * (10 - int(progress/10)),
                    percent = progress
                    )
                time.sleep(0.02)