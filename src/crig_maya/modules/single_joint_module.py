from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class SingleJointModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.bind_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = python_utils.makeSquareControl('{0}_{1}_base_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.matchTransform(base_placement, base_control)
        cmds.parent(base_control, base_placement)
        cmds.matchTransform(base_placement, self.bind_joint)

        # Connect control to bind joint.
        mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(base_control, self.bind_joint)

        # Create a locator to hold the parent space stuff if it exists.
        data_locator = cmds.spaceLocator(name='{0}_{1}_base_DAT_LOC'.format(self.prefix, self.name))[0]
        data_locator = cmds.parent(data_locator, base_control, relative=True)[0]
        cmds.select(data_locator)
        cmds.addAttr(longName='parentspace', attributeType='matrix')
        cmds.addAttr(longName='parentinvspace', attributeType='matrix')

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return