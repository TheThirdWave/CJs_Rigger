from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class AimJointModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.bind_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.aim_loc = cmds.spaceLocator(name='{0}_{1}_base_AIM_LOC'.format(self.prefix, self.name), position=(0, 0, 0))[0]
        cmds.parent(self.aim_loc, self.bind_joint)

        if 'maintainOffset' not in self.componentVars:
            self.componentVars['maintainOffset'] = True

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return
        
        # We unparent the aim locator from the bind joint because it feels cleaner to me.  Then we set up all the input nodes.
        # This component won't have any user-accessable controls, it will be driven by other components.
        cmds.parent(self.aim_loc, self.baseGroups['deform_group'])
        place_group = cmds.group(empty=True, name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name))
        cmds.matchTransform(place_group, self.aim_loc)
        cmds.parent(place_group, self.baseGroups['deform_group'])
        cmds.parent(self.aim_loc, place_group)

        # Connect control to bind joint.
        joint_transform = om2.MFnTransform(python_utils.getDagPath(self.bind_joint))
        up_vec = om2.MVector.kYaxisVector.rotateBy(joint_transform.rotation(om2.MSpace.kWorld, asQuaternion=True))
        cmds.aimConstraint(self.aim_loc, self.bind_joint, aimVector=[0.0, 1.0, 0.0] , upVector=[0.0, 0.0, 1.0], worldUpVector=up_vec.normal(), maintainOffset=self.componentVars['maintainOffset'])

        # The inputs to the mult_matrix will be defined in the rig.json, hopefully I'll have per-component defaults set up soon so it's not too confusing.
        mult_matrix = cmds.createNode('multMatrix', name='{0}_{1}_base_ACNST_MMULT'.format(self.prefix, self.name))
        matrix_decompose = python_utils.decomposeAndConnectMatrix('{0}.matrixSum'.format(mult_matrix), self.aim_loc)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return