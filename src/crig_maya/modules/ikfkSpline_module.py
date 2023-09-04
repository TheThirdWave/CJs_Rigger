from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

import math

class IKFKSpine(maya_base_module.MayaBaseModule):

    def __init__(self):
        super().__init__()

    def createBindJoints(self):
        # Create the common groups that all components share if they don't exist already.
        if not self.baseGroups:
            self.baseGroups = python_utils.generate_component_base(self.name, self.prefix)

        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        num_joints = 6
        self.bind_joints = [cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))]
        cmds.xform(self.bind_joints[0], rotation=(0, 0, 90))
        for joint_idx in range(num_joints - 1):
            self.bind_joints.append(cmds.joint(self.bind_joints[joint_idx], name='{0}_{1}_{2}_BND_JNT'.format(self.prefix, self.name, joint_idx + 1), position=(1, 0, 0), relative=True))
        self.bind_joints[-1] = cmds.rename(self.bind_joints[-1], '{0}_{1}_end_BND_JNT'.format(self.prefix, self.name))

        # We have to initialize the components input/output custom attrs so they can be connected later, even if the component rig hasn't been created yet.
        self.initializeInputandoutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        # Create ik spine
        ik_group = cmds.group(name='{0}_{1}_ikspine_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        parent = ik_group
        ik_joints = []
        idx = 0
        for joint in self.bind_joints:
            ik_joints.append(python_utils.duplicateBindJoint(joint, parent, 'IK'))
            parent = ik_joints[idx]
            idx += 1
        
        ik_handle, ik_effector, ik_curve = cmds.ikHandle(name='{0}_{1}_base_IKS_HDL'.format(self.prefix, self.name),startJoint=ik_joints[0], endEffector=ik_joints[-1], solver='ikSplineSolver', simplifyCurve=False)
        cmds.rename(ik_effector, '{0}_{1}_base_IKS_EFF'.format(self.prefix, self.name))
        cmds.rename(ik_curve, '{0}_{1}_base_IKS_CRV'.format(self.prefix, self.name))

        #TODO: create secondary/tertiary ik curves/controls for more convenient handling.

        # Create the fk spine
        fk_group = cmds.group(name='{0}_{1}_fkspine_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        parent = fk_group
        fk_joints = []
        idx = 0
        for joint in self.bind_joints:
            fk_joints.append(python_utils.duplicateBindJoint(joint, parent, 'FK'))
            parent = fk_joints[idx]
            idx += 1
        parent = fk_joints[0]
        fk_base_controls = []
        fk_base_place_groups = []
        for joint in fk_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
            control_place_group, joint_control = python_utils.makeDirectControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'FK', 'CTL', 'CRV'), joint, 1.0, 'square')
            fk_base_controls.append(joint_control)
            fk_base_place_groups.append(control_place_group)

        # After making the base fk controls, make higher order controls that can smoothly rotate multiple joints.
        # Get the number of rough controls (half the regular controls rounded up.)
        rough_control_group = cmds.group(name='{0}_{1}_RC1_HOLD_GRP'.format(self.prefix, self.name), parent=fk_group, empty=True)
        parent = rough_control_group
        num_higher_controls = int((len(fk_base_place_groups) / 2)) + 1
        fk_rough_controls_1 = []
        for i in range(num_higher_controls):
            # Match each rougher control with a base control by doing stupid index math that sucks and I hate it.
            j = 0
            for group in fk_base_place_groups:
                control_placement_index = int(round((len(fk_base_place_groups) - 1.0) / (num_higher_controls - 1.0) * i))
                if j == control_placement_index:
                    # Get base control name components and make rough control and placement group.
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(group)
                    rough_control = python_utils.makeSquareControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'CTL', 'CRV'), 1.5)
                    rough_place_group = cmds.group(rough_control, name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'PLC', 'GRP'), parent=parent)
                    cmds.matchTransform(rough_place_group, group)
                    # Make parent group for the base control that will be controlled by the rough control.
                    base_control_parent = cmds.listRelatives(group, parent=True)[0]
                    base_control_new_parent = cmds.group(group, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'), parent=base_control_parent)
                    cmds.matchTransform(base_control_new_parent, group, piv=1)
                    python_utils.constrainTransformByMatrix(rough_control, base_control_new_parent, True)
                    parent = rough_control
                    fk_rough_controls_1.append(rough_control)
                    j = j + 1
                    break
                j = j + 1
            
        



        

        # Create a locator to hold the ik/fk switch attribute along with whatever else we might need later.
        data_locator = cmds.spaceLocator(name='{0}_{1}_ikfkspine_DAT_LOC'.format(self.prefix, self.name))[0]
        data_locator = cmds.parent(data_locator, fk_joints[0], relative=True)[0]
        cmds.select(data_locator)
        cmds.addAttr(longName='ikfkswitch', defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.addAttr(longName='parentspace', attributeType='matrix')
        cmds.addAttr(longName='parentinvspace', attributeType='matrix')

        # Connect constrain parent group to parent space matrix.
        python_utils.constrainByMatrix('{0}.parentspace'.format(data_locator), self.baseGroups['parent_group'], False)

        # Connect ik/fk joints to bind joints.
        for idx in range(len(self.bind_joints)):
            blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(ik_joints[idx], fk_joints[idx], self.bind_joints[idx])
            cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        # Copy inv world space to placement_GRP to keep the offset around.
        python_utils.copyOverMatrix('{0}.parentinvspace'.format(data_locator), self.baseGroups['placement_group'])
        
        return