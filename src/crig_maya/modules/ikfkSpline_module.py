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
        self.bind_joints = [cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0), scaleCompensate=False)]
        cmds.xform(self.bind_joints[0], rotation=(0, 0, 90))
        for joint_idx in range(num_joints - 1):
            self.bind_joints.append(cmds.joint(self.bind_joints[joint_idx], name='{0}_{1}_{2}_BND_JNT'.format(self.prefix, self.name, joint_idx + 1), position=(1, 0, 0), relative=True, scaleCompensate=False))
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
        fk_base_controls = []
        fk_base_place_groups = []
        idx = 0
        for joint in self.bind_joints:
            fk_joints.append(python_utils.duplicateBindJoint(joint, parent, 'FK'))
            parent = fk_joints[idx]
            idx += 1
        parent = fk_joints[0]
        for joint in fk_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
            control_place_group, joint_control = python_utils.makeDirectControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'FK', 'CTL', 'CRV'), joint, 1.0, 'square')
            fk_base_controls.append(joint_control)
            fk_base_place_groups.append(control_place_group)

        # Implement FK Squash and Stretch
        # As control Y translate increases, the X and Z scale values should decrease. (and vice-versa)
        # We calculate a Y translate for both the current joint and the next joint (if current joint is not the end joint)
        # Y translate = a(LSx-Sx)
        # where:
        #   a = Scale factor
        #   L = Length value
        #   Sx = is either S1 or S2
        #   S1 = distance between current joint and previous joint (0 if base joint)
        #   S2 = distance between current joint and next joint (0 if end joint)
        #
        # We only calculate scale values for the current joint.
        # X and Z scale values = S/(S + b(LS-S))
        # where:
        #   b = Scale factor
        #   S = S1 + S2
        multByScaleFactorNodes = []
        roughControlHookNodes = []
        for i in range(len(fk_base_place_groups)):
            # Create squash and stretch parent group
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(fk_base_controls[i])
            new_sas_group = cmds.group(fk_base_controls[i], name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'SAS', 'PAR', 'GRP'))
            cmds.matchTransform(new_sas_group, fk_base_controls[i], piv=True)

            # Add length and scale factor attributes to the FK control.
            currentControl = fk_base_controls[i]
            cmds.select(currentControl)
            cmds.addAttr(longName='Length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
            cmds.addAttr(longName='ScaleA', attributeType='float', defaultValue=1.0, hidden=False, keyable=True)
            cmds.addAttr(longName='ScaleB', attributeType='float', defaultValue=1.0, hidden=False, keyable=True)

            # Get starting distances between joints.
            currentJoint = fk_joints[i]
            distance1 = 0
            if i > 0:
                previousJoint = fk_joints[i - 1]
                distance1 = python_utils.getTransformDistance(currentJoint, previousJoint)
            distance2 = 0
            if i < len(fk_base_place_groups) - 1:
                nextJoint = fk_joints[i + 1]
                distance2 = python_utils.getTransformDistance(currentJoint, nextJoint)

            totalDistance = distance1 + distance2

            # Set up math nodes for the rough controls to hook into later.
            roughControlLengthDiff = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '9_SAS_CMATH'), asUtility=True)
            cmds.select(roughControlLengthDiff)
            cmds.setAttr('{0}.operation'.format(roughControlLengthDiff), 1)
            cmds.setAttr('{0}.floatA'.format(roughControlLengthDiff), 1)
            cmds.setAttr('{0}.floatB'.format(roughControlLengthDiff), 1)
            roughControlHookNodes.append(roughControlLengthDiff)

            roughControlLengthAdd = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '10_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(roughControlLengthAdd), 0)
            cmds.connectAttr('{0}.Length'.format(currentControl), '{0}.floatA'.format(roughControlLengthAdd))
            cmds.connectAttr('{0}.outFloat'.format(roughControlLengthDiff), '{0}.floatB'.format(roughControlLengthAdd))

            # Start makin' math nodes babey
            scaleMultNode = cmds.shadingNode('colorMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '1_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(scaleMultNode), 2)
            cmds.connectAttr('{0}.outFloat'.format(roughControlLengthAdd), '{0}.colorAR'.format(scaleMultNode))
            cmds.connectAttr('{0}.outFloat'.format(roughControlLengthAdd), '{0}.colorAG'.format(scaleMultNode))
            cmds.connectAttr('{0}.outFloat'.format(roughControlLengthAdd), '{0}.colorAB'.format(scaleMultNode))
            cmds.setAttr('{0}.colorBR'.format(scaleMultNode), distance1)
            cmds.setAttr('{0}.colorBG'.format(scaleMultNode), distance2)
            cmds.setAttr('{0}.colorBB'.format(scaleMultNode), totalDistance)

            diffFromStartNode = cmds.shadingNode('colorMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '2_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(diffFromStartNode), 1)
            cmds.connectAttr('{0}.outColor'.format(scaleMultNode), '{0}.colorA'.format(diffFromStartNode))
            cmds.setAttr('{0}.colorBR'.format(diffFromStartNode), distance1)
            cmds.setAttr('{0}.colorBG'.format(diffFromStartNode), distance2)
            cmds.setAttr('{0}.colorBB'.format(diffFromStartNode), totalDistance)

            multByScaleFactorNode = cmds.shadingNode('colorMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '3_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(multByScaleFactorNode), 2)
            cmds.connectAttr('{0}.outColor'.format(diffFromStartNode), '{0}.colorA'.format(multByScaleFactorNode))
            cmds.connectAttr('{0}.ScaleA'.format(currentControl), '{0}.colorBR'.format(multByScaleFactorNode))
            cmds.connectAttr('{0}.ScaleA'.format(currentControl), '{0}.colorBG'.format(multByScaleFactorNode))
            cmds.connectAttr('{0}.ScaleB'.format(currentControl), '{0}.colorBB'.format(multByScaleFactorNode))
            multByScaleFactorNodes.append(multByScaleFactorNode)

            # We add together the Y translates of the current and previous joint's squash and stretch, create the node for that now.
            addPrevJointDisplacement = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '4_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(addPrevJointDisplacement), 0)
            cmds.connectAttr('{0}.outColorR'.format(multByScaleFactorNode), '{0}.floatA'.format(addPrevJointDisplacement))
            cmds.setAttr('{0}.floatB'.format(addPrevJointDisplacement), 0)
            if i > 0:
                cmds.connectAttr('{0}.outColorG'.format(multByScaleFactorNodes[i - 1]), '{0}.floatB'.format(addPrevJointDisplacement))
            
            # Finally Connect the Y displacement to the squash and stretch parent group (I guess it would make more sense to create the group down here but whatever)
            cmds.connectAttr('{0}.outFloat'.format(addPrevJointDisplacement), '{0}.translateY'.format(new_sas_group))

            # Now move on to the X and Z scaling stuff.
            addToStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '5_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(addPrevJointDisplacement), 0)
            cmds.connectAttr('{0}.outColorB'.format(multByScaleFactorNode), '{0}.floatA'.format(addToStartLen))
            cmds.setAttr('{0}.floatB'.format(addToStartLen), totalDistance)

            divideStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '6_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(divideStartLen), 3)
            cmds.setAttr('{0}.floatA'.format(divideStartLen), totalDistance)
            cmds.connectAttr('{0}.outFloat'.format(addToStartLen), '{0}.floatB'.format(divideStartLen))

            # Connect to joint X and Z scaling.
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleX'.format(currentJoint))
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleZ'.format(currentJoint))

            # and finally invert the scaling and connect it to the parent offset matrix of the PLC
            # group for the next joint so the scaling only effects the current joint.
            invertScaling = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '7_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(invertScaling), 3)
            cmds.setAttr('{0}.floatA'.format(invertScaling), 1)
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.floatB'.format(invertScaling))

            composeMatrix = cmds.createNode('composeMatrix', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '8_SAS_CMATH'))
            cmds.connectAttr('{0}.outFloat'.format(invertScaling), '{0}.inputScaleX'.format(composeMatrix))
            cmds.connectAttr('{0}.outFloat'.format(invertScaling), '{0}.inputScaleZ'.format(composeMatrix))

            if i < len(fk_base_place_groups) - 1:
                cmds.connectAttr('{0}.outputMatrix'.format(composeMatrix), '{0}.offsetParentMatrix'.format(fk_base_place_groups[i + 1]))

        # After making the base fk controls, make higher order controls that can smoothly rotate multiple joints.
        # Get the number of rough controls (half the regular controls rounded up.)
        rough_control_group = cmds.group(name='{0}_{1}_RC1_HOLD_GRP'.format(self.prefix, self.name), parent=fk_group, empty=True)
        parent = rough_control_group
        num_higher_controls = int((len(fk_base_place_groups) / 2)) + 1
        fk_rough_controls_1 = []
        control_placement_indicies = []

        # Generate rough controls and use them to drive the fine controls.
        for i in range(num_higher_controls):
            # Match each rougher control with a base control by doing stupid index math that sucks and I hate it.
            control_placement_indicies.append(int(round((len(fk_base_place_groups) - 1.0) / (num_higher_controls - 1.0) * i)))
            j = 0
            for control in fk_base_controls:
                if j == control_placement_indicies[i]:
                    # Get base control name components and make rough control and placement group.
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control)
                    rough_control = python_utils.makeSquareControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'CTL', 'CRV'), 1.5)
                    rough_place_group = cmds.group(rough_control, name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'PLC', 'GRP'))
                    cmds.matchTransform(rough_place_group, control)
                    cmds.parent(rough_place_group, parent)
                    cmds.select(rough_control)
                    cmds.addAttr(longName='Length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
                    # Make parent group for the base control that will be controlled by the rough control.
                    base_control_parent = cmds.listRelatives(control, parent=True)[0]
                    base_control_new_parent = cmds.group(control, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'))
                    cmds.matchTransform(base_control_new_parent, control, piv=True)
                    python_utils.connectTransforms(rough_control, base_control_new_parent)
                    parent = rough_control
                    fk_rough_controls_1.append(rough_control)
                    j = j + 1
                    break
                j = j + 1

        # After creating the rough controls (and connecting them to the fine controls they drive 100%)
        # Go back through and set up the fine controls that are driven by more than one rough control.
        # (and still more index stuff that is dumb and non-pythonic and there's probably a much more straightforward way to go about this.)
        cur_placement_index = 0
        next_placement_index = 1
        for i in range(len(fk_base_place_groups)):
            if i == control_placement_indicies[next_placement_index]:
                cur_placement_index = next_placement_index
                next_placement_index += 1
                continue

            # Because we didn't connect the rough control to the length parameter in the last go around, we do it all here.
            first_index = control_placement_indicies[cur_placement_index]
            next_index = control_placement_indicies[next_placement_index]
            next_control_weight = (i - first_index) / (next_index - first_index)
            scalar_blend_node = python_utils.createScalarBlend(
                '{0}.Length'.format(fk_rough_controls_1[cur_placement_index]),
                '{0}.Length'.format(fk_rough_controls_1[next_placement_index]),
                '{0}.floatA'.format(roughControlHookNodes[i]),
                next_control_weight)
            

            if i == control_placement_indicies[cur_placement_index]:
                continue

            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(fk_base_controls[i])
            new_parent_group = cmds.group(fk_base_controls[i], name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'))
            cmds.matchTransform(new_parent_group, fk_base_controls[i], piv=True)
            python_utils.createMatrixSwitch(fk_rough_controls_1[cur_placement_index], fk_rough_controls_1[next_placement_index], new_parent_group, False, next_control_weight)

            
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