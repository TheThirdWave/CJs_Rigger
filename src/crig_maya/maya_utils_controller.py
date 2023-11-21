from maya import cmds
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