from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

from . import constants
from . import utils_controller

class VertexJointUIPopup(QtWidgets.QWidget):
    def __init__(self, controller, utils, filepaths_dict):
        QtWidgets.QWidget.__init__(self)

        self.__class__.instance = self

        self.controller = controller
        self.utils = utils
        self.filepaths_dict = filepaths_dict
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName("Vertex Joint Placer")

        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QVBoxLayout()

        self.populateOptions()

        self.setLayout(self.main_layout)
        self.main_widget.setLayout(self.main_layout)

    def populateOptions(self):
        self.component_label = QtWidgets.QLabel('Target Component:')
        self.component_list = QtWidgets.QComboBox()
        self.component_layout = QtWidgets.QHBoxLayout()

        for component in self.controller.components:
            for vertex_joint_component in constants.VERTEX_JOINT_COMPONENTS:
                if component.__class__.__name__ == vertex_joint_component[0]:
                    self.component_list.addItem('{0}_{1}'.format(component.prefix, component.name), vertex_joint_component[1])

        self.main_layout.addLayout(self.component_layout)
        self.component_layout.addWidget(self.component_label)
        self.component_layout.addWidget(self.component_list)

        self.side_label = QtWidgets.QLabel('Joint Side:')
        self.side_list = QtWidgets.QComboBox()

        self.side_layout = QtWidgets.QHBoxLayout()

        self.main_layout.addLayout(self.side_layout)
        self.side_layout.addWidget(self.side_label)
        self.side_layout.addWidget(self.side_list)

        self.run_button = QtWidgets.QPushButton('Create Joints')
        self.run_button.clicked.connect(self.runJointGenerator)
        self.component_list.currentIndexChanged.connect(self.updateSideList)
        self.updateSideList()
        self.main_layout.addWidget(self.run_button)

    def updateSideList(self):
        self.side_list.clear()
        if self.component_list.currentData() == 0:
            self.side_list.addItem('upper')
            self.side_list.addItem('inner')
            self.side_list.addItem('lower')
            self.side_list.addItem('outer')
        elif self.component_list.currentData() == 1:
            self.side_list.addItem('base')


    def runJointGenerator(self):
        joint_side = self.side_list.currentText()
        component_full_name = self.component_list.currentText()
        component_prefix, component_name = component_full_name.split('_')
        for component in self.controller.components:
            if component_prefix == component.prefix and component_name == component.name:
                self.utils.generateVertexJoints(component, joint_side)
                return