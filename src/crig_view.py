import logging
import os
import shiboken2

import maya.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from .crig_maya import maya_controller
from . crig_maya.modules import root_module

LOG = logging.getLogger(__name__)

def get_maya_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)

class ModularRigger(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self.__class__.instance = self

        self.controller = maya_controller.MayaController()
        self.controller.modules = [root_module.RootModule.loadFromDict({
            'name': 'root',
            'prefix': 'C',
            'children': [],
            'controls': {},
            'inputAttrs': [],
            'outputAttrs' : [{'longName': 'OUT_WORLD', 'type': 'matrix'}]
            })]

        self.maya_main_window = get_maya_window()
        self.setParent(self.maya_main_window)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName("CJ's Rigger")

        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)

        self.main_layout = QtWidgets.QVBoxLayout()

        # Setup widgets that load the template/position files.
        self.initFileWidgets()
        self.initMainPanelWidgets()
        self.initBuildButtonWidgets()

        self.setLayout(self.main_layout)
        self.main_widget.setLayout(self.main_layout)

    def initFileWidgets(self):
        # Set up template/position file browsers
        self.template_label = QtWidgets.QLabel('Template:')
        self.template_pathbox = QtWidgets.QLineEdit()
        self.template_button = QtWidgets.QPushButton('Load Template')
        self.template_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.template_layout)
        self.template_layout.addWidget(self.template_label)
        self.template_layout.addWidget(self.template_pathbox)
        self.template_layout.addWidget(self.template_button)

        self.position_label = QtWidgets.QLabel('Controls/Positions:')
        self.position_pathbox = QtWidgets.QLineEdit()
        self.position_button = QtWidgets.QPushButton('Load Positions')
        self.position_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.position_layout)
        self.position_layout.addWidget(self.position_label)
        self.position_layout.addWidget(self.position_pathbox)
        self.position_layout.addWidget(self.position_button)

    def initMainPanelWidgets(self):
        self.component_list = QtWidgets.QListView()
        self.placebo1 = QtWidgets.QLabel('placeholder 1')
        self.placebo2 = QtWidgets.QLabel('placeholder 2')
        self.placebo3 = QtWidgets.QLabel('placeholder 3')
        self.placebo4 = QtWidgets.QLabel('placeholder 4')
        self.data_layout = QtWidgets.QVBoxLayout()
        self.data_layout.addWidget(self.placebo1)
        self.data_layout.addWidget(self.placebo2)
        self.data_layout.addWidget(self.placebo3)
        self.data_layout.addWidget(self.placebo4)
        self.main_panel_layout = QtWidgets.QHBoxLayout()
        self.main_panel_layout.addWidget(self.component_list)
        self.main_panel_layout.addLayout(self.data_layout)
        self.main_layout.addLayout(self.main_panel_layout)

    def initBuildButtonWidgets(self):
        self.loc_button = QtWidgets.QPushButton('Generate Locators')
        self.joint_button = QtWidgets.QPushButton('Generate Joints')
        self.joint_button.clicked.connect(self.controller.generateJoints)
        self.control_button = QtWidgets.QPushButton('Generate Controls')
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.loc_button)
        self.button_layout.addWidget(self.joint_button)
        self.button_layout.addWidget(self.control_button)
        self.main_layout.addLayout(self.button_layout)
        

def run():
        win = ModularRigger()
        win.setWindowTitle("CJ's Rigger")
        win.resize(900, 700)
        win.show()
        return win