from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class RootModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_end_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = python_utils.makeSquareControl('{0}_{1}_base_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(base_control, name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'])
        cmds.matchTransform(base_placement, '{0}_{1}_end_BND_JNT'.format(self.prefix, self.name))
        middle_control = python_utils.makeSquareControl('{0}_{1}_middle_CTL_CRV'.format(self.prefix, self.name), 1.5)
        middle_placement = cmds.group(middle_control, name='{0}_{1}_middle_PLC_GRP'.format(self.prefix, self.name), parent=base_control)
        end_control = python_utils.makeSquareControl('{0}_{1}_end_CTL_CRV'.format(self.prefix, self.name), 1)
        end_placement = cmds.group(end_control, name='{0}_{1}_end_PLC_GRP'.format(self.prefix, self.name), parent=middle_control)

        # Move the middle control to where the placement group is.
        cmds.makeIdentity(middle_control)

        # Connect control to bind joint.
        mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(end_control, '{0}_{1}_end_BND_JNT'.format(self.prefix, self.name))

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])
        return