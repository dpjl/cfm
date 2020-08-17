# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'load_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_load_dialog(object):
    def setupUi(self, load_dialog):
        load_dialog.setObjectName("load_dialog")
        load_dialog.resize(400, 172)
        self.verticalLayout = QtWidgets.QVBoxLayout(load_dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(load_dialog)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.num_files = QtWidgets.QLabel(self.groupBox)
        self.num_files.setMaximumSize(QtCore.QSize(50, 16777215))
        self.num_files.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.num_files.setObjectName("num_files")
        self.horizontalLayout.addWidget(self.num_files)
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(load_dialog)
        self.groupBox_2.setObjectName("groupBox_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.progressBar = QtWidgets.QProgressBar(self.groupBox_2)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.horizontalLayout_2.addWidget(self.progressBar)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(load_dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Abort)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(load_dialog)
        self.buttonBox.accepted.connect(load_dialog.accept)
        self.buttonBox.rejected.connect(load_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(load_dialog)

    def retranslateUi(self, load_dialog):
        _translate = QtCore.QCoreApplication.translate
        load_dialog.setWindowTitle(_translate("load_dialog", "Dialog"))
        self.groupBox.setTitle(_translate("load_dialog", "1. Gets all files: "))
        self.num_files.setText(_translate("load_dialog", "0"))
        self.label.setText(_translate("load_dialog", "files discovered"))
        self.groupBox_2.setTitle(_translate("load_dialog", "2. Computes/loads hashes and thumbnails"))
