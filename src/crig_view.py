import os
import shiboken2

import maya.OpenMayaUI as OpenMayaUI
import maya.cmds as cmds

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from . import constants
from .crig_maya import maya_controller, maya_utils_controller
from .crig_maya.modules import root_module

def get_maya_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)

class ModularRigger(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)

        self.__class__.instance = self

        self.controller = maya_controller.MayaController()
        self.utils = maya_utils_controller.UtilsController()
        self.filepaths_dict = {}
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
        self.loadFilepathDicts()
        self.initUtilsWidgets()
        self.initMainPanelWidgets()
        self.initBuildButtonWidgets()

        self.setLayout(self.main_layout)
        self.main_widget.setLayout(self.main_layout)

    def initFileWidgets(self):
        # Set up template/position file browsers
        self.template_label = QtWidgets.QLabel('Template:')
        self.template_pathbox = QtWidgets.QLineEdit()
        self.template_button = QtWidgets.QPushButton('Load Template')
        self.template_button.clicked.connect(self.getTemplatePath)
        self.template_save_button = QtWidgets.QPushButton('Save Template')
        self.template_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.template_layout)
        self.template_layout.addWidget(self.template_label)
        self.template_layout.addWidget(self.template_pathbox)
        self.template_layout.addWidget(self.template_button)
        self.template_layout.addWidget(self.template_save_button)

        self.position_label = QtWidgets.QLabel('Component Positions:')
        self.position_pathbox = QtWidgets.QLineEdit()
        self.position_button = QtWidgets.QPushButton('Load Positions')
        self.position_button.clicked.connect(self.getPositionsPath)
        self.position_save_button = QtWidgets.QPushButton('Save Positions')
        self.position_save_button.clicked.connect(self.savePositionsPath)
        self.position_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.position_layout)
        self.position_layout.addWidget(self.position_label)
        self.position_layout.addWidget(self.position_pathbox)
        self.position_layout.addWidget(self.position_button)
        self.position_layout.addWidget(self.position_save_button)

        self.curves_label = QtWidgets.QLabel('Component curves:')
        self.curves_pathbox = QtWidgets.QLineEdit()
        self.curves_button = QtWidgets.QPushButton('Load curves')
        self.curves_button.clicked.connect(self.getCurvesPath)
        self.curves_save_button = QtWidgets.QPushButton('Save curves')
        self.curves_save_button.clicked.connect(self.saveCurvesPath)
        self.curves_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.curves_layout)
        self.curves_layout.addWidget(self.curves_label)
        self.curves_layout.addWidget(self.curves_pathbox)
        self.curves_layout.addWidget(self.curves_button)
        self.curves_layout.addWidget(self.curves_save_button)

    def initUtilsWidgets(self):
        # Init buttons
        self.matrix_constraint_button = QtWidgets.QPushButton('Mat Const')
        self.matrix_constraint_button.clicked.connect(self.utils.constrainByMatrix)
        self.match_RL_button = QtWidgets.QPushButton('Match RL')
        self.match_RL_button.clicked.connect(self.utils.makeRLMatch)
        # Add to layout
        self.utils_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.utils_layout)
        self.utils_layout.addWidget(self.matrix_constraint_button)
        self.utils_layout.addWidget(self.match_RL_button)


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
        self.loc_button = QtWidgets.QPushButton('Generate Bind Joints')
        self.loc_button.clicked.connect(self.controller.generateLocs)
        self.joint_button = QtWidgets.QPushButton('Generate Components')
        self.joint_button.clicked.connect(self.controller.generateJoints)
        self.control_button = QtWidgets.QPushButton('Generate Controls')
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.loc_button)
        self.button_layout.addWidget(self.joint_button)
        self.button_layout.addWidget(self.control_button)
        self.main_layout.addLayout(self.button_layout)

    def loadFilepathDicts(self):
        try:
            self.filepaths_dict = self.controller.loadJSON(constants.PREV_RIG_DATA_PATH)
            self.initTemplateStuff(self.filepaths_dict['template_path'])
            self.initPositionsStuff(self.filepaths_dict['positions_path'])
            self.initCurvesStuff(self.filepaths_dict['curves_path'])
        except IOError:
            constants.RIGGER_LOG.info('Previous rig data not found at {0}, leaving filepaths blank.'.format(constants.PREV_RIG_DATA_PATH))
            self.filepaths_dict = {}

    def saveFilepathDicts(self):
        try:
            self.controller.saveJSON(constants.PREV_RIG_DATA_PATH, self.filepaths_dict)
        except IOError:
            constants.RIGGER_LOG.error('Failed to save previous rig data at {0}'.format(constants.PREV_RIG_DATA_PATH))

    def getTemplatePath(self):
        filename, filter = QtWidgets.QFileDialog.getOpenFileName(self,
        'Select Template',
        constants.TEMPLATES_PATH,
        'YAML files (*.yaml)'
        )
        self.filepaths_dict['template_path'] = filename
        self.saveFilepathDicts()
        self.initTemplateStuff(filename)

    def initTemplateStuff(self, filename):
        self.template_pathbox.setText(filename)
        self.controller.importModules(filename)
        self.controller.duplicateLRComponents()
        self.controller.buildComponentGraph()

    def getPositionsPath(self):
        filename, filter = QtWidgets.QFileDialog.getOpenFileName(self,
        'Select Position File',
        constants.POSITIONS_PATH,
        'JSON files (*.json)'
        )
        self.filepaths_dict['positions_path'] = filename
        self.saveFilepathDicts()
        self.initPositionsStuff(filename)

    def initPositionsStuff(self, filename):
        self.position_pathbox.setText(filename)
        self.controller.importBindJointPositions(filename)

    def savePositionsPath(self):
        filename, filter = QtWidgets.QFileDialog.getSaveFileName(self,
        'Select Position File',
        self.position_pathbox.text(),
        'JSON files (*.json)'
        )
        self.position_pathbox.setText(filename)
        self.controller.saveBindJointPositions(filename)

    def getCurvesPath(self):
        filename, filter = QtWidgets.QFileDialog.getOpenFileName(self,
        'Select Curves File',
        constants.CURVES_PATH,
        'JSON files (*.json)'
        )
        self.filepaths_dict['curves_path'] = filename
        self.saveFilepathDicts()
        self.initCurvesStuff(filename)

    def initCurvesStuff(self, filename):
        self.curves_pathbox.setText(filename)
        self.controller.importCurveData(filename)

    def saveCurvesPath(self):
        filename, filter = QtWidgets.QFileDialog.getSaveFileName(self,
        'Select Curves File',
        self.curves_pathbox.text(),
        'JSON files (*.json)'
        )
        self.curves_pathbox.setText(filename)
        self.controller.saveControlCurveData(filename)

def run():
        win = ModularRigger()
        win.setWindowTitle("CJ's Rigger")
        win.resize(900, 700)
        win.show()
        return win