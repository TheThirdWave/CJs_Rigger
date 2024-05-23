from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class MouthModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])

        self.jaw_base_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_jaw_base_PAR_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.jaw_joint = cmds.joint(self.jaw_base_joint, name='{0}_{1}_jaw_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.left_corner_joint = cmds.joint(self.base_joint, name='{0}_{1}_left_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.right_corner_joint = cmds.joint(self.base_joint, name='{0}_{1}_right_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        if 'numUpper' in self.componentVars:
            num_upper = self.componentVars['numUpper']
        else:
            num_upper = 0
        self.upper_joints = []
        for idx in range(num_upper):
            self.upper_joints.append(cmds.joint(self.base_joint, name='{0}_{1}_upper_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        if 'numLower' in self.componentVars:
            num_lower = self.componentVars['numLower']
        else:
            num_lower = 0
        self.lower_joints = []
        for idx in range(num_lower):
            self.lower_joints.append(cmds.joint(self.base_joint, name='{0}_{1}_lower_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        self.left_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_inner_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.right_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_middle_PLC_JNT'.format(self.prefix, self.name), position=(1, 0, 0))


    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return
        
        # Create user controls at placement joints.
        left_place_group, left_control = python_utils.replaceJointWithControl(self.left_control_place_joint, 'left', self.baseGroups['placement_group'])
        right_place_group, right_control = python_utils.replaceJointWithControl(self.right_control_place_joint, 'right', self.baseGroups['placement_group'])


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return