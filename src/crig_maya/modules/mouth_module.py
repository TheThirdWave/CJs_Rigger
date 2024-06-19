from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class MouthModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])

        self.joint_dict = {}
        self.jaw_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_jaw_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.jaw_joint = cmds.joint(self.jaw_place_joint, name='{0}_{1}_jaw_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['baseJoint'] = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['leftBackJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_left_back_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['leftFrontJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_left_front_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['rightBackJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_right_back_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['rightFrontJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_right_front_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        if 'numControls' in self.componentVars:
            num_controls = self.componentVars['numControls']
        else:
            num_controls = 5

        if 'numUpper' in self.componentVars:
            num_upper = self.componentVars['numUpper']
        else:
            num_upper = 0
        self.joint_dict['upperBackJoints'] = []
        for idx in range(num_upper):
            self.joint_dict['upperBackJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_upper_back_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))
        self.joint_dict['upperFrontJoints'] = []
        for idx in range(num_upper):
            self.joint_dict['upperFrontJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_upper_front_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        if 'numLower' in self.componentVars:
            num_lower = self.componentVars['numLower']
        else:
            num_lower = 0
        self.joint_dict['lowerBackJoints'] = []
        for idx in range(num_lower):
            self.joint_dict['lowerBackJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_lower_back_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))
        self.joint_dict['lowerFrontJoints'] = []
        for idx in range(num_lower):
            self.joint_dict['lowerFrontJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_lower_front_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        self.left_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_left_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.right_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_right_PLC_JNT'.format(self.prefix, self.name), position=(1, 0, 0))
        self.jaw_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_jaw_control_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.upper_controls = []
        for i in range(num_controls):
            self.upper_controls.append(cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_upper_{2}_PLC_JNT'.format(self.prefix, self.name, i), position=(0,0,0)))

        self.lower_controls = []
        for i in range(num_controls):
            self.lower_controls.append(cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_lower_{2}_PLC_JNT'.format(self.prefix, self.name, i), position=(0,0,0)))


    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return
        
        # Create user controls at placement joints.
        left_place_group, left_control = python_utils.replaceJointWithControl(self.left_control_place_joint, 'left', self.baseGroups['placement_group'])
        right_place_group, right_control = python_utils.replaceJointWithControl(self.right_control_place_joint, 'right', self.baseGroups['placement_group'])
        jaw_place_group, jaw_control = python_utils.replaceJointWithControl(self.jaw_control_place_joint, 'jaw_control', self.baseGroups['placement_group'])
        upper_controls_group = cmds.group(name='{0}_{1}_upper_controls_PAR_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        upper_control_objects = []
        i = 0
        for joint in self.upper_controls:
            place_group, control = python_utils.replaceJointWithControl(joint, 'upper_{0}'.format(i), upper_controls_group)
            i += 1
            upper_control_objects.append({'placeGroup': place_group, 'control': control})
        lower_controls_group = cmds.group(name='{0}_{1}_lower_controls_PAR_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        lower_control_objects = []
        i = 0
        for joint in self.lower_controls:
            place_group, control = python_utils.replaceJointWithControl(joint, 'lower_{0}'.format(i), lower_controls_group)
            i += 1
            lower_control_objects.append({'placeGroup': place_group, 'control': control})

        jaw_parent_joint = python_utils.insertJointAtParent(self.jaw_place_joint, self.jaw_joint)
        
        logic_group = '{0}_{1}_logic_PAR_GRP'.format(self.prefix, self.name)

        cmds.group(name=logic_group, parent=self.baseGroups['placement_group'], empty=True)
        cmds.inheritTransform(logic_group, off=True)

        left_control = '{0}_{1}_left_CTL_CRV'.format(self.prefix, self.name)
        right_control = '{0}_{1}_right_CTL_CRV'.format(self.prefix, self.name)

        upper_objects = [ {'backJoint': x} for x in self.joint_dict['upperBackJoints'] ]
        idx = 0
        for node in self.joint_dict['upperFrontJoints']:
            upper_objects[idx]['frontJoint'] = node
            idx += 1
        lower_objects = [ {'backJoint': x} for x in self.joint_dict['lowerBackJoints'] ]
        idx = 0
        for node in self.joint_dict['lowerFrontJoints']:
            lower_objects[idx]['frontJoint'] = node
            idx += 1
        left_objects = {'backJoint': self.joint_dict['leftBackJoint'], 'frontJoint': self.joint_dict['leftFrontJoint']}
        left_objects['control'] = left_control
        left_objects['controlPlaceGroup'] = left_place_group
        right_objects = {'backJoint': self.joint_dict['rightBackJoint'], 'frontJoint': self.joint_dict['rightFrontJoint']}
        right_objects['control'] = right_control
        right_objects['controlPlaceGroup'] = right_place_group
        long_upper_objects = [right_objects] + upper_objects + [left_objects]

        # Create the ribbons that will copy the jaw weighting.
        for object in upper_objects:
            object['frontJointPosition'] = cmds.xform(object['frontJoint'], query=True, worldSpace=True, translation=True)
        upper_curve_1 = cmds.curve(name='{0}_{1}_upper_1_DEF_CRV'.format(self.prefix, self.name), point=[x['frontJointPosition'] for x in upper_objects], degree=1)
        for object in long_upper_objects:
            object['backJointPosition'] = cmds.xform(object['backJoint'], query=True, worldSpace=True, translation=True)
        long_upper_curve = cmds.curve(name='{0}_{1}_long_upper_DEF_CRV'.format(self.prefix, self.name), point=[x['backJointPosition'] for x in long_upper_objects], degree=1)
        python_utils.renameCurveShape(long_upper_curve, long_upper_curve.replace('CRV', 'CRVShape'))
        upper_curve_2 = cmds.curve(name='{0}_{1}_upper_2_DEF_CRV'.format(self.prefix, self.name), point=[x['backJointPosition'] for x in upper_objects], degree=1)
        python_utils.renameCurveShape(upper_curve_2, upper_curve_2.replace('CRV', 'CRVShape'))
        upper_base_ribbon = cmds.loft(upper_curve_1, upper_curve_2, constructionHistory=False, degree=1, name='{0}_{1}_upper_base_DEF_RBN'.format(self.prefix, self.name))[0]
        cmds.parent(upper_base_ribbon, logic_group)
        cmds.xform(upper_base_ribbon, centerPivots=True)
        cmds.delete(upper_curve_1)
        cmds.parent(upper_curve_2, logic_group)
        cmds.parent(long_upper_curve, logic_group)

        for object in lower_objects:
            object['frontJointPosition'] = cmds.xform(object['frontJoint'], query=True, worldSpace=True, translation=True)
        lower_curve_1 = cmds.curve(name='{0}_{1}_lower_1_DEF_CRV'.format(self.prefix, self.name), point=[x['frontJointPosition'] for x in lower_objects], degree=1)
        for object in lower_objects:
            object['backJointPosition'] = cmds.xform(object['backJoint'], query=True, worldSpace=True, translation=True)
        lower_curve_2 = cmds.curve(name='{0}_{1}_lower_2_DEF_CRV'.format(self.prefix, self.name), point=[x['backJointPosition'] for x in lower_objects], degree=1)
        python_utils.renameCurveShape(lower_curve_2, lower_curve_2.replace('CRV', 'CRVShape'))

        lower_base_ribbon = cmds.loft(lower_curve_1, lower_curve_2, constructionHistory=False, degree=1, name='{0}_{1}_lower_base_DEF_RBN'.format(self.prefix, self.name))[0]
        cmds.parent(lower_base_ribbon, logic_group)
        cmds.xform(lower_base_ribbon, centerPivots=True)
        cmds.delete(lower_curve_1)
        cmds.parent(lower_curve_2, logic_group)

        # Create halfway transform and attach it to a mouth corner.
        left_halfway_loc = cmds.spaceLocator(name='{0}_{1}_l_halfway_POS_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(left_halfway_loc, logic_group)
        pOCurve = cmds.createNode('pointOnCurveInfo', name=left_halfway_loc.replace('POS_LOC', 'POS_POCI'))
        cmds.connectAttr('{0}.local'.format(long_upper_curve), '{0}.inputCurve'.format(pOCurve))
        full_param = python_utils.getCurveParam(1, long_upper_curve)
        cmds.setAttr('{0}.parameter'.format(pOCurve), full_param)
        cmds.connectAttr('{0}.result.position'.format(pOCurve), '{0}.translate'.format(left_halfway_loc))

        right_halfway_loc = cmds.spaceLocator(name='{0}_{1}_r_halfway_POS_LOC'.format(self.prefix, self.name))[0]
        cmds.parent(right_halfway_loc, logic_group)
        pOCurve = cmds.createNode('pointOnCurveInfo', name=right_halfway_loc.replace('POS_LOC', 'POS_POCI'))
        cmds.connectAttr('{0}.local'.format(long_upper_curve), '{0}.inputCurve'.format(pOCurve))
        cmds.setAttr('{0}.parameter'.format(pOCurve), 0)
        cmds.connectAttr('{0}.result.position'.format(pOCurve), '{0}.translate'.format(right_halfway_loc))

        # Create a bunch of groups to make the rotation of the halfway sticky curves make sense.
        left_halfway_group = cmds.group(name=left_halfway_loc.replace('POS_LOC', 'PAR_GRP'), empty=True)
        cmds.parent(left_halfway_group, left_halfway_loc)
        cmds.matchTransform(left_halfway_group, jaw_parent_joint)
        left_halfway_rot_group = cmds.group(name=left_halfway_group.replace('halfway', 'halfway_rotation'), empty=True)
        cmds.parent(left_halfway_rot_group, left_halfway_group)
        cmds.matchTransform(left_halfway_rot_group, left_halfway_loc, rotation=False, scale=False)
        multDiv = cmds.createNode('multiplyDivide', name=left_halfway_group.replace('PAR_GRP', 'ROT_MLDV'))
        cmds.setAttr('{0}.operation'.format(multDiv), 2)
        cmds.setAttr('{0}.input2X'.format(multDiv), 2)
        cmds.setAttr('{0}.input2Y'.format(multDiv), 2)
        cmds.setAttr('{0}.input2Z'.format(multDiv), 2)
        cmds.connectAttr('{0}.rotate'.format(jaw_parent_joint), '{0}.input1'.format(multDiv))
        cmds.connectAttr('{0}.output'.format(multDiv), '{0}.rotate'.format(left_halfway_rot_group), force=True)
        left_objects['rotationGroup'] = left_halfway_rot_group
        left_objects['controlJoint'] = cmds.duplicate(left_objects['backJoint'], name=left_objects['backJoint'].replace('back', 'control'))[0]
        cmds.parent(left_objects['controlJoint'], left_halfway_rot_group)

        right_halfway_group = cmds.group(name=right_halfway_loc.replace('POS_LOC', 'PAR_GRP'), empty=True)
        cmds.parent(right_halfway_group, right_halfway_loc)
        cmds.matchTransform(right_halfway_group, jaw_parent_joint)
        right_halfway_rot_group = cmds.group(name=right_halfway_group.replace('halfway', 'halfway_rotation'), empty=True)
        cmds.parent(right_halfway_rot_group, right_halfway_group)
        cmds.matchTransform(right_halfway_rot_group, right_halfway_loc, rotation=False, scale=False)
        multDiv = cmds.createNode('multiplyDivide', name=right_halfway_group.replace('PAR_GRP', 'ROT_MLDV'))
        cmds.setAttr('{0}.operation'.format(multDiv), 2)
        cmds.setAttr('{0}.input2X'.format(multDiv), 2)
        cmds.setAttr('{0}.input2Y'.format(multDiv), 2)
        cmds.setAttr('{0}.input2Z'.format(multDiv), 2)
        cmds.connectAttr('{0}.rotate'.format(jaw_parent_joint), '{0}.input1'.format(multDiv))
        cmds.connectAttr('{0}.output'.format(multDiv), '{0}.rotate'.format(right_halfway_rot_group), force=True)
        right_objects['rotationGroup'] = right_halfway_rot_group
        right_objects['controlJoint'] = cmds.duplicate(right_objects['backJoint'], name=right_objects['backJoint'].replace('back', 'control'))[0]
        cmds.parent(right_objects['controlJoint'], right_halfway_rot_group)

        # Create the sticky ribbons that will follow the halfway locator.
        upper_sticky_ribbon = cmds.duplicate(upper_base_ribbon, name='{0}_{1}_upper_sticky_DEF_RBN'.format(self.prefix, self.name))[0]
        lower_sticky_ribbon = cmds.duplicate(lower_base_ribbon, name='{0}_{1}_lower_sticky_DEF_RBN'.format(self.prefix, self.name))[0]
        cmds.parent(upper_sticky_ribbon, left_halfway_rot_group)
        cmds.parent(lower_sticky_ribbon, left_halfway_rot_group)

        # Create the curves that will blend between the base and sticky curves.
        upper_blend_ribbon = cmds.duplicate(upper_base_ribbon, name='{0}_{1}_upper_blend_DEF_RBN'.format(self.prefix, self.name))[0]
        lower_blend_ribbon = cmds.duplicate(upper_base_ribbon, name='{0}_{1}_lower_blend_DEF_RBN'.format(self.prefix, self.name))[0]
        upper_sticky_blendshape = cmds.blendShape(upper_base_ribbon, upper_sticky_ribbon, upper_blend_ribbon, name='{0}_{1}_upper_blend_RBN_BSHP'.format(self.prefix, self.name), origin='world')[0]
        # We will later attach a skinCluster node to the dense curve, so we want to make sure the input geometry to the skin cluster includes that deformation.
        moving_shape = cmds.listRelatives(upper_base_ribbon)[0]
        cmds.connectAttr('{0}.worldSpace[0]'.format(moving_shape), '{0}.input[0].inputGeometry'.format(upper_sticky_blendshape), force=True)

        lower_sticky_blendshape = cmds.blendShape(lower_base_ribbon, lower_sticky_ribbon, lower_blend_ribbon, name='{0}_{1}_lower_blend_RBN_BSHP'.format(self.prefix, self.name), origin='world')[0]
        cmds.setAttr('{0}.origin'.format(lower_sticky_blendshape), 0)
        # We will later attach a skinCluster node to the dense curve, so we want to make sure the input geometry to the skin cluster includes that deformation.
        moving_shape = cmds.listRelatives(lower_base_ribbon)[0]
        cmds.connectAttr('{0}.worldSpace[0]'.format(moving_shape), '{0}.input[0].inputGeometry'.format(lower_sticky_blendshape), force=True)

        # Add the sticky lips attr to the controls
        cmds.addAttr(left_control, longName='StickyLips_OnOff', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr('{0}.StickyLips_OnOff'.format(left_control), '{0}.{1}'.format(upper_sticky_blendshape, upper_sticky_ribbon))
        reverse_node = cmds.createNode('reverse', name=left_control.replace('CTL_CRV', 'stickylips_REV'))
        cmds.connectAttr('{0}.StickyLips_OnOff'.format(left_control), '{0}.inputX'.format(reverse_node))
        cmds.connectAttr('{0}.outputX'.format(reverse_node), '{0}.{1}'.format(upper_sticky_blendshape, upper_base_ribbon))

        cmds.connectAttr('{0}.StickyLips_OnOff'.format(left_control), '{0}.{1}'.format(lower_sticky_blendshape, lower_sticky_ribbon))
        reverse_node = cmds.createNode('reverse', name=left_control.replace('CTL_CRV', 'stickylips_REV'))
        cmds.connectAttr('{0}.StickyLips_OnOff'.format(left_control), '{0}.inputX'.format(reverse_node))
        cmds.connectAttr('{0}.outputX'.format(reverse_node), '{0}.{1}'.format(lower_sticky_blendshape, lower_base_ribbon))

        # Create the nodes for the "progressive" sticky lips stuff.
        # First the top curve
        cmds.addAttr(left_control, longName='L_StickyLips', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.addAttr(left_control, longName='R_StickyLips', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)

        cmds.addAttr(right_control, longName='StickyLips_OnOff', proxy='{0}.StickyLips_OnOff'.format(left_control), keyable=True)
        cmds.addAttr(right_control, longName='L_StickyLips', proxy='{0}.L_StickyLips'.format(left_control))
        cmds.addAttr(right_control, longName='R_StickyLips', proxy='{0}.R_StickyLips'.format(left_control))

        num_u_cvs, num_v_cvs = python_utils.getNumSurfCVs(upper_blend_ribbon)
        num_cvs = num_u_cvs * num_v_cvs
        half_num_cvs = int(num_v_cvs / 2)
        cv_range = 1/(num_cvs / 2)

        for i in range(half_num_cvs):
            #First the left side
            # Calculate range for CV
            blend_start = cv_range * i * 2
            blend_end = blend_start + cv_range
            # Create SetRange node and hook it up
            makeStickyLipsNodes(left_control, upper_blend_ribbon, upper_sticky_blendshape, blend_start, blend_end, 'L', num_v_cvs, i)

            #Then the right.
            # Create SetRange node and hook it up
            makeStickyLipsNodes(right_control, upper_blend_ribbon, upper_sticky_blendshape, blend_start, blend_end, 'R', -num_v_cvs, num_cvs - i - 1)

        # If there's an odd number of cvs we gotta handle the center one special.
        if num_v_cvs % 2:
            cv = half_num_cvs
            blend_start = 1 - cv_range/2
            blend_end = 1
            l_set_range = cmds.createNode('setRange', name=upper_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_SRG'.format(i)))
            cmds.connectAttr('{0}.{1}_StickyLips'.format(left_control, 'L'), '{0}.valueX'.format(l_set_range))
            cmds.setAttr('{0}.oldMinX'.format(l_set_range), blend_start)
            cmds.setAttr('{0}.oldMaxX'.format(l_set_range), blend_end)
            cmds.setAttr('{0}.minX'.format(l_set_range), 0)
            cmds.setAttr('{0}.maxX'.format(l_set_range), 1)
            l_reverse_node = cmds.createNode('reverse', name=upper_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_REV'.format(i)))
            cmds.connectAttr('{0}.outValueX'.format(l_set_range), '{0}.inputX'.format(l_reverse_node))
            
            r_set_range = cmds.createNode('setRange', name=upper_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_SRG'.format(i)))
            cmds.connectAttr('{0}.{1}_StickyLips'.format(left_control, 'R'), '{0}.valueX'.format(r_set_range))
            cmds.setAttr('{0}.oldMinX'.format(r_set_range), blend_start)
            cmds.setAttr('{0}.oldMaxX'.format(r_set_range), blend_end)
            cmds.setAttr('{0}.minX'.format(r_set_range), 0)
            cmds.setAttr('{0}.maxX'.format(r_set_range), 1)
            r_reverse_node = cmds.createNode('reverse', name=upper_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_REV'.format(i)))
            cmds.connectAttr('{0}.outValueX'.format(r_set_range), '{0}.inputX'.format(r_reverse_node))
            
            average_node = cmds.createNode('plusMinusAverage')
            cmds.setAttr('{0}.operation'.format(average_node), 3)
            cmds.connectAttr('{0}.outputX'.format(l_reverse_node), '{0}.input2D[0].input2Dx'.format(average_node))
            cmds.connectAttr('{0}.outValueX'.format(l_set_range), '{0}.input2D[0].input2Dy'.format(average_node))
            cmds.connectAttr('{0}.outputX'.format(r_reverse_node), '{0}.input2D[1].input2Dx'.format(average_node))
            cmds.connectAttr('{0}.outValueX'.format(r_set_range), '{0}.input2D[1].input2Dy'.format(average_node))
            cmds.connectAttr('{0}.output2D.output2Dx'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(upper_sticky_blendshape, cv))
            cmds.connectAttr('{0}.output2D.output2Dy'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(upper_sticky_blendshape, cv))
            cmds.connectAttr('{0}.output2D.output2Dx'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(upper_sticky_blendshape, cv + num_v_cvs))
            cmds.connectAttr('{0}.output2D.output2Dy'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(upper_sticky_blendshape, cv + num_v_cvs))

        # Then the bottom

        num_u_cvs, num_v_cvs = python_utils.getNumSurfCVs(lower_blend_ribbon)
        num_cvs = num_u_cvs * num_v_cvs
        half_num_cvs = int(num_v_cvs / 2)
        cv_range = 1/(num_cvs / 2)

        for i in range(half_num_cvs):
            #First the left side
            # Calculate range for CV
            blend_start = cv_range * i * 2
            blend_end = blend_start + cv_range
            # Create SetRange node and hook it up
            makeStickyLipsNodes(left_control, lower_blend_ribbon, lower_sticky_blendshape, blend_start, blend_end, 'L', num_v_cvs, i)

            #Then the right.
            # Create SetRange node and hook it up
            makeStickyLipsNodes(right_control, lower_blend_ribbon, lower_sticky_blendshape, blend_start, blend_end, 'R', -num_v_cvs, num_cvs - i - 1)

        # If there's an odd number of cvs we gotta handle the center one special.
        if num_v_cvs % 2:
            cv = half_num_cvs
            blend_start = 1 - cv_range/2
            blend_end = 1
            l_set_range = cmds.createNode('setRange', name=lower_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_SRG'.format(i)))
            cmds.connectAttr('{0}.{1}_StickyLips'.format(left_control, 'L'), '{0}.valueX'.format(l_set_range))
            cmds.setAttr('{0}.oldMinX'.format(l_set_range), blend_start)
            cmds.setAttr('{0}.oldMaxX'.format(l_set_range), blend_end)
            cmds.setAttr('{0}.minX'.format(l_set_range), 0)
            cmds.setAttr('{0}.maxX'.format(l_set_range), 1)
            l_reverse_node = cmds.createNode('reverse', name=lower_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_REV'.format(i)))
            cmds.connectAttr('{0}.outValueX'.format(l_set_range), '{0}.inputX'.format(l_reverse_node))
            
            r_set_range = cmds.createNode('setRange', name=lower_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_SRG'.format(i)))
            cmds.connectAttr('{0}.{1}_StickyLips'.format(left_control, 'R'), '{0}.valueX'.format(r_set_range))
            cmds.setAttr('{0}.oldMinX'.format(r_set_range), blend_start)
            cmds.setAttr('{0}.oldMaxX'.format(r_set_range), blend_end)
            cmds.setAttr('{0}.minX'.format(r_set_range), 0)
            cmds.setAttr('{0}.maxX'.format(r_set_range), 1)
            r_reverse_node = cmds.createNode('reverse', name=lower_blend_ribbon.replace('_DEF_CRV', '_{0}_CRN_REV'.format(i)))
            cmds.connectAttr('{0}.outValueX'.format(r_set_range), '{0}.inputX'.format(r_reverse_node))
            
            average_node = cmds.createNode('plusMinusAverage')
            cmds.setAttr('{0}.operation'.format(average_node), 3)
            cmds.connectAttr('{0}.outputX'.format(l_reverse_node), '{0}.input2D[0].input2Dx'.format(average_node))
            cmds.connectAttr('{0}.outValueX'.format(l_set_range), '{0}.input2D[0].input2Dy'.format(average_node))
            cmds.connectAttr('{0}.outputX'.format(r_reverse_node), '{0}.input2D[1].input2Dx'.format(average_node))
            cmds.connectAttr('{0}.outValueX'.format(r_set_range), '{0}.input2D[1].input2Dy'.format(average_node))
            cmds.connectAttr('{0}.output2D.output2Dx'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(lower_sticky_blendshape, cv))
            cmds.connectAttr('{0}.output2D.output2Dy'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(lower_sticky_blendshape, cv))
            cmds.connectAttr('{0}.output2D.output2Dx'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(lower_sticky_blendshape, cv + num_v_cvs))
            cmds.connectAttr('{0}.output2D.output2Dy'.format(average_node), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(lower_sticky_blendshape, cv + num_v_cvs))


        # Add some attrs to controls and suchlike now that we're done duplicating things for now.

        cmds.addAttr(left_control, longName='Dynamic_SL_OnOff', attributeType='float', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True)
        cmds.addAttr(left_control, longName='Dynamic_SL_MinAngle', attributeType='float', defaultValue=0.0, maxValue=0.0, keyable=True)
        cmds.addAttr(left_control, longName='Dynamic_SL_MaxAngle', attributeType='float', defaultValue=0.0, maxValue=0.0, keyable=True)
        cmds.addAttr(left_control, longName='Manual_L_SL', attributeType='float', defaultValue=0.0, minValue=0.0, maxValue=1.0, keyable=True)
        cmds.addAttr(left_control, longName='Manual_R_SL', attributeType='float', defaultValue=0.0, minValue=0.0, maxValue=1.0, keyable=True)

        cmds.addAttr(right_control, longName='Dynamic_SL_OnOff', proxy='{0}.Dynamic_SL_OnOff'.format(left_control), keyable=True)
        cmds.addAttr(right_control, longName='Dynamic_SL_MinAngle', proxy='{0}.Dynamic_SL_MinAngle'.format(left_control), keyable=True)
        cmds.addAttr(right_control, longName='Dynamic_SL_MaxAngle', proxy='{0}.Dynamic_SL_MaxAngle'.format(left_control), keyable=True)
        cmds.addAttr(right_control, longName='Manual_L_SL', proxy='{0}.Manual_L_SL'.format(left_control), keyable=True)
        cmds.addAttr(right_control, longName='Manual_R_SL', proxy='{0}.Manual_R_SL'.format(left_control), keyable=True)

        # Create nodes to control dynamic stickylips and blend between it and manual stickylips.
        sticky_setRange = cmds.createNode('setRange', name=left_control.replace('_left_CTL_CRV', '_STKY_SRG'))
        colorBlend = cmds.createNode('blendColors', name=left_control.replace('_left_CTL_CRV', '_STKY_BLNDC'))

        cmds.setAttr('{0}.minX'.format(sticky_setRange), 0)
        cmds.setAttr('{0}.maxX'.format(sticky_setRange), 1)
        cmds.setAttr('{0}.Dynamic_SL_MaxAngle'.format(left_control), -25)
        cmds.connectAttr('{0}.Dynamic_SL_MinAngle'.format(left_control), '{0}.oldMaxX'.format(sticky_setRange))
        cmds.connectAttr('{0}.Dynamic_SL_MaxAngle'.format(left_control), '{0}.oldMinX'.format(sticky_setRange))
        cmds.connectAttr('{0}.rotateX'.format(jaw_parent_joint), '{0}.valueX'.format(sticky_setRange))
        cmds.connectAttr('{0}.outValueX'.format(sticky_setRange), '{0}.color1R'.format(colorBlend))
        cmds.connectAttr('{0}.outValueX'.format(sticky_setRange), '{0}.color1G'.format(colorBlend))

        cmds.connectAttr('{0}.Dynamic_SL_OnOff'.format(left_control), '{0}.blender'.format(colorBlend))
        cmds.connectAttr('{0}.Manual_L_SL'.format(left_control), '{0}.color2R'.format(colorBlend))
        cmds.connectAttr('{0}.Manual_R_SL'.format(left_control), '{0}.color2G'.format(colorBlend))
        cmds.connectAttr('{0}.outputR'.format(colorBlend), '{0}.L_StickyLips'.format(left_control))
        cmds.connectAttr('{0}.outputG'.format(colorBlend), '{0}.R_StickyLips'.format(left_control))


        logic_joints_group = cmds.group(name='{0}_{1}_logic_joints_PAR_GRP'.format(self.prefix, self.name), parent=logic_group, empty=True)

        # Create ribbon for very rough controls
        upper_rough_control_ribbon = cmds.duplicate(upper_blend_ribbon, name=upper_blend_ribbon.replace('blend', 'rough_control'))[0]
        cmds.blendShape(upper_blend_ribbon, upper_rough_control_ribbon, weight=[0, 1.0])
        cmds.rebuildSurface(upper_rough_control_ribbon, rebuildType=0, spansU=0, spansV=0, degreeU=0, degreeV=3)
        upper_rebuild_stuff = cmds.rebuildSurface(upper_rough_control_ribbon, rebuildType=0, spansU=0, spansV=2, degreeU=0, degreeV=3)

        lower_rough_control_ribbon = cmds.duplicate(lower_blend_ribbon, name=lower_blend_ribbon.replace('blend', 'rough_control'))[0]
        cmds.blendShape(lower_blend_ribbon, lower_rough_control_ribbon, weight=[0, 1.0])
        cmds.rebuildSurface(lower_rough_control_ribbon, rebuildType=0, spansU=0, spansV=0, degreeU=0, degreeV=3)
        lower_rebuild_stuff = cmds.rebuildSurface(lower_rough_control_ribbon, rebuildType=0, spansU=0, spansV=2, degreeU=0, degreeV=3)

        # Create controls/joints for rough very ribbon
        num_controls = 3
        control_percent = 1.0 / (num_controls - 1)
        upper_very_rough_joints = []
        lower_very_rough_joints = []
        control_joints_group = cmds.group(name='{0}_{1}_control_joints_PAR_GRP'.format(self.prefix, self.name), parent=logic_joints_group, empty=True)
        for idx in range(num_controls):
            createControlOnSurface(0.5, control_percent * idx, upper_blend_ribbon, upper_curve_2, '{0}_{1}_very_rough_upper_{2}_CTL_JNT'.format(self.prefix, self.name, idx), control_joints_group, upper_very_rough_joints)
            
            createControlOnSurface(0.5, control_percent * idx, lower_blend_ribbon, lower_curve_2, '{0}_{1}_very_rough_lower_{2}_CTL_JNT'.format(self.prefix, self.name, idx), control_joints_group, lower_very_rough_joints)
            
        # Then skin the very rough joints to the very rough curve.
        upper_rough_control_skincluster = cmds.skinCluster([x['joint'] for x in upper_very_rough_joints], upper_rough_control_ribbon, toSelectedBones=False, maximumInfluences=2, obeyMaxInfluences=False, dropoffRate=1, name='{0}_{1}_control_CTL_SCST'.format(self.prefix, self.name))[0]
        idx = 0
        for rough_object in upper_very_rough_joints:
            cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(rough_object['parentGroup']), '{0}.bindPreMatrix[{1}]'.format(upper_rough_control_skincluster, idx))
            idx += 1

        lower_rough_control_skincluster = cmds.skinCluster([x['joint'] for x in lower_very_rough_joints], lower_rough_control_ribbon, toSelectedBones=False, maximumInfluences=2, obeyMaxInfluences=False, dropoffRate=1, name='{0}_{1}_control_CTL_SCST'.format(self.prefix, self.name))[0]
        idx = 0
        for rough_object in lower_very_rough_joints:
            cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(rough_object['parentGroup']), '{0}.bindPreMatrix[{1}]'.format(lower_rough_control_skincluster, idx))
            idx += 1

        # Create controls/joints for rough ribbon
        num_controls = 7
        control_percent = 1.0 / (num_controls - 1)
        upper_rough_joints = []
        lower_rough_joints = []
        for idx in range(num_controls):
            createControlOnSurface(0.5, control_percent * idx, upper_rough_control_ribbon, upper_curve_2, '{0}_{1}_rough_upper_{2}_CTL_JNT'.format(self.prefix, self.name, idx), control_joints_group, upper_rough_joints, True, upper_rebuild_stuff[1])

            createControlOnSurface(0.5, control_percent * idx, lower_rough_control_ribbon, lower_curve_2, '{0}_{1}_rough_lower_{2}_CTL_JNT'.format(self.prefix, self.name, idx), control_joints_group, lower_rough_joints, True, lower_rebuild_stuff[1])
            
        # Create controls/joints for rougher ribbon

        upper_control_ribbon = cmds.duplicate(upper_blend_ribbon, name=upper_blend_ribbon.replace('blend', 'control'))[0]
        cmds.blendShape(upper_blend_ribbon, upper_control_ribbon, weight=[0, 1.0])

        lower_control_ribbon = cmds.duplicate(lower_blend_ribbon, name=lower_blend_ribbon.replace('blend', 'control'))[0]
        cmds.blendShape(lower_blend_ribbon, lower_control_ribbon, weight=[0, 1.0])


        # Then skin the rough joints to the rough curve.
        upper_control_skincluster = cmds.skinCluster([x['joint'] for x in upper_rough_joints], upper_control_ribbon, toSelectedBones=False, maximumInfluences=2, obeyMaxInfluences=False, dropoffRate=2, name='{0}_{1}_control_CTL_SCST'.format(self.prefix, self.name))[0]
        idx = 0
        for rough_object in upper_rough_joints:
            cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(rough_object['secondaryParGroup']), '{0}.bindPreMatrix[{1}]'.format(upper_control_skincluster, idx))
            idx += 1
            
        lower_control_skincluster = cmds.skinCluster([x['joint'] for x in lower_rough_joints], lower_control_ribbon, toSelectedBones=False, maximumInfluences=2, obeyMaxInfluences=False, dropoffRate=2, name='{0}_{1}_control_CTL_SCST'.format(self.prefix, self.name))[0]
        idx = 0
        for rough_object in lower_rough_joints:
            cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(rough_object['secondaryParGroup']), '{0}.bindPreMatrix[{1}]'.format(lower_control_skincluster, idx))
            idx += 1

        # Create parent joints to the bind joints and attach them to the blend curve.
        # Plus a bunch of garbage to get the rotations to match the original jaw rotation.
        ribbon_joints_group = cmds.group(name='{0}_{1}_ribbon_joints_PAR_GRP'.format(self.prefix, self.name), parent=logic_joints_group, empty=True)
        for object in upper_objects:
            parent_joint = cmds.duplicate(object['backJoint'], name=object['backJoint'].replace('BND_JNT', 'CTL_JNT'))[0]
            cmds.parent(parent_joint, ribbon_joints_group)
            object['backRibbonJoint'] = parent_joint
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(parent_joint, upper_control_ribbon, connectionsList=['translate'])
            parent_joint = cmds.duplicate(object['frontJoint'], name=object['frontJoint'].replace('BND_JNT', 'CTL_JNT'))[0]
            cmds.parent(parent_joint, object['backRibbonJoint'])
            object['frontRibbonJoint'] = parent_joint
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(parent_joint, upper_control_ribbon, connectionsList=['translate'])
            object['proxyGroup'] = cmds.group(parent=ribbon_joints_group, name=object['backJoint'].replace('BND_JNT', 'PRX_GRP'), empty=True)
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(object['proxyGroup'], upper_base_ribbon)
            object['staticGroup'] = cmds.group(parent=ribbon_joints_group, name=object['backJoint'].replace('BND_JNT', 'STAT_GRP'), empty=True)
            cmds.matchTransform(object['staticGroup'], object['proxyGroup'])
            mult_matrix2, mult_matrix2, quat_to_euler = python_utils.createRotDiffNodes('{0}.worldMatrix[0]'.format(object['staticGroup']), '{0}.worldInverseMatrix[0]'.format(object['proxyGroup']), ['Z'])
            invert_mult = cmds.createNode('multDoubleLinear', name=object['backJoint'].replace('BND_JNT', 'JAW_MDL'))
            cmds.connectAttr('{0}.outputRotateZ'.format(quat_to_euler), '{0}.input1'.format(invert_mult))
            cmds.setAttr('{0}.input2'.format(invert_mult), -1)
            cmds.connectAttr('{0}.output'.format(invert_mult), '{0}.rotateX'.format(object['backRibbonJoint']))    

        for object in lower_objects:
            parent_joint = cmds.duplicate(object['backJoint'], name=object['backJoint'].replace('BND_JNT', 'CTL_JNT'))[0]
            cmds.parent(parent_joint, ribbon_joints_group)
            object['backRibbonJoint'] = parent_joint
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(parent_joint, lower_control_ribbon, connectionsList=['translate'])
            parent_joint = cmds.duplicate(object['frontJoint'], name=object['frontJoint'].replace('BND_JNT', 'CTL_JNT'))[0]
            cmds.parent(parent_joint, object['backRibbonJoint'])
            object['frontRibbonJoint'] = parent_joint
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(parent_joint, lower_control_ribbon, connectionsList=['translate'])
            object['proxyGroup'] = cmds.group(parent=ribbon_joints_group, name=object['backJoint'].replace('BND_JNT', 'PRX_GRP'), empty=True)
            mult_matrix, matrix_decompose, fourByFour, pOSurface = python_utils.pinTransformToSurface(object['proxyGroup'], lower_base_ribbon)
            object['staticGroup'] = cmds.group(parent=ribbon_joints_group, name=object['backJoint'].replace('BND_JNT', 'STAT_GRP'), empty=True)
            cmds.matchTransform(object['staticGroup'], object['proxyGroup'])
            mult_matrix2, mult_matrix2, quat_to_euler = python_utils.createRotDiffNodes('{0}.worldMatrix[0]'.format(object['staticGroup']), '{0}.worldInverseMatrix[0]'.format(object['proxyGroup']), ['Z'])
            invert_mult = cmds.createNode('multDoubleLinear', name=object['backJoint'].replace('BND_JNT', 'JAW_MDL'))
            cmds.connectAttr('{0}.outputRotateZ'.format(quat_to_euler), '{0}.input1'.format(invert_mult))
            cmds.setAttr('{0}.input2'.format(invert_mult), -1)
            cmds.connectAttr('{0}.output'.format(invert_mult), '{0}.rotateX'.format(object['backRibbonJoint']))    
            

        # Now that we're done duplicating the dense curves we add bound_geo attribute to signal to the autorigger to save out it's bind weights.    
        cmds.addAttr(upper_base_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(upper_control_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(upper_rough_control_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(lower_base_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(lower_control_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(lower_rough_control_ribbon, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)
        cmds.addAttr(long_upper_curve, longName=constants.BOUND_GEO_ATTR, attributeType='bool', defaultValue=True)

        # Create user controls for all the tweak joints.  
        # Create an ungodly series of rube goldberg transforms to connect the actual user controls and the rough joints in just the right way.
        # There was probably a more efficient way to go about this.
        mirror_offset_mult_nodes = []
        i = 1
        for object in upper_control_objects:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['control'])
            control_zero_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=object['placeGroup'], empty=True)
            cmds.matchTransform(control_zero_group, object['control'])
            cmds.parent(object['control'], control_zero_group)
            python_utils.mirrorOffset(upper_rough_joints[i]['positionGroup'], upper_rough_joints[i]['parentGroup'], object['placeGroup'], control_zero_group)
            object['controlParentGroup'] = control_zero_group
            mirror_offset_mult_nodes.append(python_utils.mirrorOffset(object['controlParentGroup'], object['control'], upper_rough_joints[i]['parentGroup'], upper_rough_joints[i]['joint'], liveParent=True, liveTParent=True))
            i += 1


        i = 1
        for object in lower_control_objects:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['control'])
            control_zero_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=object['placeGroup'], empty=True)
            cmds.matchTransform(control_zero_group, object['control'])
            cmds.parent(object['control'], control_zero_group)
            python_utils.mirrorOffset(lower_rough_joints[i]['positionGroup'], lower_rough_joints[i]['parentGroup'], object['placeGroup'], control_zero_group)
            object['controlParentGroup'] = control_zero_group
            mirror_offset_mult_nodes.append(python_utils.mirrorOffset(object['controlParentGroup'], object['control'], lower_rough_joints[i]['parentGroup'], lower_rough_joints[i]['joint'], liveParent=True, liveTParent=True))
            i += 1

        # Create controls for the corners of the mouth using a rube goldberg machine of MATRIX MULTIPLICATIONS, uses openmaya, took twice as long to figure out, I am smart.
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(left_objects['controlPlaceGroup'])
        left_objects['controlJawGroup'] = cmds.group(parent=left_objects['controlPlaceGroup'], name=left_objects['controlPlaceGroup'].replace('left_PLC_GRP', 'left_jaw_PAR_GRP'), empty=True)
        mult_matrix = python_utils.mirrorOffset(left_halfway_loc, left_objects['rotationGroup'], left_objects['controlPlaceGroup'], left_objects['controlJawGroup'])
        cmds.matchTransform(left_objects['controlJawGroup'], left_objects['control'])
        cmds.parent(left_objects['control'], left_objects['controlJawGroup'])

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(right_objects['controlPlaceGroup'])
        right_objects['controlJawGroup'] = cmds.group(parent=right_objects['controlPlaceGroup'], name=right_objects['controlPlaceGroup'].replace('right_PLC_GRP', 'right_jaw_PAR_GRP'), empty=True)
        mult_matrix = python_utils.mirrorOffset(right_halfway_loc, right_objects['rotationGroup'], right_objects['controlPlaceGroup'], right_objects['controlJawGroup'])
        cmds.matchTransform(right_objects['controlJawGroup'], right_objects['control'])
        cmds.parent(right_objects['control'], right_objects['controlJawGroup'])


        centerUpRoughControlPlace, centerUpRoughControl = python_utils.makeControl(left_objects['control'].replace('left', 'up_rough_control'), 0.1, curveType="circle")
        jointControlDiffVec = python_utils.getTransformDiffVec(jaw_control, jaw_parent_joint)
        transformFunc1 = om2.MFnTransform(python_utils.getDagPath(upper_very_rough_joints[1]['joint']))
        transformFunc2 = om2.MFnTransform(python_utils.getDagPath(centerUpRoughControlPlace))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(centerUpRoughControl))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)
        cmds.parent(centerUpRoughControlPlace, upper_controls_group)
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(centerUpRoughControl)
        centerUpJawGroup = cmds.group(parent=centerUpRoughControlPlace, name='{0}_{1}_{2}_jaw_PAR_GRP'.format(prefix, component_name, joint_name), empty=True)
        mult_matrix = python_utils.mirrorOffset(upper_very_rough_joints[1]['positionGroup'], upper_very_rough_joints[1]['parentGroup'], centerUpRoughControlPlace, centerUpJawGroup)
        cmds.matchTransform(centerUpJawGroup, centerUpRoughControl)
        cmds.parent(centerUpRoughControl, centerUpJawGroup)

        mirror_offset_mult_nodes.append(python_utils.mirrorOffset(centerUpJawGroup, centerUpRoughControl, upper_very_rough_joints[1]['parentGroup'], upper_very_rough_joints[1]['joint'], liveParent=True, liveTParent=True))

        centerDownRoughControlPlace, centerDownRoughControl = python_utils.makeControl(left_objects['control'].replace('left', 'down_rough_control'), 0.1, curveType="circle")
        jointControlDiffVec = python_utils.getTransformDiffVec(jaw_control, jaw_parent_joint)
        transformFunc1 = om2.MFnTransform(python_utils.getDagPath(lower_very_rough_joints[1]['joint']))
        transformFunc2 = om2.MFnTransform(python_utils.getDagPath(centerDownRoughControlPlace))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(centerDownRoughControl))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)
        cmds.parent(centerDownRoughControlPlace, lower_controls_group)
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(centerDownRoughControl)
        centerDownJawGroup = cmds.group(parent=centerDownRoughControlPlace, name='{0}_{1}_{2}_jaw_PAR_GRP'.format(prefix, component_name, joint_name), empty=True)
        mult_matrix = python_utils.mirrorOffset(lower_very_rough_joints[1]['positionGroup'], lower_very_rough_joints[1]['parentGroup'], centerDownRoughControlPlace, centerDownJawGroup)
        cmds.matchTransform(centerDownJawGroup, centerDownRoughControl)
        cmds.parent(centerDownRoughControl, centerDownJawGroup)

        mirror_offset_mult_nodes.append(python_utils.mirrorOffset(centerDownJawGroup, centerDownRoughControl, lower_very_rough_joints[1]['parentGroup'], lower_very_rough_joints[1]['joint'], liveParent=True, liveTParent=True))

        # Oh yeah and get around to connecting up the jaw control.
        python_utils.connectTransforms(jaw_control, jaw_parent_joint)

        # create controls for the corners of the mouth, somehow.
        # get new controls positions, first we get the vector between the jaw control and the jaw joint (which we assume will give us the
        # vector between the blendshape model and the main model), and then use that to get the positions of the correct vertecies on the original mesh
        # (which is where we'll put the control pivots.
        left_objects['fineCornerPlace'], left_objects['fineControl'] = python_utils.makeControl(left_objects['control'].replace('left', 'left_fine_control'), 0.1, curveType="circle")
        cmds.parent(left_objects['fineCornerPlace'], left_objects['control'])
        left_objects['roughUpPlace'], left_objects['roughUpControl'] = python_utils.makeControl(left_objects['control'].replace('left', 'left_up_rough_control'), 0.1, curveType="circle")
        cmds.parent(left_objects['roughUpPlace'], left_objects['control'])
        left_objects['fineUpPlace'], left_objects['fineUpControl'] = python_utils.makeControl(left_objects['control'].replace('left', 'left_up_control'), 0.1, curveType="circle")
        cmds.parent(left_objects['fineUpPlace'], left_objects['roughUpControl'])
        left_objects['roughDownPlace'], left_objects['roughDownControl'] = python_utils.makeControl(left_objects['control'].replace('left', 'left_down_rough_control'), 0.1, curveType="circle")
        cmds.parent(left_objects['roughDownPlace'], left_objects['control'])
        left_objects['fineDownPlace'], left_objects['fineDownControl'] = python_utils.makeControl(left_objects['control'].replace('left', 'left_down_control'), 0.1, curveType="circle")
        cmds.parent(left_objects['fineDownPlace'], left_objects['roughDownControl'])
        left_objects['roughUpJoint'] = upper_very_rough_joints[-1]['joint']
        left_objects['roughUpJointParent'] = upper_very_rough_joints[-1]['parentGroup']
        left_objects['roughDownJoint'] = lower_very_rough_joints[-1]['joint']
        left_objects['roughDownJointParent'] = lower_very_rough_joints[-1]['parentGroup']
        left_objects['fineUpJoint'] = upper_rough_joints[-1]['joint']
        left_objects['fineUpJointParent'] = upper_rough_joints[-1]['parentGroup']
        left_objects['fineDownJoint'] = lower_rough_joints[-1]['joint']
        left_objects['fineDownJointParent'] = lower_rough_joints[-1]['parentGroup']
        jointControlDiffVec = python_utils.getTransformDiffVec(jaw_control, jaw_parent_joint)
        transformFunc1 = om2.MFnTransform(python_utils.getDagPath(left_objects['controlJoint']))
        transformFunc2 = om2.MFnTransform(python_utils.getDagPath(left_objects['fineCornerPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(left_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        transformFunc1.setObject(python_utils.getDagPath(left_objects['fineUpJoint']))
        transformFunc2.setObject(python_utils.getDagPath(left_objects['roughUpPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(left_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        transformFunc1.setObject(python_utils.getDagPath(left_objects['fineDownJoint']))
        transformFunc2.setObject(python_utils.getDagPath(left_objects['roughDownPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(left_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        right_objects['fineCornerPlace'], right_objects['fineControl'] = python_utils.makeControl(right_objects['control'].replace('right', 'right_fine_control'), 0.1, curveType="circle")
        cmds.parent(right_objects['fineCornerPlace'], right_objects['control'])
        right_objects['roughUpPlace'], right_objects['roughUpControl'] = python_utils.makeControl(right_objects['control'].replace('right', 'right_up_rough_control'), 0.1, curveType="circle")
        cmds.parent(right_objects['roughUpPlace'], right_objects['control'])
        right_objects['fineUpPlace'], right_objects['fineUpControl'] = python_utils.makeControl(right_objects['control'].replace('right', 'right_up_control'), 0.1, curveType="circle")
        cmds.parent(right_objects['fineUpPlace'], right_objects['roughUpControl'])
        right_objects['roughDownPlace'], right_objects['roughDownControl'] = python_utils.makeControl(right_objects['control'].replace('right', 'right_down_rough_control'), 0.1, curveType="circle")
        cmds.parent(right_objects['roughDownPlace'], right_objects['control'])
        right_objects['fineDownPlace'], right_objects['fineDownControl'] = python_utils.makeControl(right_objects['control'].replace('right', 'right_down_control'), 0.1, curveType="circle")
        cmds.parent(right_objects['fineDownPlace'], right_objects['roughDownControl'])
        right_objects['roughUpJoint'] = upper_very_rough_joints[0]['joint']
        right_objects['roughUpJointParent'] = upper_very_rough_joints[0]['parentGroup']
        right_objects['roughDownJoint'] = lower_very_rough_joints[0]['joint']
        right_objects['roughDownJointParent'] = lower_very_rough_joints[0]['parentGroup']
        right_objects['fineUpJoint'] = upper_rough_joints[0]['joint']
        right_objects['fineUpJointParent'] = upper_rough_joints[0]['parentGroup']
        right_objects['fineDownJoint'] = lower_rough_joints[0]['joint']
        right_objects['fineDownJointParent'] = lower_rough_joints[0]['parentGroup']
        jointControlDiffVec = python_utils.getTransformDiffVec(jaw_control, jaw_parent_joint)
        transformFunc1 = om2.MFnTransform(python_utils.getDagPath(right_objects['controlJoint']))
        transformFunc2 = om2.MFnTransform(python_utils.getDagPath(right_objects['fineCornerPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(right_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        transformFunc1.setObject(python_utils.getDagPath(right_objects['fineUpJoint']))
        transformFunc2.setObject(python_utils.getDagPath(right_objects['roughUpPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(right_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        transformFunc1.setObject(python_utils.getDagPath(right_objects['fineDownJoint']))
        transformFunc2.setObject(python_utils.getDagPath(right_objects['roughDownPlace']))
        transformFunc2.setTranslation(transformFunc1.translation(om2.MSpace.kWorld) + jointControlDiffVec, om2.MSpace.kWorld)
        transformFunc1.setObject(python_utils.getDagPath(right_objects['control']))
        transformFunc2.setRotation(transformFunc1.rotation(om2.MSpace.kWorld, asQuaternion=True), om2.MSpace.kWorld)

        # Now actually connect the controls to the joints, somehow.
        left_objects['groupMoveGroup'] = cmds.group(parent=left_objects['rotationGroup'], name=left_objects['controlJoint'].replace('left_control_BND_JNT', 'left_control_PAR_GRP'), empty=True)
        cmds.parent(left_objects['controlJoint'], left_objects['groupMoveGroup'])
        matrix_mult = python_utils.mirrorOffset(left_objects['controlJawGroup'], left_objects['control'], left_objects['rotationGroup'], left_objects['groupMoveGroup'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(left_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        left_objects['groupMoveRoughUpGroup'] = cmds.group(parent=left_objects['roughUpJointParent'], name=left_objects['controlJoint'].replace('left_control_BND_JNT', 'up_left_rough_PAR_GRP'), empty=True)
        cmds.parent(left_objects['roughUpJoint'], left_objects['groupMoveRoughUpGroup'])
        matrix_mult = python_utils.mirrorOffset(left_objects['controlJawGroup'], left_objects['control'], left_objects['roughUpJointParent'], left_objects['groupMoveRoughUpGroup'], liveParent=True, liveTParent=True, pivotTransform=left_objects['groupMoveGroup'])
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(left_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        matrix_mult = python_utils.mirrorOffset(left_objects['roughUpPlace'], left_objects['roughUpControl'], left_objects['groupMoveRoughUpGroup'], left_objects['roughUpJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)

        left_objects['groupMoveUpGroup'] = cmds.group(parent=left_objects['fineUpJointParent'], name=left_objects['controlJoint'].replace('left_control_BND_JNT', 'up_left_control_PAR_GRP'), empty=True)
        cmds.parent(left_objects['fineUpJoint'], left_objects['groupMoveUpGroup'])
        #matrix_mult = mirrorOffset(left_objects['controlJawGroup'], left_objects['control'], left_objects['fineUpJointParent'], left_objects['groupMoveUpGroup'], liveParent=True, liveTParent=True, pivotTransform=left_objects['groupMoveGroup'])
        #cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(left_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        left_objects['groupMoveRoughDownGroup'] = cmds.group(parent=left_objects['roughDownJointParent'], name=left_objects['controlJoint'].replace('left_control_BND_JNT', 'down_left_rough_PAR_GRP'), empty=True)
        cmds.parent(left_objects['roughDownJoint'], left_objects['groupMoveRoughDownGroup'])
        matrix_mult = python_utils.mirrorOffset(left_objects['controlJawGroup'], left_objects['control'], left_objects['roughDownJointParent'], left_objects['groupMoveRoughDownGroup'], liveParent=True, liveTParent=True, pivotTransform=left_objects['groupMoveGroup'])
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(left_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        matrix_mult = python_utils.mirrorOffset(left_objects['roughDownPlace'], left_objects['roughDownControl'], left_objects['groupMoveRoughDownGroup'], left_objects['roughDownJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)

        left_objects['groupMoveDownGroup'] = cmds.group(parent=left_objects['fineDownJointParent'], name=left_objects['controlJoint'].replace('left_control_BND_JNT', 'down_left_control_PAR_GRP'), empty=True)
        cmds.parent(left_objects['fineDownJoint'], left_objects['groupMoveDownGroup'])
        #matrix_mult = mirrorOffset(left_objects['controlJawGroup'], left_objects['control'], left_objects['fineDownJointParent'], left_objects['groupMoveDownGroup'], liveParent=True, liveTParent=True, pivotTransform=left_objects['groupMoveGroup'])
        #cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(left_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        right_objects['groupMoveGroup'] = cmds.group(parent=right_objects['rotationGroup'], name=right_objects['controlJoint'].replace('right_control_BND_JNT', 'right_control_PAR_GRP'), empty=True)
        cmds.parent(right_objects['controlJoint'], right_objects['groupMoveGroup'])
        matrix_mult = python_utils.mirrorOffset(right_objects['controlJawGroup'], right_objects['control'], right_objects['rotationGroup'], right_objects['groupMoveGroup'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(right_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        right_objects['groupMoveRoughUpGroup'] = cmds.group(parent=right_objects['roughUpJointParent'], name=right_objects['controlJoint'].replace('right_control_BND_JNT', 'up_right_rough_PAR_GRP'), empty=True)
        cmds.parent(right_objects['roughUpJoint'], right_objects['groupMoveRoughUpGroup'])
        matrix_mult = python_utils.mirrorOffset(right_objects['controlJawGroup'], right_objects['control'], right_objects['roughUpJointParent'], right_objects['groupMoveRoughUpGroup'], liveParent=True, liveTParent=True, pivotTransform=right_objects['groupMoveGroup'])
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(right_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        matrix_mult = python_utils.mirrorOffset(right_objects['roughUpPlace'], right_objects['roughUpControl'], right_objects['groupMoveRoughUpGroup'], right_objects['roughUpJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)

        right_objects['groupMoveUpGroup'] = cmds.group(parent=right_objects['fineUpJointParent'], name=right_objects['controlJoint'].replace('right_control_BND_JNT', 'up_right_control_PAR_GRP'), empty=True)
        cmds.parent(right_objects['fineUpJoint'], right_objects['groupMoveUpGroup'])
        #matrix_mult = mirrorOffset(right_objects['controlJawGroup'], right_objects['control'], right_objects['fineUpJointParent'], right_objects['groupMoveUpGroup'], liveParent=True, liveTParent=True, pivotTransform=right_objects['groupMoveGroup'])
        #cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(right_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        right_objects['groupMoveRoughDownGroup'] = cmds.group(parent=right_objects['roughDownJointParent'], name=right_objects['controlJoint'].replace('right_control_BND_JNT', 'down_right_rough_PAR_GRP'), empty=True)
        cmds.parent(right_objects['roughDownJoint'], right_objects['groupMoveRoughDownGroup'])
        matrix_mult = python_utils.mirrorOffset(right_objects['controlJawGroup'], right_objects['control'], right_objects['roughDownJointParent'], right_objects['groupMoveRoughDownGroup'], liveParent=True, liveTParent=True, pivotTransform=right_objects['groupMoveGroup'])
        mirror_offset_mult_nodes.append(matrix_mult)
        mirror_offset_mult_nodes.append(matrix_mult)
        cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(right_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        matrix_mult = python_utils.mirrorOffset(right_objects['roughDownPlace'], right_objects['roughDownControl'], right_objects['groupMoveRoughDownGroup'], right_objects['roughDownJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)

        right_objects['groupMoveDownGroup'] = cmds.group(parent=right_objects['fineDownJointParent'], name=right_objects['controlJoint'].replace('right_control_BND_JNT', 'down_right_control_PAR_GRP'), empty=True)
        cmds.parent(right_objects['fineDownJoint'], right_objects['groupMoveDownGroup'])
        #matrix_mult = mirrorOffset(right_objects['controlJawGroup'], right_objects['control'], right_objects['fineDownJointParent'], right_objects['groupMoveDownGroup'], liveParent=True, liveTParent=True, pivotTransform=right_objects['groupMoveGroup'])
        #cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(right_objects['control']), '{0}.matrixIn[5]'.format(matrix_mult), force=True)

        matrix_mult = python_utils.mirrorOffset(left_objects['fineCornerPlace'], left_objects['fineControl'], left_objects['groupMoveGroup'], left_objects['controlJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        matrix_mult = python_utils.mirrorOffset(left_objects['fineUpPlace'], left_objects['fineUpControl'], left_objects['groupMoveUpGroup'], left_objects['fineUpJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        matrix_mult = python_utils.mirrorOffset(left_objects['fineDownPlace'], left_objects['fineDownControl'], left_objects['groupMoveDownGroup'], left_objects['fineDownJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)

        matrix_mult = python_utils.mirrorOffset(right_objects['fineCornerPlace'], right_objects['fineControl'], right_objects['groupMoveGroup'], right_objects['controlJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        matrix_mult = python_utils.mirrorOffset(right_objects['fineUpPlace'], right_objects['fineUpControl'], right_objects['groupMoveUpGroup'], right_objects['fineUpJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)
        matrix_mult = python_utils.mirrorOffset(right_objects['fineDownPlace'], right_objects['fineDownControl'], right_objects['groupMoveDownGroup'], right_objects['fineDownJoint'], liveParent=True, liveTParent=True)
        mirror_offset_mult_nodes.append(matrix_mult)


        python_utils.constrainTransformByMatrix(left_objects['controlJoint'], left_objects['backJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotateq', 'scale', 'translate', 'shear'])
        cmds.parent(left_objects['frontJoint'], left_objects['backJoint'])
        #cmds.delete(left_objects['frontJoint'])

        python_utils.constrainTransformByMatrix(right_objects['controlJoint'], right_objects['backJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'])
        cmds.parent(right_objects['frontJoint'], right_objects['backJoint'])
        #cmds.delete(right_objects['frontJoint'])

        for object in upper_objects:
            python_utils.constrainTransformByMatrix(object['backRibbonJoint'], object['backJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'])
            python_utils.constrainTransformByMatrix(object['frontRibbonJoint'], object['frontJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'])

        for object in lower_objects:
            python_utils.constrainTransformByMatrix(object['backRibbonJoint'], object['backJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'])
            python_utils.constrainTransformByMatrix(object['frontRibbonJoint'], object['frontJoint'], maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'])


        # So, turning on the liveTParent option in the "python_utils.mirrorOffset()" function causes a double transform issue, BUT, if I try to fix the issue by replacing
        # the live connections with static values, the rig explodes, it seems to be some order-of-operations issue when connecting up nodes that are parented to each other.
        # To fix this, I *could* go through each call of the mirrorOffset function and meticulously order them so they don't interfere with one another, but
        # that is hard and I don't want to do that.  Instead, I'll just go through and set the static values after everything has been put into place.
        for mult_node in mirror_offset_mult_nodes:
            connections = cmds.listConnections(mult_node, connections=True, source=True, plugs=True)
            for i in range(0, len(connections), 2):
                if connections[i] == '{0}.matrixIn[6]'.format(mult_node):
                    cmds.disconnectAttr(connections[i+1], connections[i])
                    attr = cmds.getAttr(connections[i+1])
                    cmds.setAttr('{0}.matrixIn[6]'.format(mult_node), attr, type='matrix')
                if connections[i] == '{0}.matrixIn[2]'.format(mult_node):
                    cmds.disconnectAttr(connections[i+1], connections[i])
                    attr = cmds.getAttr(connections[i+1])
                    cmds.setAttr('{0}.matrixIn[2]'.format(mult_node), attr, type='matrix')

        # Make the proxy attrs for all the controls that don't have them yet.
        for object in upper_objects:
            for key, node in object.items():
                if isinstance(node, str) and cmds.listRelatives(node, shapes=True):
                    try:
                        cmds.addAttr(node, longName='StickyLips_OnOff', proxy='{0}.StickyLips_OnOff'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='L_StickyLips', proxy='{0}.L_StickyLips'.format(left_control))
                        cmds.addAttr(node, longName='R_StickyLips', proxy='{0}.R_StickyLips'.format(left_control))
                        cmds.addAttr(node, longName='Dynamic_SL_OnOff', proxy='{0}.Dynamic_SL_OnOff'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Dynamic_SL_MinAngle', proxy='{0}.Dynamic_SL_MinAngle'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Dynamic_SL_MaxAngle', proxy='{0}.Dynamic_SL_MaxAngle'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Manual_L_SL', proxy='{0}.Manual_L_SL'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Manual_R_SL', proxy='{0}.Manual_R_SL'.format(left_control), keyable=True)
                    except:
                        continue

        for object in lower_objects:
            for key, node in object.items():
                if isinstance(node, str) and cmds.listRelatives(node, shapes=True):
                    try:
                        cmds.addAttr(node, longName='StickyLips_OnOff', proxy='{0}.StickyLips_OnOff'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='L_StickyLips', proxy='{0}.L_StickyLips'.format(left_control))
                        cmds.addAttr(node, longName='R_StickyLips', proxy='{0}.R_StickyLips'.format(left_control))
                        cmds.addAttr(node, longName='Dynamic_SL_OnOff', proxy='{0}.Dynamic_SL_OnOff'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Dynamic_SL_MinAngle', proxy='{0}.Dynamic_SL_MinAngle'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Dynamic_SL_MaxAngle', proxy='{0}.Dynamic_SL_MaxAngle'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Manual_L_SL', proxy='{0}.Manual_L_SL'.format(left_control), keyable=True)
                        cmds.addAttr(node, longName='Manual_R_SL', proxy='{0}.Manual_R_SL'.format(left_control), keyable=True)
                    except:
                        continue

        for key, node in left_objects.items():
            if isinstance(node, str) and cmds.listRelatives(node, shapes=True):
                try:
                    cmds.addAttr(node, longName='StickyLips_OnOff', proxy='{0}.StickyLips_OnOff'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='L_StickyLips', proxy='{0}.L_StickyLips'.format(left_control))
                    cmds.addAttr(node, longName='R_StickyLips', proxy='{0}.R_StickyLips'.format(left_control))
                    cmds.addAttr(node, longName='Dynamic_SL_OnOff', proxy='{0}.Dynamic_SL_OnOff'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Dynamic_SL_MinAngle', proxy='{0}.Dynamic_SL_MinAngle'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Dynamic_SL_MaxAngle', proxy='{0}.Dynamic_SL_MaxAngle'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Manual_L_SL', proxy='{0}.Manual_L_SL'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Manual_R_SL', proxy='{0}.Manual_R_SL'.format(left_control), keyable=True)
                except:
                    continue

        for key, node in right_objects.items():
            if isinstance(node, str) and cmds.listRelatives(node, shapes=True):
                try:
                    cmds.addAttr(node, longName='StickyLips_OnOff', proxy='{0}.StickyLips_OnOff'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='L_StickyLips', proxy='{0}.L_StickyLips'.format(left_control))
                    cmds.addAttr(node, longName='R_StickyLips', proxy='{0}.R_StickyLips'.format(left_control))
                    cmds.addAttr(node, longName='Dynamic_SL_OnOff', proxy='{0}.Dynamic_SL_OnOff'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Dynamic_SL_MinAngle', proxy='{0}.Dynamic_SL_MinAngle'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Dynamic_SL_MaxAngle', proxy='{0}.Dynamic_SL_MaxAngle'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Manual_L_SL', proxy='{0}.Manual_L_SL'.format(left_control), keyable=True)
                    cmds.addAttr(node, longName='Manual_R_SL', proxy='{0}.Manual_R_SL'.format(left_control), keyable=True)
                except:
                    continue

        # Do some clean up.
        cmds.delete(upper_curve_2)
        #cmds.delete(long_upper_curve)
        cmds.delete(lower_curve_2)


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return
    
def makeStickyLipsNodes(control, blend_ribbon, blend_shape, blend_start, blend_end, side_prefix, cv_width, idx):
    set_range = cmds.createNode('setRange', name=blend_ribbon.replace('_DEF_RBN', '_{0}_CRN_SRG'.format(idx)))
    cmds.connectAttr('{0}.{1}_StickyLips'.format(control, side_prefix), '{0}.valueX'.format(set_range))
    cmds.setAttr('{0}.oldMinX'.format(set_range), blend_start)
    cmds.setAttr('{0}.oldMaxX'.format(set_range), blend_end)
    cmds.setAttr('{0}.minX'.format(set_range), 0)
    cmds.setAttr('{0}.maxX'.format(set_range), 1)
    reverse_node = cmds.createNode('reverse', name=blend_ribbon.replace('_DEF_RBN', '_{0}_CRN_REV'.format(idx)))
#    cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.inputX'.format(reverse_node))
    cmds.setAttr('{0}.inputX'.format(reverse_node), 0)
    cmds.connectAttr('{0}.outputX'.format(reverse_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(blend_shape, idx))
    cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(blend_shape, idx))
    cmds.connectAttr('{0}.outputX'.format(reverse_node), '{0}.inputTarget[0].inputTargetGroup[0].targetWeights[{1}]'.format(blend_shape, (idx + cv_width)))
    cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.inputTarget[0].inputTargetGroup[1].targetWeights[{1}]'.format(blend_shape, (idx + cv_width)))

def createControlOnSurface(fakeU, fakeV, ribbon, ribbonCurve, name, controlParent, jointList, secondaryTransform=False, rebuildSurface=None):
    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(name)
    pointOnCurve = python_utils.getPointAlongCurve((fakeV), ribbonCurve)
    rough_joint = cmds.joint(controlParent, name='{0}_{1}_{2}_CTL_JNT'.format(prefix, component_name, joint_name), position=[pointOnCurve.x, pointOnCurve.y, pointOnCurve.z])
    pos_group = cmds.group(name='{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name), parent=controlParent, empty=True)
    par_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=controlParent, empty=True)
    par_group_1 = None
    cmds.matchTransform(pos_group, rough_joint)
    cmds.matchTransform(par_group, pos_group)
    cmds.parent(par_group, pos_group)
    cmds.parent(rough_joint, par_group)
    if secondaryTransform:
        par_group_1 = cmds.group(name='{0}_{1}_{2}_secondary_PAR_GRP'.format(prefix, component_name, joint_name), parent=controlParent, empty=True)
        cmds.matchTransform(par_group_1, par_group)
        cmds.parent(par_group_1, pos_group)
        cmds.parent(par_group, par_group_1)
    uselessPoint, realU, uselessV = python_utils.getPointAlongSurface(fakeU, (fakeV), ribbon)
    closestPoint, closestU, closestV = python_utils.getClosestPointOnSurface(pos_group, ribbon)
    pOSurface = cmds.createNode('pointOnSurfaceInfo', name=rough_joint.replace('CTL_JNT', 'DEF_POSI'))
    cmds.connectAttr('{0}.local'.format(ribbon), '{0}.inputSurface'.format(pOSurface))
    cmds.setAttr('{0}.parameterU'.format(pOSurface), realU)
    cmds.setAttr('{0}.parameterV'.format(pOSurface), closestV)
    fourByFour = cmds.createNode('fourByFourMatrix', name=pos_group.replace('PLC_GRP', 'DEF_4X4'))
    python_utils.hookUpPointOnSurfaceTo4x4Mat(pOSurface, fourByFour)
    mult_matrix, matrix_decompose = python_utils.constrainByMatrix(fourByFour + '.output', par_group, False, False, ['rotate', 'translate'])
    cmds.matchTransform(pos_group, par_group)
    if secondaryTransform:
        pOSurface = cmds.createNode('pointOnSurfaceInfo', name=rough_joint.replace('CTL_JNT', 'DEF_POSI'))
        cmds.connectAttr('{0}.outputSurface'.format(rebuildSurface), '{0}.inputSurface'.format(pOSurface))
        cmds.setAttr('{0}.parameterU'.format(pOSurface), realU)
        cmds.setAttr('{0}.parameterV'.format(pOSurface), closestV)
        fourByFour = cmds.createNode('fourByFourMatrix', name=pos_group.replace('PLC_GRP', 'DEF_4X4'))
        python_utils.hookUpPointOnSurfaceTo4x4Mat(pOSurface, fourByFour)
        mult_matrix, matrix_decompose = python_utils.constrainByMatrix(fourByFour + '.output', par_group_1, False, False, ['rotate', 'translate'])
        cmds.matchTransform(pos_group, par_group_1)
    jointList.append({'joint': rough_joint, 'parentGroup': par_group, 'secondaryParGroup': par_group_1, 'positionGroup': pos_group})