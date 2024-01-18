from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class SingleJointModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the common groups that all components share if they don't exist already.
        if not self.baseGroups:
            self.baseGroups = python_utils.generate_component_base(self.name, self.prefix)

        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        # We have to initialize the components input/output custom attrs so they can be connected later, even if the component rig hasn't been created yet.
        self.initializeInputandoutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = python_utils.makeSquareControl('{0}_{1}_base_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.matchTransform(base_placement, base_control)
        cmds.parent(base_control, base_placement)
        cmds.matchTransform(base_placement, '{0}_{1}_BND_JNT'.format(self.prefix, self.name))

        # Connect control to bind joint.
        mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(base_control, '{0}_{1}_BND_JNT'.format(self.prefix, self.name))

        # Create a locator to hold the parent space stuff if it exists.
        data_locator = cmds.spaceLocator(name='{0}_{1}_DAT_LOC'.format(self.prefix, self.name))[0]
        data_locator = cmds.parent(data_locator, base_control, relative=True)[0]
        cmds.select(data_locator)
        cmds.addAttr(longName='parentspace', attributeType='matrix')
        cmds.addAttr(longName='parentinvspace', attributeType='matrix')

        # Connect constrain parent group to parent space matrix.
        python_utils.constrainByMatrix('{0}.parentspace'.format(data_locator), self.baseGroups['parent_group'], False)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        # Copy inv world space to placement_GRP to keep the offset around.
        python_utils.copyOverMatrix('{0}.parentinvspace'.format(data_locator), self.baseGroups['placement_group'])

        return