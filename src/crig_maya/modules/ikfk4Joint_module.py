from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class IKFK4Joint(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.start_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_start_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.upper_joint = cmds.joint(self.start_joint, name='{0}_{1}_upper_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        self.lower_joint = cmds.joint(self.upper_joint, name='{0}_{1}_lower_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        self.end_joint = cmds.joint(self.lower_joint, name='{0}_{1}_end_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)

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


        # Then we duplicate the IK and FK joints
        joint_list = []
        dupe_joints = python_utils.duplicateBindChain(self.start_joint, fk_group, 'FK')
        joint_list.append({'fk_joint': dupe_joints[0], 'bind_joint': self.start_joint})
        start_fk_joint = joint_list[0]['fk_joint']
        joint_list.append({'fk_joint': dupe_joints[1], 'bind_joint': self.upper_joint})
        upper_fk_joint = joint_list[1]['fk_joint']
        joint_list.append({'fk_joint': dupe_joints[2], 'bind_joint': self.lower_joint})
        lower_fk_joint = joint_list[2]['fk_joint']
        joint_list.append({'fk_joint': dupe_joints[3], 'bind_joint': self.end_joint})
        end_fk_joint = joint_list[3]['fk_joint']

        # Now we make the ik joints by duplicating the fk group
        ik_group = cmds.duplicate(fk_group, name=fk_group.replace('fk', 'ik'))[0]
        ik_group_children = cmds.listRelatives(ik_group, type='joint', allDescendents=True, fullPath=True)
        for child in ik_group_children:
            short_name = child.split('|')[-1]
            cmds.rename(child, short_name.replace('FK', 'IK'))
        for joint_dict in joint_list:
            joint_dict['ik_joint'] = joint_dict['fk_joint'].replace('FK', 'IK')
        

        # Create FK Controls.
        start_fk_placement, start_fk_control = python_utils.makeDirectControl('{0}_{1}_start_CTL_CRV'.format(self.prefix, self.name), start_fk_joint, 2, "square")
        joint_list[0]['fk_control'] = start_fk_control
        joint_list[0]['fk_place'] = start_fk_placement
        upper_fk_placement, upper_fk_control = python_utils.makeDirectControl('{0}_{1}_upper_CTL_CRV'.format(self.prefix, self.name), upper_fk_joint, 2, "square")
        joint_list[1]['fk_control'] = upper_fk_control
        joint_list[1]['fk_place'] = upper_fk_placement
        lower_fk_placement, lower_fk_control = python_utils.makeDirectControl('{0}_{1}_lower_CTL_CRV'.format(self.prefix, self.name), lower_fk_joint, 2, "square")
        joint_list[2]['fk_control'] = lower_fk_control
        joint_list[2]['fk_place'] = lower_fk_placement
        end_fk_placement, end_fk_control = python_utils.makeDirectControl('{0}_{1}_end_CTL_CRV'.format(self.prefix, self.name), end_fk_joint, 2, "square")
        joint_list[3]['fk_control'] = end_fk_control
        joint_list[3]['fk_place'] = end_fk_placement

        cmds.select(start_fk_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='SASScale_0', attributeType='float', defaultValue=0.0, keyable=True, hidden=False)
        cmds.select(upper_fk_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='SASScale_1', attributeType='float', defaultValue=1.0, keyable=True, hidden=False)
        cmds.select(lower_fk_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='SASScale_2', attributeType='float', defaultValue=1.0, keyable=True, hidden=False)

        # Handle FK Squash and Stretch
        joint_list[0]['fk_sas_joint'] = self.makeFKSASNodes(start_fk_control, 0, start_fk_joint, upper_fk_placement, True)
        joint_list[1]['fk_sas_joint'] = self.makeFKSASNodes(upper_fk_control, 1, upper_fk_joint, lower_fk_placement, True)
        joint_list[2]['fk_sas_joint'] = self.makeFKSASNodes(lower_fk_control, 2, lower_fk_joint, end_fk_placement, True)
        joint_list[3]['fk_sas_joint'] = None

        # Create KEY joints
        for joint_dict in joint_list:
            python_utils.zeroJointOrient(joint_dict['fk_joint'])
            key_joint = cmds.duplicate(joint_dict['fk_joint'], name=joint_dict['fk_joint'].replace('FK', 'KEY'), parentOnly=True)[0]
            joint_dict['fk_key_joint'] = key_joint
            cmds.parent(key_joint, joint_dict['fk_place'])
            cmds.parent(joint_dict['fk_control'], key_joint)
            python_utils.zeroJointOrient(key_joint)

        # Create Rotate Plane IK system.
        # First we set the current start/mid joint rotations as the "preferred angle"s, otherwise the ik will keep the bend stiff.
        start_ik_joint = joint_list[0]['ik_joint']
        upper_ik_joint = joint_list[1]['ik_joint']
        lower_ik_joint = joint_list[2]['ik_joint']
        end_ik_joint = joint_list[3]['ik_joint']
        for joint in joint_list:
            cmds.setAttr('{0}.preferredAngle'.format(joint['ik_joint']), *cmds.getAttr('{0}.rotate'.format(joint['ik_joint']))[0])
        ik_handle, ik_effector = cmds.ikHandle( name='{0}_{1}_base_IKRP_HDL'.format(self.prefix, self.name),
                                                startJoint=start_ik_joint,
                                                endEffector=end_ik_joint,
                                                solver='ikSCsolver' )
        ik_effector = cmds.rename(ik_effector, '{0}_{1}_base_IKRP_EFF'.format(self.prefix, self.name))
        # Create IK Controls
        ik_control_group = cmds.group(name='{0}_{1}_ik_ctls_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        end_ik_control_place, end_ik_control = python_utils.makeControl('{0}_{1}_ik_end_CTL_CRV'.format(self.prefix, self.name), 2.0, "circle",)
        cmds.matchTransform(end_ik_control_place, end_ik_joint)
        cmds.parent(end_ik_control_place, ik_control_group)
        if self.prefix == 'R':
            cmds.setAttr('{0}.scale'.format(end_ik_control_place), -1, -1, -1)
        cmds.parent(ik_handle, end_ik_control)
        #python_utils.constrainTransformByMatrix(end_ik_control, ik_handle, True, False, ['translate'])
        python_utils.constrainTransformByMatrix(end_ik_control, end_ik_joint, True, False, ['rotate'])
        cmds.connectAttr('{0}.scale'.format(end_ik_control), '{0}.scale'.format(end_ik_joint))

        # Add necessary attrs and create measurement nodes for squash and stretch
        cmds.select(end_ik_control)
        cmds.addAttr(longName='bendLength', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='stretch', attributeType='float', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=True)
        i = 0
        default_scale_factor = 1
        for joint in joint_list:
            cmds.addAttr(longName='SASScale_{0}'.format(i), attributeType='float', defaultValue=default_scale_factor, minValue=0.0, keyable=True, hidden=False)
            default_scale_factor -= 1.0/len(joint_list)
            i += 1

        # Create a measurement locator for cycle avoidance reasons.
        start_joint_locator = cmds.spaceLocator(name='{0}_{1}_start_IK_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(start_joint_locator, ik_group)
        cmds.matchTransform(start_joint_locator, start_ik_joint)

        # Create nodes to get the length values that can be put into the squash and stretch math.
        self.createIKLengthNodes(start_joint_locator, joint_list, end_ik_control)
        self.makeFKSASNodes(end_ik_control, 0, start_ik_joint, upper_ik_joint, False)
        self.makeFKSASNodes(end_ik_control, 1, upper_ik_joint, lower_ik_joint, False)
        self.makeFKSASNodes(end_ik_control, 1, lower_ik_joint, end_ik_joint, False)

        # Create a locator to hold the ik/fk switch attribute along with whatever else we might need later.
        data_locator = cmds.spaceLocator(name='{0}_{1}_4joint_DAT_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(data_locator, start_fk_joint, relative=True)
        cmds.select(data_locator)
        cmds.addAttr(longName='ikfkswitch', defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=0)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=0)

        # Proxy the ikfkswitch to all the controls for funsies.
        for joint_dict in joint_list:
            control = joint_dict['fk_control']
            cmds.addAttr('{0}'.format(control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))
        cmds.addAttr('{0}'.format(end_ik_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(data_locator))

        # Connect control to bind joint.
        for joint in joint_list:
            blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(joint['fk_joint'], joint['ik_joint'], joint['bind_joint'])
            cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return
    
    # Handle FK Squash and Stretch
    # We're gonna keep it simple this time, child_node is moving, parent node is squashing:
    # Y translate = LS - S
    # X and Z scale values = (S/(S + b(LS-S)))
    # where:
    #   L = Length value
    #   S = Original distance between current joint and next joint
    #   b = Scale factor
    def makeFKSASNodes(self, length_node, SASScale_index, parent_joint, child_node, add_sas_node=True):

        og_distance = python_utils.getTransformDistance(parent_joint, child_node)

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(parent_joint)
        
        scaledCurrentDistance = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '2_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(scaledCurrentDistance), 2)
        cmds.setAttr('{0}.floatA'.format(scaledCurrentDistance), og_distance)
        cmds.connectAttr('{0}.length'.format(length_node), '{0}.floatB'.format(scaledCurrentDistance))

        subtractUnscaledDist = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '3_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(subtractUnscaledDist), 1)
        cmds.connectAttr('{0}.outFloat'.format(scaledCurrentDistance), '{0}.floatA'.format(subtractUnscaledDist))
        cmds.setAttr('{0}.floatB'.format(subtractUnscaledDist), og_distance)

        multByScaleFactor = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '4_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(multByScaleFactor), 2)
        cmds.connectAttr('{0}.outFloat'.format(subtractUnscaledDist), '{0}.floatA'.format(multByScaleFactor))
        cmds.connectAttr('{0}.SASScale_{1}'.format(length_node, SASScale_index), '{0}.floatB'.format(multByScaleFactor))

        addToStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '5_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(addToStartLen), 0)
        cmds.connectAttr('{0}.outFloat'.format(multByScaleFactor), '{0}.floatA'.format(addToStartLen))
        cmds.setAttr('{0}.floatB'.format(addToStartLen), og_distance)

        divideStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '7_SAS_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(divideStartLen), 3)
        cmds.setAttr('{0}.floatA'.format(divideStartLen), og_distance)
        cmds.connectAttr('{0}.outFloat'.format(addToStartLen), '{0}.floatB'.format(divideStartLen))

        # Connect to joint X and Z scaling.
        cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleX'.format(parent_joint))
        cmds.connectAttr('{0}.outFloat'.format(divideStartLen), '{0}.scaleZ'.format(parent_joint))

        # If needed we add a squash and stretch joint between the parent and child nodes
        if add_sas_node:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(child_node)
            new_sas_joint = cmds.duplicate(parent_joint, parentOnly=True, name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'SAS', 'PAR', 'JNT'))[0]
            cmds.parent(new_sas_joint, parent_joint)
            cmds.matchTransform(new_sas_joint, parent_joint)
            cmds.matchTransform(new_sas_joint, child_node, pos=True, rot=False, scl=False, piv=True)
            cmds.parent(child_node, new_sas_joint)
            python_utils.zeroJointOrient(new_sas_joint)

        # The end joint is the next "main" joint in this context so it's directly parented to the previous "main" joint, which is the first joint in "joint_list"
        # which means we treat its' scale and translate values differently (The SAS group is below the placement group, so we subtract the original distance).
        # Y = LS - S
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

        if add_sas_node:
            cmds.connectAttr('{0}.outFloat'.format(scaledDistance), '{0}.translateY'.format(new_sas_joint))
            return new_sas_joint
        else:
            cmds.connectAttr('{0}.outFloat'.format(scaledDistance), '{0}.translateY'.format(child_node))

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
    # We need a length value for the first 3 joints.
    # By default, chain should stretch to match the main ik control.  Should have a toggle for this behavior on the control.
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
    def createIKLengthNodes(self, start_joint_loc, joints, end_control):
        start_ik_joint = joints[0]['ik_joint']
        upper_ik_joint = joints[1]['ik_joint']
        lower_ik_joint = joints[2]['ik_joint']
        end_ik_joint = joints[3]['ik_joint']
        start_end_dist, start_ik_decomp, end_ctl_decomp = python_utils.createDistNode(
            start_joint_loc,
            end_control,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        start_orient_dist, start_ik_decomp, upper_ik_decomp = python_utils.createDistNode(
            start_joint_loc,
            upper_ik_joint,
            decompose_1=start_ik_decomp,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        orient_end_dist, upper_ik_decomp, lower_ik_decomp = python_utils.createDistNode(
            upper_ik_joint,
            lower_ik_joint,
            decompose_1=upper_ik_decomp,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )
        orient_end_dist, lower_ik_decomp, end_ik_decomp = python_utils.createDistNode(
            lower_ik_joint,
            end_ik_joint,
            decompose_1=lower_ik_decomp,
            decompose_2=end_ctl_decomp,
            space_matrix='{0}.parentInverseMatrix[0]'.format(start_joint_loc)
            )


        start_up_og_len = python_utils.getTransformDistance(start_ik_joint, upper_ik_joint)
        up_low_og_len = python_utils.getTransformDistance(upper_ik_joint, lower_ik_joint)
        low_end_og_len = python_utils.getTransformDistance(lower_ik_joint, end_ik_joint)
        start_end_og_len = start_up_og_len + up_low_og_len + low_end_og_len

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
        length_color_blend_1 = python_utils.createScalarBlend('{0}.outColorR'.format(stretchCondition), '{0}.bendLength'.format(end_control), '{0}.length'.format(end_control))
        cmds.connectAttr('{0}.stretch'.format(end_control), '{0}.blender'.format(length_color_blend_1))

