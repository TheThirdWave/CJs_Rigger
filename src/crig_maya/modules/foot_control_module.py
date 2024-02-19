from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class FootControlModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.ankle_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_ankle_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.ball_joint = cmds.joint(self.ankle_joint, name='{0}_{1}_ball_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        self.toe_joint = cmds.joint(self.ball_joint, name='{0}_{1}_toe_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)
        self.heel_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_heel_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.outer_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_outer_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.inner_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_inner_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

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

        # Duplicate the FK joints.
        fk_joints = python_utils.duplicateBindChain(self.ankle_joint, fk_group, 'FK')

        # Now we make the ik joints by duplicating the fk group
        ik_group = cmds.duplicate(fk_group, name=fk_group.replace('fk', 'ik'))[0]
        ik_group_children = cmds.listRelatives(ik_group, type='joint', allDescendents=True, fullPath=True)
        for child in ik_group_children:
            short_name = child.split('|')[-1]
            cmds.rename(child, short_name.replace('FK', 'IK'))
        ik_joints = []
        for joint in fk_joints:
            ik_joints.append(joint.replace('FK', 'IK'))

        # Now we create the controls
        # We're using the parent ikfklimb end control as the ankle control, so we don't need
        # to create that here.
        # Which means that for the FK, I think we literally just need a control for the ball joint.
        fk_ball_placement, fk_ball_control = python_utils.makeDirectControl('{0}_{1}_ball_CTL_CRV'.format(self.prefix, self.name), fk_joints[1], 2, "square")
        #cmds.parent(fk_ball_placement, fk_joints[0])

        # For the IK controls it gets more complicated.
        ik_control_group = cmds.group(name='{0}_{1}_ik_ctls_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        ankle_joint_locator = python_utils.createLocAt(ik_joints[0], ik_control_group, 'IK')
        heel_locator = python_utils.createLocAt(self.heel_place_joint, ankle_joint_locator, 'IK')
        cmds.delete(self.heel_place_joint)
        outer_locator = python_utils.createLocAt(self.outer_place_joint, heel_locator, 'IK')
        cmds.delete(self.outer_place_joint)
        inner_locator = python_utils.createLocAt(self.inner_place_joint, outer_locator, 'IK')
        cmds.delete(self.inner_place_joint)
        toe_locator = python_utils.createLocAt(ik_joints[2], inner_locator, 'IK')
        ball_locator = python_utils.createLocAt(ik_joints[1], toe_locator, 'IK')

        # Now we create ik handles going from the ankle to the ball, and the ball to the toe
        ball_ik_handle, ball_ik_effector = cmds.ikHandle( name='{0}_{1}_ball_IKS_HDL'.format(self.prefix, self.name),
                                                startJoint=ik_joints[0],
                                                endEffector=ik_joints[1],
                                                solver='ikSCsolver' )
        ball_ik_effector = cmds.rename(ball_ik_effector, '{0}_{1}_ball_IKS_EFF'.format(self.prefix, self.name))
        # Parent ik to control.
        cmds.matchTransform(ball_ik_handle, ball_locator)
        cmds.parent(ball_ik_handle, ball_locator)

        toe_ik_handle, toe_ik_effector = cmds.ikHandle( name='{0}_{1}_toe_IKS_HDL'.format(self.prefix, self.name),
                                                startJoint=ik_joints[1],
                                                endEffector=ik_joints[2],
                                                solver='ikSCsolver' )
        toe_ik_effector = cmds.rename(toe_ik_effector, '{0}_{1}_toe_IKS_EFF'.format(self.prefix, self.name))
        # Parent ik to control.
        cmds.matchTransform(toe_ik_handle, toe_locator)

        # Then parent handle to a group underneath the ankle.
        toe_wiggle_group = cmds.group(name='{0}_{1}_toe_wiggle_PAR_GRP'.format(self.prefix, self.name), parent=toe_locator, empty=True)
        cmds.matchTransform(toe_wiggle_group, ball_locator)
        cmds.parent(toe_ik_handle, toe_wiggle_group)

        # Now we create all the attributes that control the various ik movements.
        cmds.addAttr(ball_locator, longName='footRoll', defaultValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='bendLimitAngle', defaultValue=45.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='toeStraightAngle', defaultValue=70.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='footTilt', defaultValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='ballLean', defaultValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='toeSpin', defaultValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(ball_locator, longName='toeWiggle', defaultValue=0.0, keyable=True, hidden=False)

        # First lets deal with the foot tilt 'cause it's easy, just alternate rotating the inner and outer locs
        # depending on if the value is positive or negative.
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(inner_locator)
        innerCondition = cmds.shadingNode('condition', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_CTL_COND'), asUtility=True)
        if self.prefix == 'L':
            cmds.setAttr('{0}.operation'.format(innerCondition), 2)
        else:
            cmds.setAttr('{0}.operation'.format(innerCondition), 4)
        cmds.connectAttr('{0}.footTilt'.format(ball_locator), '{0}.firstTerm'.format(innerCondition))
        cmds.setAttr('{0}.secondTerm'.format(innerCondition), 0)
        cmds.connectAttr('{0}.footTilt'.format(ball_locator), '{0}.colorIfTrueR'.format(innerCondition))
        cmds.setAttr('{0}.colorIfFalseR'.format(innerCondition), 0)
        cmds.connectAttr('{0}.outColorR'.format(innerCondition), '{0}.rotateZ'.format(inner_locator))

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(outer_locator)
        outerCondition = cmds.shadingNode('condition', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_CTL_COND'), asUtility=True)
        if self.prefix == 'L':
            cmds.setAttr('{0}.operation'.format(outerCondition), 4)
        else:
            cmds.setAttr('{0}.operation'.format(outerCondition), 2)
        cmds.connectAttr('{0}.footTilt'.format(ball_locator), '{0}.firstTerm'.format(outerCondition))
        cmds.setAttr('{0}.secondTerm'.format(outerCondition), 0)
        cmds.connectAttr('{0}.footTilt'.format(ball_locator), '{0}.colorIfTrueR'.format(outerCondition))
        cmds.setAttr('{0}.colorIfFalseR'.format(outerCondition), 0)
        cmds.connectAttr('{0}.outColorR'.format(outerCondition), '{0}.rotateZ'.format(outer_locator))

        # Ball lean, toe spin, and toe wiggle are all just direct connections.
        cmds.connectAttr('{0}.toeWiggle'.format(ball_locator), '{0}.rotateX'.format(toe_wiggle_group))
        cmds.connectAttr('{0}.toeSpin'.format(ball_locator), '{0}.rotateY'.format(toe_locator))
        cmds.connectAttr('{0}.ballLean'.format(ball_locator), '{0}.rotateZ'.format(ball_locator))

        # TODO: Get foot roll nodes set up
        # Nodes that bend the ball joint
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(ball_locator)
        ballZeroToBendPercent = cmds.shadingNode('setRange', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_0_CTL_RNG'), asUtility=True)
        cmds.setAttr('{0}.maxX'.format(ballZeroToBendPercent), 1)
        cmds.connectAttr('{0}.bendLimitAngle'.format(ball_locator), '{0}.oldMaxX'.format(ballZeroToBendPercent))
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.valueX'.format(ballZeroToBendPercent))

        # Nodes that unbend the ball joint and bend the toe joint
        ballBendToStraightPercent = cmds.shadingNode('setRange', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_1_CTL_RNG'), asUtility=True)
        cmds.setAttr('{0}.maxX'.format(ballBendToStraightPercent), 1)
        cmds.connectAttr('{0}.bendLimitAngle'.format(ball_locator), '{0}.oldMinX'.format(ballBendToStraightPercent))
        cmds.connectAttr('{0}.toeStraightAngle'.format(ball_locator), '{0}.oldMaxX'.format(ballBendToStraightPercent))
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.valueX'.format(ballBendToStraightPercent))

        toeRollMult = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_1_CTL_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(toeRollMult), 2)
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.floatA'.format(toeRollMult))
        cmds.connectAttr('{0}.outValueX'.format(ballBendToStraightPercent), '{0}.floatB'.format(toeRollMult))

        # Connect up the toe rotation
        cmds.connectAttr('{0}.outFloat'.format(toeRollMult), '{0}.rotateX'.format(toe_locator))

        invertValue = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_2_CTL_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(invertValue), 1)
        cmds.setAttr('{0}.floatA'.format(invertValue), 1)
        cmds.connectAttr('{0}.outValueX'.format(ballBendToStraightPercent), '{0}.floatB'.format(invertValue))

        bendInterpMult = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_3_CTL_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(bendInterpMult), 2)
        cmds.connectAttr('{0}.outFloat'.format(invertValue), '{0}.floatA'.format(bendInterpMult))
        cmds.connectAttr('{0}.outValueX'.format(ballZeroToBendPercent), '{0}.floatB'.format(bendInterpMult))

        ballRollMult = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'bend_4_CTL_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(ballRollMult), 2)
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.floatA'.format(ballRollMult))
        cmds.connectAttr('{0}.outFloat'.format(bendInterpMult), '{0}.floatB'.format(ballRollMult))

        # Connect up the ball rotation
        cmds.connectAttr('{0}.outFloat'.format(ballRollMult), '{0}.rotateX'.format(ball_locator))

        # Connect up the heel
        heelCondition = cmds.shadingNode('condition', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_CTL_COND'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(heelCondition), 4)
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.firstTerm'.format(heelCondition))
        cmds.setAttr('{0}.secondTerm'.format(heelCondition), 0)
        cmds.connectAttr('{0}.footRoll'.format(ball_locator), '{0}.colorIfTrueR'.format(heelCondition))
        cmds.setAttr('{0}.colorIfFalseR'.format(heelCondition), 0)
        cmds.connectAttr('{0}.outColorR'.format(heelCondition), '{0}.rotateX'.format(heel_locator))


        # Create a locator to hold the ik/fk switch attribute along with whatever else we might need later.
        cmds.select(ball_locator)
        cmds.addAttr(longName='ikfkswitch', defaultValue=0.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(ball_locator), driverValue=0, value=0)
        cmds.setDrivenKeyframe('{0}.visibility'.format(ik_group), currentDriver='{0}.ikfkswitch'.format(ball_locator), driverValue=1, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(ball_locator), driverValue=0, value=1)
        cmds.setDrivenKeyframe('{0}.visibility'.format(fk_group), currentDriver='{0}.ikfkswitch'.format(ball_locator), driverValue=1, value=0)

        # Proxy the ikfkswitch to all the controls for funsies.
        cmds.addAttr('{0}'.format(fk_ball_control), longName='ikfkswitch', proxy='{0}.ikfkswitch'.format(ball_locator))

        # Connect control to bind joint.
        blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(fk_joints[0], ik_joints[0], self.ankle_joint)
        cmds.connectAttr('{0}.ikfkswitch'.format(ball_locator), '{0}.target[0].weight'.format(blend_matrix))
        blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(fk_joints[1], ik_joints[1], self.ball_joint)
        cmds.connectAttr('{0}.ikfkswitch'.format(ball_locator), '{0}.target[0].weight'.format(blend_matrix))
        blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(fk_joints[2], ik_joints[2], self.toe_joint)
        cmds.connectAttr('{0}.ikfkswitch'.format(ball_locator), '{0}.target[0].weight'.format(blend_matrix))

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return