from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class KeepOutBelt(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.joint_dict = {}
        self.joint_dict['baseJoint'] = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        if 'numKeepOutJoints' in self.componentVars:
            numKeepOutJoints = self.componentVars['numKeepOutJoints']
        else:
            numKeepOutJoints = 4

       
        self.joint_dict['keepOutJoints'] = []
        for i in range(numKeepOutJoints):
            joint_chain = {}
            joint_chain['locatorJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_{2}_measure_LOC_JNT'.format(self.prefix, self.name, i), position=(0, 0, 0))
            joint_chain['pivotJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_{2}_edge_LOC_JNT'.format(self.prefix, self.name, i), position=(0,0,0))
            joint_chain['bindJoint'] = cmds.duplicate(joint_chain['locatorJoint'], name=joint_chain['locatorJoint'].replace('LOC_JNT', 'BND_JNT'))
            cmds.parent(joint_chain['locatorJoint'], joint_chain['bindJoint'])
            self.joint_dict['keepOutJoints'].append(joint_chain)

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        keep_out_disk_group = cmds.group(name='{0}_{1}_rigid_KOD_GRP'.format(self.prefix, self.name), empty=True, parent=self.baseGroups['placement_group'])
        base_control_joint = cmds.duplicate(self.joint_dict['baseJoint'], name=self.joint_dict['baseJoint'].replace('BND', 'CTL'), parentOnly=True)[0]
        cmds.matchTransform(keep_out_disk_group, base_control_joint)
        center_group = cmds.group(name=base_control_joint.replace('CTL_JNT', 'PLC_GRP'), parent=keep_out_disk_group, empty=True)
        cmds.matchTransform(center_group, base_control_joint)
        cmds.parent(base_control_joint, center_group)
        python_utils.zeroJointOrient(base_control_joint)
        cmds.setAttr('{0}.rotate'.format(base_control_joint), 0,0,0)

        #Reparent the curve that'll act as the "edge" of the disk.
        self.kod_curve = '{0}_{1}_{2}'.format(self.prefix, self.name, self.componentVars['curveGeo'])
        self.kod_og_parent = cmds.listRelatives(self.componentVars['curveGeo'], parent=True)[0]
        cmds.parent(self.componentVars['curveGeo'], keep_out_disk_group)
        cmds.rename(self.componentVars['curveGeo'], self.kod_curve)

        # Turn the collision geometry into maya muscles so they can collide with things.
        self.collisionObjects = []
        for geo in self.componentVars['collisionGeo']:
            muscle = python_utils.createCMuscle(geo)
            self.collisionObjects.append({'geometry': geo, 'cMuscle': muscle})



        # Actually load the plugin and create the Keep Out Disk node (should I load the plugin somewhere else? Probably.)
        cmds.loadPlugin('Keep_Out_Disk.mll')
        keep_out_disk_node = cmds.createNode('keepOutDisk', name='keepOutDiskNode')

        # Everything in the plugin should act relative to the transform of the center_group
        cmds.connectAttr('{0}.matrix'.format(center_group), '{0}.center'.format(keep_out_disk_node))
        cmds.setAttr('{0}.centerWorld'.format(keep_out_disk_node), cmds.getAttr('{0}.worldMatrix[0]'.format(center_group)), type='matrix')
        # Connect up the curve
        cmds.connectAttr('{0}.local'.format(self.kod_curve), '{0}.edgeCurve'.format(keep_out_disk_node))

        joint_list = []
        idx = 0
        for joint_chain in self.joint_dict['keepOutJoints']:
            # Create the control locs for the keep out disk
            joint_chain['edgeLoc'] = python_utils.createLocAt(joint_chain['pivotJoint'], keep_out_disk_group, 'EDG')
            cmds.connectAttr('{0}.matrix'.format(joint_chain['edgeLoc']), '{0}.edgeMatrix[{1}]'.format(keep_out_disk_node, idx))

            joint_chain['measureLoc'] = python_utils.createLocAt(joint_chain['locatorJoint'], keep_out_disk_group, 'MEA')
            # Create the KeepOut groups and connect them to the collision geometry
            joint_chain['muscleKeepOut'], joint_chain['keepOutShape'], joint_chain['keepOutGroup'] = python_utils.rigForCMuscleKeepOut(joint_chain['measureLoc'], 'COLI')
            jdx = 0 
            for object in self.collisionObjects:
                cmds.connectAttr('{0}.muscleData'.format(object['cMuscle']), '{0}.muscleData[{1}]'.format(joint_chain['keepOutShape'], jdx))
                jdx += 1
            # Because of the way the keep out stuff works we have to do a matrix mult to get the moving group into the locator space
            mult_matrix = cmds.createNode('multMatrix', name='{0}_{1}_keepOut_{2}_ACNST_MMULT'.format(self.prefix, self.name, idx))
            cmds.connectAttr('{0}.worldMatrix[0]'.format(joint_chain['keepOutGroup']), '{0}.matrixIn[0]'.format(mult_matrix))
            cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(center_group), '{0}.matrixIn[1]'.format(mult_matrix))
            cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.measureMatrix[{1}]'.format(keep_out_disk_node, idx))

            # Make sure the keep out shape has it's movement vector match the center_group's "up" direction.
            center_group_transform = om2.MFnTransform(python_utils.getDagPath(center_group))
            up_vec = om2.MVector.kYaxisVector.rotateBy(center_group_transform.rotation(om2.MSpace.kWorld, asQuaternion=True))
            keepOutGroup_matrix = python_utils.getDagPath(joint_chain['keepOutGroup']).inclusiveMatrixInverse()
            up_vec = up_vec * keepOutGroup_matrix
            cmds.setAttr('{0}.inDirection'.format(joint_chain['keepOutShape']), *up_vec)

            idx += 1
        
        cmds.connectAttr('{0}.outCenterMatrix'.format(keep_out_disk_node), '{0}.offsetParentMatrix'.format(base_control_joint))

        # Set up the "bendy" motion of the belt that'll blend with the rigid KOD group
        bend_joints_group = cmds.group(name='{0}_{1}_bend_PAR_GRP'.format(self.prefix, self.name), empty=True, parent=self.baseGroups['placement_group'])
        cmds.addAttr(bend_joints_group, longName='RigidWeight', keyable=True, defaultValue=0.5, minValue=0.0, maxValue=1.0)
        cmds.addAttr(bend_joints_group, longName='BendWeight', keyable=True, defaultValue=1.0, minValue=0.0, maxValue=1.0)
        cmds.addAttr(bend_joints_group, longName='keepOutDirection', attributeType='double3', hidden=False, keyable=True)
        cmds.addAttr(bend_joints_group, longName='X', attributeType='double', parent='keepOutDirection')
        cmds.addAttr(bend_joints_group, longName='Y', attributeType='double', parent='keepOutDirection')
        cmds.addAttr(bend_joints_group, longName='Z', attributeType='double', parent='keepOutDirection', defaultValue=1.0)
        cmds.matchTransform(bend_joints_group, keep_out_disk_group)
        # We plug the output of the rigid group into the bend group using a blendMatrix so we can turn it on and off.
        rigid_mult_matrix, rigid_matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(base_control_joint), bend_joints_group, True, True, ['rotate', 'scale', 'translate', 'shear'], True, False)
        rigid_blend_matrix = cmds.createNode('blendMatrix', name='{0}_BLND_SWTCHM'.format(bend_joints_group))
        static_mult_matrix, static_matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(keep_out_disk_group), bend_joints_group, True, True, ['rotate', 'scale', 'translate', 'shear'], True, False)
        cmds.connectAttr('{0}.matrixSum'.format(static_mult_matrix), '{0}.inputMatrix'.format(rigid_blend_matrix))
        cmds.connectAttr('{0}.matrixSum'.format(rigid_mult_matrix), '{0}.target[0].targetMatrix'.format(rigid_blend_matrix))
        cmds.connectAttr('{0}.RigidWeight'.format(bend_joints_group), '{0}.target[0].weight'.format(rigid_blend_matrix))
        cmds.connectAttr('{0}.outputMatrix'.format(rigid_blend_matrix), '{0}.offsetParentMatrix'.format(bend_joints_group))
        python_utils.zeroOutLocal(bend_joints_group)
        idx = 0
        for joint_chain in self.joint_dict['keepOutJoints']:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_chain['pivotJoint'])
            joint_chain['bendJoint'] = cmds.duplicate(joint_chain['bindJoint'], name='{0}_{1}_{2}_bend_CTL_JNT'.format(prefix, component_name, idx), parentOnly=True)[0]
            joint_chain['rigidJoint'] = cmds.duplicate(joint_chain['bindJoint'], name='{0}_{1}_{2}_rigid_CTL_JNT'.format(prefix, component_name, idx), parentOnly=True)[0]
            cmds.parent(joint_chain['bendJoint'], bend_joints_group)
            cmds.parent(joint_chain['rigidJoint'], bend_joints_group)
            joint_chain['bendLoc'] = python_utils.createLocAt(joint_chain['locatorJoint'], bend_joints_group, 'bend_CTL')
            joint_chain['bendLoc'] = cmds.rename(joint_chain['bendLoc'], joint_chain['bendLoc'].replace('measure_', ''))
            cmds.matchTransform(joint_chain['bendLoc'], joint_chain['locatorJoint'])

            joint_chain['bendKeepOut'], joint_chain['bendKOShape'], joint_chain['bendKOGroup'] = python_utils.rigForCMuscleKeepOut(joint_chain['bendLoc'], 'bend_COLI')
            jdx = 0 
            for object in self.collisionObjects:
                cmds.connectAttr('{0}.muscleData'.format(object['cMuscle']), '{0}.muscleData[{1}]'.format(joint_chain['bendKOShape'], jdx))
                jdx += 1

            # The "bendJoint" will aim at the "bendLoc"'s keepOutGroup, which will be pushed outwards from the center of the belt (we assume the Z direction of the
            # "locatorJoint" points outwards from the curve of the belt)
            cmds.aimConstraint(
                joint_chain['bendKOGroup'],
                joint_chain['bendJoint'],
                aimVector=[1.0, 0.0, 0.0],
                upVector=[0.0, 0.0, 1.0],
                worldUpType='objectrotation',
                worldUpObject=bend_joints_group,
                worldUpVector=[0.0, 1.0, 0.0],
                maintainOffset=True)

            cmds.connectAttr('{0}.keepOutDirection'.format(bend_joints_group),'{0}.inDirection'.format(joint_chain['bendKOShape']))

            # Also delete all the locatorJoints 'cause we're done with them.
            cmds.delete(joint_chain['locatorJoint'])

            idx += 1

        #Set up the manual set of joints "underneath" the bendy and rigid belt motions.
        manual_joints_group = cmds.group(name='{0}_{1}_manual_PAR_GRP'.format(self.prefix, self.name), empty=True, parent=self.baseGroups['placement_group'])
        cmds.matchTransform(manual_joints_group, keep_out_disk_group)
        idx = 0
        for joint_chain in self.joint_dict['keepOutJoints']:
            joint_chain['manualJoint'] = cmds.duplicate(joint_chain['bindJoint'], name='{0}_{1}_{2}_manual_CTL_JNT'.format(self.prefix, self.name, idx), parentOnly=True)[0]
            cmds.parent(joint_chain['manualJoint'], manual_joints_group)
            # We plug the movement of the joints in the bend group here.
            rigid_mult_matrix, rigid_matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(joint_chain['rigidJoint']), joint_chain['manualJoint'], True, True, ['rotate', 'scale', 'translate', 'shear'], True, False)
            bend_mult_matrix, bend_matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(joint_chain['bendJoint']), joint_chain['manualJoint'], True, True, ['rotate', 'scale', 'translate', 'shear'], True, False)
            blend_matrix = cmds.createNode('blendMatrix', name='{0}_BLND_SWTCHM'.format(joint_chain['manualJoint']))
            cmds.connectAttr('{0}.matrixSum'.format(rigid_mult_matrix), '{0}.inputMatrix'.format(blend_matrix))
            cmds.connectAttr('{0}.matrixSum'.format(bend_mult_matrix), '{0}.target[0].targetMatrix'.format(blend_matrix))
            cmds.connectAttr('{0}.BendWeight'.format(bend_joints_group), '{0}.target[0].weight'.format(blend_matrix))
            cmds.connectAttr('{0}.outputMatrix'.format(blend_matrix), '{0}.offsetParentMatrix'.format(joint_chain['manualJoint']))
            python_utils.zeroOutLocal(joint_chain['manualJoint'])

            joint_chain['manualControlGroup'], joint_chain['manualControl'] = python_utils.makeControlMatchTransform('{0}_{1}_{2}_manual_CTL_CRV'.format(self.prefix, self.name, idx), joint_chain['manualJoint'], 1.0, "circle")
            cmds.parent(joint_chain['manualControlGroup'], joint_chain['manualJoint'])

            mult_matrix, matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(joint_chain['manualControl']), joint_chain['bindJoint'][0], False, False)
            cmds.setAttr('{0}.segmentScaleCompensate'.format(joint_chain['bindJoint'][0]), False)

            cmds.addAttr(joint_chain['manualControl'], longName='RigidWeight', proxy='{0}.RigidWeight'.format(bend_joints_group))
            cmds.addAttr(joint_chain['manualControl'], longName='BendWeight', proxy='{0}.BendWeight'.format(bend_joints_group))

            idx += 1
            
        rigid_mult_matrix, rigid_matrix_decompose = python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(bend_joints_group), self.joint_dict['baseJoint'], False, False, ['rotate', 'scale', 'translate', 'shear'], True, True)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return
    
    def destroy(self):
        if self.kod_curve:
            cmds.rename(self.kod_curve, self.componentVars['curveGeo'])
            cmds.parent(self.componentVars['curveGeo'], self.kod_og_parent)