from functools import partial

from PyQt5 import QtWidgets, QtCore, QtGui, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QListWidgetItem

from camerafile.MediaSet import MediaSet
from camerafile.Constants import SIGNATURE
from camerafile.ui.UIFlowLayout import FlowLayout
from camerafile.ui.Worker import Worker
from camerafile.ui.load_dialog import Ui_load_dialog


class UIMediaSetTab(QtWidgets.QWidget):

    def __init__(self, name, dir_path, thread_pool):
        super().__init__()

        self.thread_pool = thread_pool
        self.dir_path = dir_path
        self.label_thumbnails = []
        self.label_dict = {}
        self.current_n_copied = None
        self.position = 0
        self.current_groups = []
        self.current_thumbnail_list = []
        self.group_image_list = {}
        self.layout_list = {}
        self.media_set = None
        self.duplicates_result = None

        self.dialog_window = QtWidgets.QDialog()
        self.dialog_window.setModal(True)
        self.load_dialog = Ui_load_dialog()
        self.load_dialog.setupUi(self.dialog_window)

        self.setObjectName(name)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_3.setObjectName("verticalLayout_3")

        self.splitter_x = QtWidgets.QSplitter(self)
        self.splitter_x.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_x.setObjectName("splitter_x")

        self.sub_tabs = QtWidgets.QTabWidget(self.splitter_x)
        self.sub_tabs.setTabPosition(QtWidgets.QTabWidget.West)
        self.sub_tabs.setObjectName("media_set_sub_tabs")

        self.duplicates = QtWidgets.QWidget()
        self.duplicates.setObjectName("duplicates_tab")

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.duplicates)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.splitter_list_thumbnails = QtWidgets.QSplitter(self.duplicates)
        self.splitter_list_thumbnails.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_list_thumbnails.setObjectName("splitter")

        self.n_copied_list = QtWidgets.QListWidget(self.splitter_list_thumbnails)
        self.n_copied_list.setMaximumSize(QtCore.QSize(200, 16777215))
        self.n_copied_list.setObjectName("n_copied_list")

        self.thumbnails_scroll_area = QtWidgets.QScrollArea(self.splitter_list_thumbnails)
        self.thumbnails_scroll_area.setWidgetResizable(True)
        self.thumbnails_scroll_area.setObjectName("thumbnails_scroll_area")

        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 552, 366))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.images_area = QWidget()
        self.images_area_layout = QVBoxLayout()
        self.images_area_layout.addStretch()
        self.images_area.setLayout(self.images_area_layout)

        self.thumbnails_scroll_area.setWidget(self.scrollAreaWidgetContents)
        self.thumbnails_scroll_area.setWidget(self.images_area)
        self.horizontalLayout.addWidget(self.splitter_list_thumbnails)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("C:/Users/g555329/Desktop/hopstarter-soft-scraps-button-add.ico"),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.sub_tabs.addTab(self.duplicates, icon, "")
        self.verticalLayout_3.addWidget(self.splitter_x)

        self.sub_tabs.setCurrentIndex(0)

        self.n_copied_list.currentItemChanged.connect(self.display_thumbnails)
        self.thumbnails_scroll_area.verticalScrollBar().valueChanged.connect(self.thumbnails_scrolled)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.duplicates), _translate("cfm_window", "Duplicates"))

    def load(self):
        self.execute(
            self.find_duplicates,
            self.start_find_duplicates,
            self.end_find_duplicates,
            self.progress_load_media_set,
            self.progress_compute_signatures)

    def execute(self, function, function_start, function_end, function_num, function_progress):
        worker = Worker(function)
        worker.signals.start.connect(function_start)
        worker.signals.finished.connect(function_end)
        worker.signals.progress.connect(function_progress)
        worker.signals.num.connect(function_num)
        self.thread_pool.start(worker)

    def create_label_thumbnail(self, media_file):
        # ça change quoi de mettre un parent au label ??
        label = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(media_file.metadata.get_thumbnail())
        label.setPixmap(pixmap)
        label.resize(pixmap.width(), pixmap.height())
        label.setToolTip(media_file.path + '\n' + media_file.get_signature())
        label.focusInEvent = partial(self.thum_on_focus, label)
        label.focusOutEvent = partial(self.thum_out_focus, label)
        label.setFocusPolicy(QtCore.Qt.WheelFocus)
        # print(media_file.path)
        # print(media_file.get_exact_signature())
        return label

    def thum_on_focus(self, label, mouseevent):
        label.setStyleSheet("border: 2px solid blue;")

    def thum_out_focus(self, label, mouseevent):
        label.setStyleSheet("")

    def display_thumbnails(self):

        if self.n_copied_list.currentItem() is not None:
            n_copied = int(self.n_copied_list.currentItem().data(QtCore.Qt.UserRole))
            if n_copied != self.current_n_copied:
                self.thumbnails_scroll_area.verticalScrollBar().setValue(0)
                self.current_n_copied = n_copied
                # self.current_thumbnail_list = [item for sublist in self.duplicates_result[n_copied].values()
                #                               for item in sublist]
                for old_group in self.current_groups:
                    old_group.hide()
                    self.images_area_layout.removeWidget(old_group)
                self.current_groups = []
                self.position = 0
            else:
                self.position += 100

            group = self.create_thumbnails_group(n_copied, self.position, self.position + 99)
            self.images_area_layout.addWidget(group)
            group.show()
            self.current_groups.append(group)

    def thumbnails_scrolled(self, value):
        if value == self.thumbnails_scroll_area.verticalScrollBar().maximum():
            self.display_thumbnails()

    def create_thumbnails_group(self, n_copied, start, end):
        layout = FlowLayout()
        group = QGroupBox()
        group.hide()
        group.setLayout(layout)

        if start % n_copied == 0:
            start = int(start / n_copied)
        else:
            start = int(start / n_copied) + 1

        end = int(end / n_copied)

        num_columns = int(n_copied ** 0.5)
        num_rows = int(num_columns + ((n_copied - num_columns ** 2) / num_columns))
        if (n_copied - num_columns ** 2) % num_columns != 0:
            num_rows += 1

        for dup_list in list(self.duplicates_result[n_copied].values())[start:end]:
            # ici un "flow" n'est pas nécessaire, à changer
            layout2 = FlowLayout()
            group2 = QGroupBox()
            group2.setLayout(layout2)
            width = 0
            height = 0
            for media_file in dup_list:
                label = self.create_label_thumbnail(media_file)
                width = label.width()
                height = label.height()
                layout2.addWidget(label)
            group2.setMinimumWidth(num_columns * (width + 15) + 20)
            group2.setMaximumHeight(num_rows * height + (num_rows - 1) * 15 + 50)
            layout.addWidget(group2)

        # for media_file in self.current_thumbnail_list[start:end]:
        #    label = self.create_label_thumbnail(media_file)
        #    layout.addWidget(label)
        return group

    def start_find_duplicates(self):
        self.dialog_window.show()

    def end_find_duplicates(self):
        self.dialog_window.hide()

    def progress_load_media_set(self, i):
        self.load_dialog.num_files.setText(str(i))

    def progress_compute_signatures(self, i):
        self.load_dialog.progressBar.setValue(i)

    def find_duplicates(self, progress_callback, num_callback):

        self.n_copied_list.clear()
        if self.media_set is None:
            self.media_set = MediaSet(self.dir_path, num_callback)

        total = len(self.media_set)
        i = 0
        for media_file in self.media_set:
            i += 1
            media_file.metadata.compute_value(SIGNATURE)
            progress_callback.emit(int((i * 100) / total))

        self.media_set.save_database()

        self.duplicates_result = self.media_set.analyze_duplicates_2()
        for element in sorted(self.duplicates_result):
            item = QListWidgetItem()
            item.setText("x%s (%s x %s = %s)" % (str(element), str(len(self.duplicates_result[element])), str(element),
                                                 str(len(self.duplicates_result[element]) * element)))
            item.setData(QtCore.Qt.UserRole, element)
            self.n_copied_list.addItem(item)
