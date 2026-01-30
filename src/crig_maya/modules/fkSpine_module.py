from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class FKSpine(maya_base_module.MayaBaseModule):

    def createBindJoints(self):

        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        # TODO: replace these if statements with some kind of default component vars thing at the data layer.
        if 'numJoints' in self.componentVars:
            num_joints = self.componentVars['numJoints']
        else:
            num_joints = 6

        if 'reverseFK' in self.componentVars:
            self.reverseFK = self.componentVars['reverseFK']
        else:
            self.reverseFK = False

        self.bind_joints = [cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0), scaleCompensate=False)]
        cmds.xform(self.bind_joints[0], rotation=(0, 0, 0))
        for joint_idx in range(num_joints - 1):
            self.bind_joints.append(cmds.joint(self.bind_joints[joint_idx], name='{0}_{1}_{2}_BND_JNT'.format(self.prefix, self.name, joint_idx + 1), position=(0, 1, 0), relative=True, scaleCompensate=False))
        self.bind_joints[-1] = cmds.rename(self.bind_joints[-1], '{0}_{1}_end_BND_JNT'.format(self.prefix, self.name))

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        # Create the fk spine
        fk_group = cmds.group(name='{0}_{1}_fkspine_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        parent = fk_group
        fk_joints = []
        fk_base_controls = []
        fk_base_place_groups = []
        idx = 0
        dupe_joints = python_utils.duplicateBindChain(self.bind_joints[0], parent, 'FK')
        for joint in dupe_joints:
            fk_joints.append(joint)
            idx += 1
        parent = fk_joints[0]
        for joint in fk_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
            control_place_group, joint_control = python_utils.makeDirectControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'FK', 'CTL', 'CRV'), joint, 1.25, 'square')
            fk_base_controls.append(joint_control)
            fk_base_place_groups.append(control_place_group)

        # If reverseFK is asked for, we create a new joint chain going in reverse (the base is parented under the end) underneath
        # the forward fk chain, parent the joints under *those* controls, and do some double-parenting to make the reverse fk
        # chain follow the forward fk chain.
        if self.reverseFK:
            fk_forward_controls = fk_base_controls
            fk_forward_place_groups = fk_base_place_groups
            fk_reverse_controls = [None] * len(fk_joints)
            fk_reverse_place_groups = [None] * len(fk_joints)
            fk_reverse_parent_groups = [None] * len(fk_joints)
            fk_reverse_mult_node = [None] * len(fk_joints)
            fk_reverse_par_mult_node = [None] * len(fk_joints)
            reverse_parent = fk_forward_controls[-1]
            for i in range(len(fk_joints)-1, -1, -1):
                joint = fk_joints[i]
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
                place_group, control = python_utils.makeControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rev_FK', 'CTL', 'CRV'), 1.0, curveType="cross")
                cmds.matchTransform(place_group, fk_forward_place_groups[i])
                cmds.parent(place_group, reverse_parent)
                parent_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rev_FK', 'PAR', 'GRP'), empty=True)
                cmds.matchTransform(parent_group, place_group)
                cmds.parent(parent_group, place_group)
                cmds.parent(control, parent_group)
                fk_reverse_parent_groups[i] = parent_group
                # We get the joint out of the forward chain because otherwise you can't parent it to
                # the bottom.
                if i < (len(fk_joints) - 1):
                    cmds.parent(fk_forward_place_groups[i + 1], fk_forward_controls[i])
                cmds.parent(joint, control)
                reverse_parent = joint
                fk_reverse_controls[i] = control
                fk_reverse_place_groups[i] = place_group

                mult_node = cmds.createNode('multMatrix', name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rev_FK', 'SAS', 'MMULT'))
                fk_reverse_mult_node[i] = mult_node
                cmds.connectAttr('{0}.matrixSum'.format(mult_node), '{0}.offsetParentMatrix'.format(fk_reverse_place_groups[i]))
                par_mult_node = cmds.createNode('multMatrix', name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rev_par_FK', 'SAS', 'MMULT'))
                fk_reverse_par_mult_node[i] = par_mult_node
                cmds.connectAttr('{0}.matrixSum'.format(par_mult_node), '{0}.offsetParentMatrix'.format(fk_reverse_parent_groups[i]))
                # Make the reverse controls follow the forward controls.
                if i < (len(fk_joints) - 1):
                    cmds.connectAttr('{0}.inverseMatrix'.format(fk_forward_controls[i + 1]), '{0}.matrixIn[1]'.format(mult_node))



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
        sasGroups = []
        for i in range(len(fk_base_place_groups)):
            # Create squash and stretch parent group
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(fk_base_controls[i])
            new_sas_group = cmds.group(fk_base_place_groups[i], name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'SAS', 'PAR', 'GRP'))
            cmds.matchTransform(new_sas_group, fk_base_place_groups[i], piv=True)
            sasGroups.append(new_sas_group)

            # Add length and scale factor attributes to the FK control.
            currentControl = fk_base_controls[i]
            cmds.select(currentControl)
            cmds.addAttr(longName='Length', attributeType='float', defaultValue=1.0, minValue=0.0001, keyable=True, hidden=False)
            defaultValue = 1.0
            if self.prefix == 'R':
                defaultValue = -1.0
            cmds.addAttr(longName='ScaleA', attributeType='float', defaultValue=defaultValue, hidden=False, keyable=True)
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
            cmds.setAttr('{0}.operation'.format(addToStartLen), 0)
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

            if not self.reverseFK:
                if i < len(fk_base_place_groups) - 1:
                    cmds.connectAttr('{0}.outputMatrix'.format(composeMatrix), '{0}.offsetParentMatrix'.format(fk_base_place_groups[i + 1]))    
            else:
                cmds.addAttr(fk_reverse_controls[i], longName='Length', attributeType='float', proxy='{0}.Length'.format(currentControl), defaultValue=1.0, minValue=0.0001, keyable=True, hidden=False)
                if i > 0:
                    cmds.connectAttr('{0}.outputMatrix'.format(composeMatrix), '{0}.matrixIn[2]'.format(fk_reverse_mult_node[i - 1]))
                    cmds.connectAttr('{0}.inverseMatrix'.format(sasGroups[i]), '{0}.matrixIn[0]'.format(fk_reverse_mult_node[i - 1]))
        # After making the base fk controls, make higher order controls that can smoothly rotate multiple joints.
        # Get the number of rough controls (half the regular controls rounded up.)
        rough_control_group = cmds.group(name='{0}_{1}_RC1_HOLD_GRP'.format(self.prefix, self.name), parent=fk_group, empty=True)
        parent = rough_control_group
        # TODO: replace the if statements with some kind of default component vars thing at the data layer.
        if 'numRoughFKControls' in self.componentVars:
            num_higher_controls = self.componentVars['numRoughFKControls']
        else:
            num_higher_controls = int((len(fk_base_place_groups) / 2)) + 1
        fk_rough_controls_1 = []
        control_placement_indicies = []
        if self.reverseFK:
            fk_reverse_rough_controls = [None] * num_higher_controls
            fk_reverse_rough_place_groups = [None] * num_higher_controls

        # Generate rough controls and use them to drive the fine controls.
        for i in range(num_higher_controls):
            # Match each rougher control with a base control by doing stupid index math that sucks and I hate it.
            control_placement_indicies.append(int(round((len(fk_base_place_groups) - 1.0) / (num_higher_controls - 1.0) * i)))
            j = 0
            for control in fk_base_controls:
                if j == control_placement_indicies[i]:
                    # Get base control name components and make rough control and placement group.
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control)
                    rough_control = python_utils.makeSquareControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'CTL', 'CRV'), 2)
                    rough_place_group = cmds.group(rough_control, name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'RC1', 'PLC', 'GRP'))
                    cmds.matchTransform(rough_place_group, control)
                    cmds.parent(rough_place_group, parent)
                    cmds.select(rough_control)
                    cmds.addAttr(longName='Length', attributeType='float', defaultValue=1.0, minValue=0.001, keyable=True, hidden=False)
                    # Make parent group for the base control that will be controlled by the rough control.
                    base_control_parent = cmds.listRelatives(control, parent=True)[0]
                    base_control_new_parent = cmds.group(control, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'))
                    cmds.matchTransform(base_control_new_parent, control, piv=True)
                    cmds.connectAttr('{0}.dagLocalMatrix'.format(rough_control), '{0}.offsetParentMatrix'.format(base_control_new_parent))
                    parent = rough_control
                    fk_rough_controls_1.append(rough_control)
                    # Parent constrain the rough place group to the base place group it's on top of
                    # to get the rough control to follow the chain properly.
                    cmds.parentConstraint(fk_base_place_groups[j], rough_place_group, maintainOffset=True)
                    if self.reverseFK:
                        cmds.connectAttr('{0}.inverseMatrix'.format(base_control_new_parent), '{0}.matrixIn[1]'.format(fk_reverse_par_mult_node[j]))
                        reverse_rough_place, reverse_rough_control = python_utils.makeControl('{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rev_RC1', 'CTL', 'CRV'), 1.5, curveType="cross")
                        fk_reverse_rough_controls[i] = reverse_rough_control
                        fk_reverse_rough_place_groups[i] = reverse_rough_place
                        cmds.matchTransform(reverse_rough_place, rough_place_group)
                        if i > 0:
                            cmds.parent(fk_reverse_rough_place_groups[i - 1], reverse_rough_control)
                        if i == num_higher_controls - 1:
                            cmds.parent(reverse_rough_place, rough_control)
                        python_utils.connectTransforms(reverse_rough_control, fk_reverse_parent_groups[j])
                        cmds.parentConstraint(fk_reverse_place_groups[j], reverse_rough_place, maintainOffset=True)
                        
                        
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
            python_utils.createMatrixSwitch(fk_rough_controls_1[cur_placement_index], fk_rough_controls_1[next_placement_index], new_parent_group, False, next_control_weight, True)
            if self.reverseFK:
                cmds.connectAttr('{0}.inverseMatrix'.format(new_parent_group), '{0}.matrixIn[1]'.format(fk_reverse_par_mult_node[i]))
                python_utils.createMatrixSwitch(fk_reverse_rough_controls[cur_placement_index], fk_reverse_rough_controls[next_placement_index], fk_reverse_parent_groups[i], False, next_control_weight, True)


            
        # Create a locator to hold whatever attrs.
        data_locator = cmds.spaceLocator(name='{0}_{1}_fkspine_DAT_LOC'.format(self.prefix, self.name))[0]
        data_locator = cmds.parent(data_locator, fk_joints[0], relative=True)[0]
        cmds.select(data_locator)
        cmds.addAttr(longName='fkFineControls', keyable=True, hidden=False, defaultValue=0.0, minValue=0.0, maxValue=1.0)

        # Connect fk joints to bind joints and controls.
        for idx in range(len(self.bind_joints)):
            python_utils.constrainTransformByMatrix(fk_joints[idx], self.bind_joints[idx])
            cmds.setDrivenKeyframe('{0}.visibility'.format(fk_base_controls[idx]), currentDriver='{0}.fkFineControls'.format(data_locator), driverValue=0, value=0)
            cmds.setDrivenKeyframe('{0}.visibility'.format(fk_base_controls[idx]), currentDriver='{0}.fkFineControls'.format(data_locator), driverValue=1, value=1)

        for control in fk_rough_controls_1:
            cmds.addAttr('{0}'.format(control), longName='fkFineControls', proxy='{0}.fkFineControls'.format(data_locator))


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])
        
        return
