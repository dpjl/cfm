# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'cfm-window.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_cfm_window(object):
    def setupUi(self, cfm_window):
        cfm_window.setObjectName("cfm_window")
        cfm_window.resize(850, 497)
        self.centralwidget = QtWidgets.QWidget(cfm_window)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.media_set_tab = QtWidgets.QTabWidget(self.centralwidget)
        self.media_set_tab.setObjectName("media_set_tab")
        self.media_set = QtWidgets.QWidget()
        self.media_set.setObjectName("media_set")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.media_set)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.splitter = QtWidgets.QSplitter(self.media_set)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tabWidget = QtWidgets.QTabWidget(self.splitter)
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setStyleStrategy(QtGui.QFont.PreferDefault)
        self.tabWidget.setFont(font)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.West)
        self.tabWidget.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.tabWidget.setElideMode(QtCore.Qt.ElideNone)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setMovable(False)
        self.tabWidget.setObjectName("tabWidget")
        self.duplicates = QtWidgets.QWidget()
        self.duplicates.setObjectName("duplicates")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.duplicates)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.splitter_2 = QtWidgets.QSplitter(self.duplicates)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.duplicate_type_list = QtWidgets.QListWidget(self.splitter_2)
        self.duplicate_type_list.setMaximumSize(QtCore.QSize(200, 16777215))
        self.duplicate_type_list.setObjectName("duplicate_type_list")
        self.scrollbar_thumbnails = QtWidgets.QScrollArea(self.splitter_2)
        self.scrollbar_thumbnails.setStyleSheet("")
        self.scrollbar_thumbnails.setWidgetResizable(True)
        self.scrollbar_thumbnails.setObjectName("scrollbar_thumbnails")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 552, 366))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.label.setMouseTracking(True)
        self.label.setFocusPolicy(QtCore.Qt.WheelFocus)
        self.label.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.label.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.label.setFrameShadow(QtWidgets.QFrame.Plain)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.scrollbar_thumbnails.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout.addWidget(self.splitter_2)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("C:/Users/g555329/Desktop/hopstarter-soft-scraps-button-add.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.tabWidget.addTab(self.duplicates, icon, "")
        self.add = QtWidgets.QWidget()
        self.add.setObjectName("add")
        self.tabWidget.addTab(self.add, "")
        self.verticalLayout_3.addWidget(self.splitter)
        self.media_set_tab.addTab(self.media_set, "")
        self.verticalLayout.addWidget(self.media_set_tab)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        cfm_window.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(cfm_window)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 850, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        cfm_window.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(cfm_window)
        self.statusbar.setObjectName("statusbar")
        cfm_window.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QAction(cfm_window)
        self.actionOpen.setObjectName("actionOpen")
        self.menuFile.addAction(self.actionOpen)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(cfm_window)
        self.media_set_tab.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(cfm_window)

    def retranslateUi(self, cfm_window):
        _translate = QtCore.QCoreApplication.translate
        cfm_window.setWindowTitle(_translate("cfm_window", "Camera Files Manager"))
        self.label.setText(_translate("cfm_window", "TextLabel"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.duplicates), _translate("cfm_window", "Duplicates"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.add), _translate("cfm_window", "Add"))
        self.media_set_tab.setTabText(self.media_set_tab.indexOf(self.media_set), _translate("cfm_window", "Media set"))
        self.menuFile.setTitle(_translate("cfm_window", "File"))
        self.actionOpen.setText(_translate("cfm_window", "Open"))
import resources_rc