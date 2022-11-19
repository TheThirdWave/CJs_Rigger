import maya.cmds as cmds

from .utilities import python_utils
from .. import base_controller, constants

class MayaController(base_controller.BaseController):

    def __init__(self):
        self._modulePath = constants.MAYA_MODULES_PATH
        self._dccPath = constants.MAYA_CRIG_PATH
        self._modules = []
        self._bindPositionData = {}

    @property
    def modulePath(self):
        return self._modulePath

    @modulePath.setter
    def modulePath(self, m):
        self._modulePath = m

    @property
    def dccPath(self):
        return self._dccPath

    @dccPath.setter
    def dccPath(self, dcc):
        self._dccPath = dcc

    @property
    def modules(self):
        return self._modules

    @modules.setter
    def modules(self, m):
        self._modules = m

    @property
    def bindPositionData(self):
        return self._bindPositionData

    @bindPositionData.setter
    def bindPositionData(self, m):
        self._bindPositionData = m

    def generateLocs(self):
        # First, have the modules generate their bind/location joints.
        for module in self.modules:
            module.createBindJoints()

        # Then, set those joints to the saved positions (if any)
        for module, data in self.bindPositionData.items():
            python_utils.setNodesFromDict(data)

    def generateJoints(self):
        for module in self.modules:
            module.createControlRig()

    def generateControls(self):
        return

    def saveBindJointPositions(self, positions_path):
        position_dict = {}
        for module in self.modules:
            deform_group = module.baseGroups['deform_group']
            children = cmds.listRelatives(deform_group, allDescendents=True, type='transform')
            position_dict['{0}_{1}'.format(module.prefix, module.name)] = python_utils.dictionizeAttrs(children, constants.POSITION_SAVE_ATTRS)
        self.bindPositionData = position_dict
        self.saveJSON(positions_path, position_dict)
