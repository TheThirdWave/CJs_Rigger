from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class IKFKLimb(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.start_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_start_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.middle_joint = cmds.joint(self.start_joint, name='{0}_{1}_middle_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        self.end_joint = cmds.joint(self.middle_joint, name='{0}_{1}_end_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        if 'orientOffsetScale' in self.componentVars:
            self.orient_offset_scale = self.componentVars['orientOffsetScale']
        else:
            self.orient_offset_scale = 6

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        # Create some groups for organization.
        fk_group = cmds.group(name='{0}_{1}_fk_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        ik_group = None
        msc_group = cmds.group(name='{0}_{1}_msc_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.inheritTransform(msc_group, off=True)

        # First we have to insert twist joints between the main start/middle/end bind joints.
        # TODO: Add number of upper/lower twist joints as dynamic variable.
        self.upper_arm_bind_joints = python_utils.insertJoints(self.start_joint, self.middle_joint, 'upper', 6)
        self.lower_arm_bind_joints = python_utils.insertJoints(self.middle_joint, self.end_joint, 'lower', 6)

        # Then we duplicate the IK and FK joints
        fk_parent = fk_group
        upper_arm_fk_joints = []
        for joint in self.upper_arm_bind_joints:
            fk_parent = python_utils.duplicateBindJoint(joint, fk_parent, 'FK')
            upper_arm_fk_joints.append(fk_parent)
        start_fk_joint = upper_arm_fk_joints[0]
        lower_arm_fk_joints = []
        for joint in self.lower_arm_bind_joints:
            fk_parent = python_utils.duplicateBindJoint(joint, fk_parent, 'FK')
            lower_arm_fk_joints.append(fk_parent)
        middle_fk_joint = lower_arm_fk_joints[0]
        end_fk_joint = python_utils.duplicateBindJoint(self.end_joint, lower_arm_fk_joints[-1], 'FK')

        # Set joint orients, zero out joint orientation, set rotation order and transfer to rotation.
        for joint in upper_arm_fk_joints:
            cmds.select(joint)
            python_utils.setOrientJoint(joint, 'yzx', 'zup')
            python_utils.zeroJointOrient(joint)
        for joint in lower_arm_fk_joints:
            cmds.select(joint)
            python_utils.setOrientJoint(joint, 'yzx', 'zup')
            python_utils.zeroJointOrient(joint)
        python_utils.setOrientJoint(end_fk_joint, 'none', 'zup')
        python_utils.zeroJointOrient(end_fk_joint)

        # Reverse the right joint chain so things are mirrored properly.
        if self.prefix =='R':
            python_utils.reverseJointChainOnX(start_fk_joint)

        # We want to get the main joints out from under the twist joints in the fk for cycle avoidance reasons.
        cmds.parent(middle_fk_joint, start_fk_joint)
        cmds.parent(end_fk_joint, middle_fk_joint)

        # Now we make the ik joints by duplicating the fk group
        ik_group = cmds.duplicate(fk_group, name=fk_group.replace('fk', 'ik'))[0]
        ik_group_children = cmds.listRelatives(ik_group, type='joint', allDescendents=True, fullPath=True)
        for child in ik_group_children:
            short_name = child.split('|')[-1]
            cmds.rename(child, short_name.replace('FK', 'IK'))
        upper_arm_ik_joints = []
        for joint in upper_arm_fk_joints:
            upper_arm_ik_joints.append(joint.replace('FK', 'IK'))
        start_ik_joint = upper_arm_ik_joints[0]
        lower_arm_ik_joints = []
        for joint in lower_arm_fk_joints:
            lower_arm_ik_joints.append(joint.replace('FK', 'IK'))
        middle_ik_joint = lower_arm_ik_joints[0]
        end_ik_joint = end_fk_joint.replace('FK', 'IK')
        

        # Create FK Controls.
        start_fk_placement, start_fk_control = python_utils.makeDirectControl('{0}_{1}_start_CTL_CRV'.format(self.prefix, self.name), start_fk_joint, 2, "square")
        middle_fk_placement, middle_fk_control = python_utils.makeDirectControl('{0}_{1}_middle_CTL_CRV'.format(self.prefix, self.name), middle_fk_joint, 2, "square")
        end_fk_placement, end_fk_control = python_utils.makeDirectControl('{0}_{1}_end_CTL_CRV'.format(self.prefix, self.name), end_fk_joint, 2, "square")

        cmds.select(start_fk_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='twistScale', attributeType='float', defaultValue=0.0, keyable=True, hidden=False)
        i = 0
        default_scale_factor = 0
        for joint in upper_arm_fk_joints:
            cmds.addAttr(longName='SASScale_{0}'.format(i), attributeType='float', defaultValue=default_scale_factor, minValue=0.0, keyable=True, hidden=False)
            default_scale_factor += 1.0/len(upper_arm_fk_joints)
            python_utils.zeroJointOrient(joint)
            i += 1
        cmds.select(middle_fk_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='twistScale', attributeType='float', defaultValue=1.0, keyable=True, hidden=False)
        if self.prefix == 'R':
            cmds.setAttr('{0}.twistScale'.format(middle_fk_control, -1.0))
        i = 0
        default_scale_factor = 1
        for joint in lower_arm_fk_joints:
            cmds.addAttr(longName='SASScale_{0}'.format(i), attributeType='float', defaultValue=default_scale_factor, minValue=0.0, keyable=True, hidden=False)
            default_scale_factor -= 1.0/len(lower_arm_fk_joints)
            python_utils.zeroJointOrient(joint)
            i += 1

        # Handle FK Squash and Stretch
        self.makeSASNodes(start_fk_control, start_fk_control, upper_arm_fk_joints, middle_fk_placement, middle_fk_control, middle_fk_joint)
        self.makeSASNodes(middle_fk_control, middle_fk_control, lower_arm_fk_joints, end_fk_placement, end_fk_control, end_fk_joint)

        # Handle FK Twist
        # We do some quaternion stuff to get the twist angle between the main joints
        # and then basically just increment that out among the twist joints
        self.makeFKTwistNodes('{0}.twistScale'.format(start_fk_control), upper_arm_fk_joints, middle_fk_joint)
        self.makeFKTwistNodes('{0}.twistScale'.format(middle_fk_control), lower_arm_fk_joints, end_fk_joint)

        # Create Rotate Plane IK system.
        # First we set the current start/mid joint rotations as the "preferred angle"s, otherwise the ik will keep the bend stiff.
        cmds.setAttr('{0}.preferredAngle'.format(start_ik_joint), *cmds.getAttr('{0}.rotate'.format(start_ik_joint))[0])
        cmds.setAttr('{0}.preferredAngle'.format(middle_ik_joint), *cmds.getAttr('{0}.rotate'.format(middle_ik_joint))[0])
        two_bone_solver = cmds.createNode('ik2Bsolver')
        ik_handle, ik_effector = cmds.ikHandle( name='{0}_{1}_base_IKRP_HDL'.format(self.prefix, self.name),
                                                startJoint=start_ik_joint,
                                                endEffector=end_ik_joint,
                                                solver=two_bone_solver )
        ik_effector = cmds.rename(ik_effector, '{0}_{1}_base_IKRP_EFF'.format(self.prefix, self.name))
        #cmds.parent(ik_handle, msc_group)
        # Create IK Controls
        ik_control_group = cmds.group(name='{0}_{1}_ik_ctls_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        end_ik_control_place, end_ik_control = python_utils.makeControl('{0}_{1}_ik_end_CTL_CRV'.format(self.prefix, self.name), 2.0, "circle",)
        cmds.matchTransform(end_ik_control_place, end_ik_joint)
        cmds.parent(end_ik_control_place, ik_control_group)
        if self.prefix == 'R':
            cmds.setAttr('{0}.scale'.format(end_ik_control_place), -1, -1, -1)
        #python_utils.constrainTransformByMatrix(end_ik_control, ik_handle, True, False, ['translate'])
        ik_handle_group = cmds.group(name='{0}_{1}_base_IKRP_PAR_GRP'.format(self.prefix, self.name), parent=end_ik_control, empty=True)
        cmds.matchTransform(ik_handle_group, ik_handle)
        cmds.parent(ik_handle, ik_handle_group)
        cmds.orientConstraint(end_ik_control, end_ik_joint)
        #python_utils.constrainTransformByMatrix(end_ik_control, end_ik_joint, True, False, ['rotate'])
        cmds.connectAttr('{0}.scale'.format(end_ik_control), '{0}.scale'.format(end_ik_joint))
        
        # We create the orient/knee/elbow control and offset it in the direction of the chain bend.
        ik_orient_control_place, ik_orient_control = python_utils.makeControlMatchTransform('{0}_{1}_orient_CTL_CRV'.format(self.prefix, self.name), middle_ik_joint, 2.0, "circle")
        cmds.parent(ik_orient_control_place, ik_control_group)
        if self.prefix == 'R':
            cmds.setAttr('{0}.scale'.format(ik_orient_control_place), -1, -1, -1)
        mid_pole_vec = python_utils.getPoleVec(start_ik_joint, ik_handle, ik_orient_control_place)
        orient_transform = om2.MFnTransform(python_utils.getDagPath(ik_orient_control_place))
        orient_transform.setTranslation(orient_transform.translation(om2.MSpace.kWorld) + (mid_pole_vec * self.orient_offset_scale), om2.MSpace.kWorld)

        # Then we create a pole vector constraint between the orient control and the ik handle
        cmds.poleVectorConstraint(ik_orient_control, ik_handle)

        # Add necessary attrs and create measurement nodes for squash and stretch
        cmds.select(ik_orient_control)
        cmds.addAttr(longName='elbowSnap', attributeType='float', defaultValue=0.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)
        i = 0
        default_scale_factor = 0
        for joint in upper_arm_fk_joints:
            cmds.addAttr(longName='SASScale_{0}'.format(i), attributeType='float', defaultValue=default_scale_factor, minValue=0.0, keyable=True, hidden=False)
            default_scale_factor += 1.0/len(upper_arm_fk_joints)
            i += 1
        cmds.select(end_ik_control)
        cmds.addAttr(longName='bendLength', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='stretch', attributeType='float', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)
        cmds.addAttr(longName='twistScale', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        i = 0
        default_scale_factor = 1
        for joint in lower_arm_fk_joints:
            cmds.addAttr(longName='SASScale_{0}'.format(i), attributeType='float', defaultValue=default_scale_factor, minValue=0.0, keyable=True, hidden=False)
            default_scale_factor -= 1.0/len(lower_arm_fk_joints)
            i += 1
        cmds.select(start_ik_joint)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=True)
        cmds.select(middle_ik_joint)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=True)

        # Create a measurement locator for cycle avoidance reasons.
        start_joint_locator = cmds.spaceLocator(name='{0}_{1}_start_IK_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(start_joint_locator, ik_group)
        cmds.matchTransform(start_joint_locator, start_ik_joint)

        # Create nodes to get the length values that can be put into the squash and stretch math.
        self.createIKLengthNodes(start_joint_locator, upper_arm_ik_joints, lower_arm_ik_joints, ik_orient_control, end_ik_joint, end_ik_control, ik_handle_group)
        self.makeSASNodes(start_ik_joint, ik_orient_control, upper_arm_ik_joints, middle_ik_joint, ik_orient_control, middle_ik_joint, False)
        self.makeSASNodes(middle_ik_joint, end_ik_control, lower_arm_ik_joints, end_ik_joint, end_ik_control, end_ik_joint, False)

        # Make twist nodes
        self.makeFKTwistNodes('{0}.twistScale'.format(end_ik_control), lower_arm_ik_joints, end_ik_joint)

        # Create a locator to hold the ik/fk switch attribute along with whatever else we might need later.
        data_locator = cmds.spaceLocator(name='{0}_{1}_ikfklimbs_DAT_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(data_locator, start_fk_joint, relative=True)
        cmds.select(data_locator)
        cmds.addAttr(longName='ikfkswitch', defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=0)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=0)

        # Proxy the ikfkswitch to all the controls for funsies.
        cmds.addAttr('{0}'.format(start_fk_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))
        cmds.addAttr('{0}'.format(middle_fk_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))
        cmds.addAttr('{0}'.format(end_fk_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))
        cmds.addAttr('{0}'.format(ik_orient_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))
        cmds.addAttr('{0}'.format(end_ik_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))

        # Connect control to bind joint.
        for idx in range(len(self.upper_arm_bind_joints)):
            blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(upper_arm_fk_joints[idx], upper_arm_ik_joints[idx], self.upper_arm_bind_joints[idx])
            cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))
        for idx in range(len(self.lower_arm_bind_joints)):
            blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(lower_arm_fk_joints[idx], lower_arm_ik_joints[idx], self.lower_arm_bind_joints[idx])
            cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))
        blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(end_fk_joint, end_ik_joint, self.end_joint)
        cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return
    
    # Handle FK Squash and Stretch
    # The control Length attribute will control the Y translate of the downstream joints.
    # As the length value of the control increases, the X and Z scale values of the downstream joints should decrease.
    # To control the shape of the squash and stretch we also implement a scale factor for each joint in the SAS chain.
    # To avoid any weird double transformations, each joint is also scaled by the inverse of it's parent joint's squash and stretch.
    # Y translate = (LS)/N
    # X and Z scale values = 1/P(S/(S + b(LS-S)))
    # where:
    #   L = Length value
    #   N = number of twist joints + 1 (assumed to be the length of the joint_list)
    #   S = distance between current joint and next joint
    #   b = Scale factor
    #   p = parent X or Z squash and stretch value
    def makeSASNodes(self, length_node, sasscale_node, joint_list, end_place_group, end_control, end_joint, add_sas_node=True):

        og_distance = python_utils.getTransformDistance(joint_list[0], end_joint)
        parent_scale = None
        start_joint_scale = None

        for i in range(len(joint_list)):
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_list[i])
            
            scaledCurrentDistance = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '2_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(scaledCurrentDistance), 2)
            cmds.setAttr('{0}.floatA'.format(scaledCurrentDistance), og_distance)
            cmds.connectAttr('{0}.length'.format(length_node), '{0}.floatB'.format(scaledCurrentDistance))
            
            # The start joint doesn't translate.
            if i > 0:
                distanceSegment = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '1_SAS_CMATH'), asUtility=True)
                cmds.setAttr('{0}.operation'.format(distanceSegment), 3)
                cmds.connectAttr('{0}.outFloat'.format(scaledCurrentDistance), '{0}.floatA'.format(distanceSegment))
                cmds.setAttr('{0}.floatB'.format(distanceSegment), len(joint_list))

                # They move backwards if they're flipped, so we add a node to invert if it's the right one.
                invertY = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '11_SAS_CMATH'), asUtility=True)
                cmds.setAttr('{0}.operation'.format(invertY), 2)
                cmds.connectAttr('{0}.outFloat'.format(distanceSegment), '{0}.floatA'.format(invertY))
                cmds.setAttr('{0}.floatB'.format(invertY), 1)
                if self.prefix == 'R':
                    cmds.setAttr('{0}.floatB'.format(invertY), -1)
                cmds.connectAttr('{0}.outFloat'.format(invertY), '{0}.translateY'.format(joint_list[i]))

            subtractUnscaledDist = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '3_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(subtractUnscaledDist), 1)
            cmds.connectAttr('{0}.outFloat'.format(scaledCurrentDistance), '{0}.floatA'.format(subtractUnscaledDist))
            cmds.setAttr('{0}.floatB'.format(subtractUnscaledDist), og_distance)

            multByScaleFactor = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '4_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(multByScaleFactor), 2)
            cmds.connectAttr('{0}.outFloat'.format(subtractUnscaledDist), '{0}.floatA'.format(multByScaleFactor))
            cmds.connectAttr('{0}.SASScale_{1}'.format(sasscale_node, i), '{0}.floatB'.format(multByScaleFactor))

            addToStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '5_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(addToStartLen), 0)
            cmds.connectAttr('{0}.outFloat'.format(multByScaleFactor), '{0}.floatA'.format(addToStartLen))
            cmds.setAttr('{0}.floatB'.format(addToStartLen), og_distance)

            divideStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '7_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(divideStartLen), 3)
            cmds.setAttr('{0}.floatA'.format(divideStartLen), og_distance)
            cmds.connectAttr('{0}.outFloat'.format(addToStartLen), '{0}.floatB'.format(divideStartLen))

            invertParentScale = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '10_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(invertParentScale), 3)
            cmds.setAttr('{0}.floatA'.format(invertParentScale), 1)
            if i > 0:
                cmds.connectAttr('{0}.outFloat'.format(parent_scale), '{0}.floatB'.format(invertParentScale))
            else:
                cmds.setAttr('{0}.floatB'.format(invertParentScale), 1)

            multByParentScale = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '6_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(multByParentScale), 2)
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.floatA'.format(multByParentScale))
            if i > 0:
                cmds.connectAttr('{0}.outFloat'.format(invertParentScale), '{0}.floatB'.format(multByParentScale))
            else:
                cmds.setAttr('{0}.floatB'.format(multByParentScale), 1)

            # Connect to joint X and Z scaling.
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleX'.format(joint_list[i]))
            cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleZ'.format(joint_list[i]))

            parent_scale = divideStartLen
            if i == 0 :
                start_joint_scale = parent_scale
            i += 1

        # Finally we add the translate and inverse scaling to the end joint
        if add_sas_node:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(end_control)
            new_sas_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'SAS', 'PAR', 'GRP'), empty=True)
            cmds.matchTransform(new_sas_group, joint_list[-1])
            cmds.matchTransform(new_sas_group, end_place_group, pos=True, rot=False, scl=False, piv=True)
            cmds.parent(new_sas_group, joint_list[0])
            cmds.parent(end_place_group, new_sas_group)

        # The end joint is the next "main" joint in this context so it's directly parented to the previous "main" joint, which is the first joint in "joint_list"
        # which means we treat its' scale and translate values differently (The SAS group is below the placement group, so we subtract the original distance).
        # Y = LS - S
        # X and Z scale values: 1/p
        scaledDistance = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '8_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(scaledDistance), 2)
        cmds.setAttr('{0}.floatA'.format(scaledDistance), og_distance)
        if self.prefix =='R':
            cmds.setAttr('{0}.floatA'.format(scaledDistance), -og_distance)
        cmds.connectAttr('{0}.length'.format(length_node), '{0}.floatB'.format(scaledDistance))

        subtractOGDist = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '9_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(subtractOGDist), 1)
        cmds.connectAttr('{0}.outFloat'.format(scaledDistance), '{0}.floatA'.format(subtractOGDist))
        cmds.setAttr('{0}.floatB'.format(subtractOGDist), og_distance)
        if self.prefix =='R':
            cmds.setAttr('{0}.floatB'.format(subtractOGDist), -og_distance)

        invertParentScale = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '10_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(invertParentScale), 3)
        cmds.setAttr('{0}.floatA'.format(invertParentScale), 1)
        cmds.connectAttr('{0}.outFloat'.format(start_joint_scale), '{0}.floatB'.format(invertParentScale))

        if add_sas_node:
            cmds.connectAttr('{0}.outFloat'.format(scaledDistance), '{0}.translateY'.format(new_sas_group))
            cmds.connectAttr('{0}.outFloat'.format(invertParentScale), '{0}.scaleX'.format(new_sas_group))
            cmds.connectAttr('{0}.outFloat'.format(invertParentScale), '{0}.scaleZ'.format(new_sas_group))
        else:
            cmds.connectAttr('{0}.outFloat'.format(scaledDistance), '{0}.translateY'.format(end_joint))
            #cmds.connectAttr('{0}.outFloat'.format(invertParentScale), '{0}.scaleX'.format(end_joint))
            #cmds.connectAttr('{0}.outFloat'.format(invertParentScale), '{0}.scaleZ'.format(end_joint))

    # We get the twist between the first main joint and the second main joint and then distribute that twist among the twist joints.
    # twist joint Y rotation = A(Ym / N)
    # where:
    # A = a scale factor from [0,1]
    # Ym = the rotation between the main joints about the Y axis
    # N = number of twist joints + 1 (assumed to be the length of the joint_list)
    def makeFKTwistNodes(self, twist_attr, joint_list, end_joint):
        mult_matrix, matrix_decompose, quat_to_euler = python_utils.createRotDiffNodes('{0}.worldMatrix[0]'.format(end_joint), '{0}.worldInverseMatrix[0]'.format(joint_list[0]), ['Y'])
        for joint in joint_list[1:]:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
            rotationIncrement = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '0_TWST_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(rotationIncrement), 3)
            cmds.connectAttr('{0}.outputRotateY'.format(quat_to_euler), '{0}.floatA'.format(rotationIncrement))
            cmds.setAttr('{0}.floatB'.format(rotationIncrement), len(joint_list))

            scaledRotation = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '1_TWST_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(scaledRotation), 2)
            cmds.connectAttr('{0}.outFloat'.format(rotationIncrement), '{0}.floatA'.format(scaledRotation))
            cmds.connectAttr(twist_attr, '{0}.floatB'.format(scaledRotation))

            cmds.connectAttr('{0}.outFloat'.format(scaledRotation), '{0}.rotateY'.format(joint))


    # We want to create some nodes that can produce scalar length values that can be passed into "makeFKSASnodes()"
    # One length value for the upper joints and one length value for the lower joints.
    # By default, arm should stretch to match the main ik control.  Should have a toggle for this behavior on the control.
    # Also would like an ability to squash the arm somehow.
    # Dist nodes are all in world space so they change with scale, need to account for that somehow
    # Lout = (L/OGL) > BL: (L/OGL) | BL
    # where:
    #   Lout = the out length
    #   L = length as determined by the distance node between the end control and start joint
    #   OGL = The original length between the end control and start joint
    #   BL = the bendLength attribute on the end control (defaults to 1)
    #
    #
    def createIKLengthNodes(self, start_joint_loc, upper_joints, lower_joints, middle_control, end_ik_joint, end_control, handle_parent):
        start_ik_joint = upper_joints[0]
        middle_ik_joint = lower_joints[0]
        start_end_dist, start_ik_decomp, end_ctl_decomp = python_utils.createDistNode(
            start_joint_loc,
            handle_parent,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        start_orient_dist, start_ik_decomp, middle_control_decomp = python_utils.createDistNode(
            start_joint_loc,
            middle_control,
            decompose_1=start_ik_decomp,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        orient_end_dist, middle_control_decomp, end_ik_decomp = python_utils.createDistNode(
            middle_control,
            handle_parent,
            decompose_1=middle_control_decomp,
            decompose_2=end_ctl_decomp,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        
        start_mid_og_len = python_utils.getTransformDistance(start_ik_joint, middle_ik_joint)
        mid_end_og_len = python_utils.getTransformDistance(middle_ik_joint, end_ik_joint)
        start_end_og_len = start_mid_og_len + mid_end_og_len

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(end_control)

        # Get ratio of current length:original length
        divideStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_0_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(divideStartLen), 3)
        cmds.connectAttr('{0}.distance'.format(start_end_dist), '{0}.floatA'.format(divideStartLen))
        cmds.setAttr('{0}.floatB'.format(divideStartLen), start_end_og_len)

        # Only modify the lengths of the arm sections if the control is out further than the og distance.
        stretchCondition = cmds.shadingNode('condition', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_SAS_COND'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(stretchCondition), 2)
        cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.firstTerm'.format(stretchCondition))
        cmds.connectAttr('{0}.bendLength'.format(end_control), '{0}.secondTerm'.format(stretchCondition))
        cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.colorIfTrueR'.format(stretchCondition))
        cmds.connectAttr('{0}.bendLength'.format(end_control), '{0}.colorIfFalseR'.format(stretchCondition))

        # Blend between the 'blendLength' attr and the current length ratio
        length_color_blend_2 = cmds.shadingNode('blendColors', name='{0}_{1}_{2}_BLND_BLNDC'.format(prefix, component_name, joint_name), asUtility=True)
        length_color_blend_1 = python_utils.createScalarBlend('{0}.outColorR'.format(stretchCondition), '{0}.bendLength'.format(end_control), '{0}.color2R'.format(length_color_blend_2))
        cmds.connectAttr('{0}.outputR'.format(length_color_blend_1), '{0}.color2G'.format(length_color_blend_2))
        cmds.connectAttr('{0}.stretch'.format(end_control), '{0}.blender'.format(length_color_blend_1))

        # Now for the snap to the orient control stuff we gotta do some more math, treating the upper and lower joints separately.
        divideStartMidLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_1_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(divideStartMidLen), 3)
        cmds.connectAttr('{0}.distance'.format(start_orient_dist), '{0}.floatA'.format(divideStartMidLen))
        cmds.setAttr('{0}.floatB'.format(divideStartMidLen), start_mid_og_len)

        divideMidEndLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_2_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(divideMidEndLen), 3)
        cmds.connectAttr('{0}.distance'.format(orient_end_dist), '{0}.floatA'.format(divideMidEndLen))
        cmds.setAttr('{0}.floatB'.format(divideMidEndLen), mid_end_og_len)

        # And blend the snap lengths for the two joints with the length for the main ik controls using the ""
        cmds.connectAttr('{0}.outFloat'.format(divideStartMidLen), '{0}.color1R'.format(length_color_blend_2))
        cmds.connectAttr('{0}.outFloat'.format(divideMidEndLen), '{0}.color1G'.format(length_color_blend_2))
        cmds.connectAttr('{0}.outputR'.format(length_color_blend_2), '{0}.length'.format(start_ik_joint))
        cmds.connectAttr('{0}.outputG'.format(length_color_blend_2), '{0}.length'.format(middle_ik_joint))
        cmds.connectAttr('{0}.elbowSnap'.format(middle_control), '{0}.blender'.format(length_color_blend_2))

