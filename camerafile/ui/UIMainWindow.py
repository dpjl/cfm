from PyQt5 import QtCore, QtWidgets


class UIMainWindow(object):
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

        QtCore.QMetaObject.connectSlotsByName(cfm_window)

    def retranslateUi(self, cfm_window):
        _translate = QtCore.QCoreApplication.translate
        cfm_window.setWindowTitle(_translate("cfm_window", "Camera Files Manager"))
        self.menuFile.setTitle(_translate("cfm_window", "File"))
        self.actionOpen.setText(_translate("cfm_window", "Open"))
