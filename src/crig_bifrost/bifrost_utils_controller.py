from maya import cmds
from maya import OpenMaya as om
from .utilities import python_utils
from .. import utils_controller, constants

class UtilsController(utils_controller.UtilsController):

    def __init__(self):
        return

    def constrainByMatrix(self):
        pass

    def makeRLMatch(self):
        pass

    def selectBindJoints(self):
        pass

    def mirrorDrivenKeys(self):
        pass

    def generateVertexJoints(self, component, joint_data):
        pass

    def markAttrsForSaving(self):
        pass

    def appendSoftModDeformer(self):
        pass

    def loadAnim(self, anim_data):
        pass

    def getAnimData(self):
        all_controls = cmds.ls('*CTL_CRV')
        controls_anim = {}
        for control in all_controls:
            keys = python_utils.getAnimKeys(control)
            if keys:
                controls_anim[control] = keys
        return controls_anim