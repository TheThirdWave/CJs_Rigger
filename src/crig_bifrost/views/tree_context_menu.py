#from PySide2 import QtGui
#from PySide2 import QtCore
#from PySide2 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from ... import constants
from ..utilities import python_utils

class BifModulePublishPopup(QtWidgets.QWidget):
    def __init__(self, controller, utils, module, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.Tool)

        self.__class__.instance = self

        self.controller = controller
        self.utils = utils
        self.module = module
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName("Publish Bifrost Module")

        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QVBoxLayout()

        self.populateOptions()

        self.setLayout(self.main_layout)
        self.main_widget.setLayout(self.main_layout)

    def populateOptions(self):
        self.module_label = QtWidgets.QLabel('Module Name:')
        self.module_lineEdit = QtWidgets.QLineEdit()
        self.module_name_layout = QtWidgets.QHBoxLayout()

        self.main_layout.addLayout(self.module_name_layout)
        self.module_name_layout.addWidget(self.module_label)
        self.module_name_layout.addWidget(self.module_lineEdit)

        self.run_button = QtWidgets.QPushButton('Publish Module')
        self.run_button.clicked.connect(self.runPublish)
        self.main_layout.addWidget(self.run_button)

    def runPublish(self):
        python_utils.publishModule(self.module.graph.name, self.module.path, self.module_lineEdit.text())
        pass


def addBifrostContextMenu(main_view):
    main_view.component_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

    publish_action = QtGui.QAction(main_view)
    publish_action.setText('publish_module')
    publish_action.triggered.connect(lambda: publishModule(main_view))
    main_view.component_tree.addAction(publish_action)

def publishModule(main_view):
    clicked_item = main_view.component_model.itemFromIndex(main_view.component_tree.selectedIndexes()[0])
    clicked_component = clicked_item.data(QtCore.Qt.UserRole)
    component_dict = {}
    for key, value in clicked_component.__dict__.items():
        if '_' in key:
            component_dict[key.replace('_', '')] = value
        else:
            component_dict[key] = value
    component = main_view.controller.getComponent(component_dict['prefix'], component_dict['name'])
    node = component.bifNode
    constants.RIGGER_LOG.warning('hello, node is {}'.format(node))
    main_view.jointWidgetWindow = BifModulePublishPopup(main_view.controller, main_view.utils, node, main_view)
    main_view.jointWidgetWindow.show()
    main_view.jointWidgetWindow.resize(300, 150)
