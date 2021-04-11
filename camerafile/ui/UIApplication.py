import sys
from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool, QFile, QTextStream
from PyQt5.QtWidgets import QFileDialog

from camerafile.OutputDirectory import OutputDirectory
from camerafile.Resource import Resource
from camerafile.ui.UIMainWindow import UIMainWindow
from camerafile.ui.UIMediaSet import UIMediaSetTab
from camerafile.Logging import init_logging


class UIApplication:

    def __init__(self):
        self.ui = None
        self.thread_pool = None
        self.main_window = None

    def start_window(self):
        app = QtWidgets.QApplication(sys.argv)
        file = QFile("ui/style.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())

        self.main_window = QtWidgets.QMainWindow()
        self.ui = UIMainWindow()
        self.ui.setupUi(self.main_window)

        self.ui.actionOpen.triggered.connect(self.create_new_media_set_tab)
        self.main_window.show()
        self.thread_pool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.thread_pool.maxThreadCount())
        sys.exit(app.exec_())

    def create_new_media_set_tab(self):
        dir_path = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        new_tab = UIMediaSetTab(Path(dir_path).name, dir_path, self.thread_pool)
        self.ui.media_set_tab.addTab(new_tab, Path(dir_path).name)
        new_tab.load()


def main():
    OutputDirectory.init("../cfm-wip")
    Resource.init()
    init_logging()
    window = UIApplication()
    window.start_window()


if __name__ == '__main__':
    main()
