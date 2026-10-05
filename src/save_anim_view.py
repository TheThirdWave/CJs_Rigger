import json
import shiboken2
import shiboken6

import maya.OpenMayaUI as OpenMayaUI

#from PySide2 import QtGui
#from PySide2 import QtCore
#from PySide2 import QtWidgets

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from . import constants
from .crig_maya import maya_utils_controller

def get_maya_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)

class ControlAnimSaveLoad(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self.__class__.instance = self

        self.maya_main_window = get_maya_window()
        self.setParent(self.maya_main_window)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName("Save Out Anim Window")

        self.utils = maya_utils_controller.UtilsController()

        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_layout = QtWidgets.QVBoxLayout()

        self.populateOptions()

        self.setLayout(self.main_layout)
        self.main_widget.setLayout(self.main_layout)

    def populateOptions(self):

        self.file_label = QtWidgets.QLabel('file:')
        self.file_pathbox = QtWidgets.QLineEdit()
        self.file_button = QtWidgets.QPushButton('select file')
        self.file_button.clicked.connect(self.getFilePath)
        self.file_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.file_layout)
        self.file_layout.addWidget(self.file_label)
        self.file_layout.addWidget(self.file_pathbox)
        self.file_layout.addWidget(self.file_button)

        self.load_button = QtWidgets.QPushButton('Load Anim')
        self.load_button.clicked.connect(self.loadButtonPressed)
        self.save_button = QtWidgets.QPushButton('Save Anim')
        self.save_button.clicked.connect(self.saveButtonPressed)
        self.button_layout = QtWidgets.QHBoxLayout()

        self.main_layout.addLayout(self.button_layout)
        self.button_layout.addWidget(self.load_button)
        self.button_layout.addWidget(self.save_button)


    def getFilePath(self):
        filename, filter = QtWidgets.QFileDialog.getOpenFileName(self,
        'Select Template',
        constants.ANIM_PATH,
        'JSON files (*.json)'
        )
        if filename:
            self.file_pathbox.setText(filename)

    def loadButtonPressed(self):
        anim_data = self.loadJSON(self.file_pathbox.text())
        self.utils.loadAnim(anim_data)

    def saveButtonPressed(self):
        filename, filter = QtWidgets.QFileDialog.getSaveFileName(self,
        'Select Bind Data File',
        constants.ANIM_PATH,
        'JSON files (*.json)'
        )
        if filename:
            self.file_pathbox.setText(filename)
            anim_data = self.utils.getAnimData()
            self.saveJSON(self.file_pathbox.text(), anim_data)

    def loadJSON(self, path):
        with open(path, 'r') as file:
            positions = json.load(file)
        return positions
    
    def saveJSON(self, path, data):
        with open(path, 'w') as file:
            json.dump(data, file, indent = 4)

def run():
        win = ControlAnimSaveLoad()
        win.setWindowTitle("save/load anim")
        win.resize(500, 60)
        win.show()
        return win