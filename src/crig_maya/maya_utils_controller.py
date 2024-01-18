from maya import cmds
from maya import OpenMaya as om
from .utilities import python_utils
from .. import utils_controller, constants

class UtilsController(utils_controller.UtilsController):

    def __init__(self):
        return

    def constrainByMatrix(self):
        selection = cmds.ls(selection=True)
        if len(selection) > 2:
            constants.RIGGER_LOG.error('Cannot constrain by matrix, more than two objects selected!')
            return
        
        python_utils.constrainTransformByMatrix(selection[0], selection[1], True, False)

    def makeRLMatch(self):
        selection = cmds.ls(selection=True, transforms=True)
        for node in selection:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(node)
            if prefix != 'L' and prefix != 'R':
                constants.RIGGER_LOG.error('Cannot match component, must select an L_ or R_ object!')
                return
            opposite_prefix = ''
            if prefix == 'L':
                opposite_prefix = 'R'
            if prefix == 'R':
                opposite_prefix = 'L'
            opposite_node = cmds.ls('{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, component_name, joint_name, node_purpose, node_type), transforms=True)[0]
            cmds.matchTransform(opposite_node, node)
            new_transform = om.MFnTransform(python_utils.getDagPath(opposite_node))
            translate = new_transform.translation(om.MSpace.kWorld)
            translate.x = -translate.x
            new_transform.setTranslation(translate, om.MSpace.kWorld)