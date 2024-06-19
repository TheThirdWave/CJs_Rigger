from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class EyebrowsModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.joint_dict = {
            'baseJoint' : '',
            'bindJoints': []
        }

        if 'numJoints' in self.componentVars:
            num_joints = self.componentVars['numJoints']
        else:
            num_joints = 1

        self.joint_dict['baseJoint'] = cmds.group(name='{0}_{1}_base_PAR_GRP'.format(self.prefix, self.name), parent=self.baseGroups['deform_group'], empty=True)
        for i in range(num_joints):
            self.joint_dict['bindJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_base_{2}_BND_JNT'.format(self.prefix, self.name, i), position=(0, 0, 0)))

        self.inner_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_inner_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.middle_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_middle_PLC_JNT'.format(self.prefix, self.name), position=(1, 0, 0))
        self.outer_control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_outer_PLC_JNT'.format(self.prefix, self.name), position=(2, 0, 0))


    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return
        
        # Create user controls at placement joints.
        inner_place_group, inner_control = python_utils.replaceJointWithControl(self.inner_control_place_joint, 'inner', self.baseGroups['placement_group'])
        middle_place_group, middle_control = python_utils.replaceJointWithControl(self.middle_control_place_joint, 'middle', self.baseGroups['placement_group'])
        outer_place_group, outer_control = python_utils.replaceJointWithControl(self.outer_control_place_joint, 'outer', self.baseGroups['placement_group'])

        logic_group = '{0}_{1}_logic_PAR_GRP'.format(self.prefix, self.name)
        cmds.group(name=logic_group, parent=self.baseGroups['placement_group'], empty=True)
        cmds.inheritTransform(logic_group, off=True)

        base_objects = [ {'joint': x} for x in self.joint_dict['bindJoints'] ]

        # Create the dense curve
        for object in base_objects:
            object['jointPosition'] = cmds.xform(object['joint'], query=True, worldSpace=True, translation=True)
        dense_curve = cmds.curve(name='{0}_{1}_base_DEF_CRV'.format(self.prefix, self.name), point=[x['jointPosition'] for x in base_objects], degree=1)
        cmds.parent(dense_curve, logic_group)

        # Next, attach the joints to the curve using pointOnCurveInfo nodes.
        for object in base_objects:
            closestPoint, closestParam = python_utils.getClosestPointOnCurve(object['joint'], dense_curve)
            pointOnCurve = cmds.createNode('pointOnCurveInfo', name=object['joint'].replace('BND_JNT', 'CTL_POCI'))
            cmds.connectAttr('{0}.worldSpace'.format(dense_curve), '{0}.inputCurve'.format(pointOnCurve))
            cmds.setAttr('{0}.parameter'.format(pointOnCurve), closestParam)
            cmds.connectAttr('{0}.position'.format(pointOnCurve), '{0}.translate'.format(object['joint']))

        # Create the rough curve and use it to drive the original with a wire deformer
        rough_curve = cmds.duplicate(dense_curve, name='{0}_{1}_rough_DEF_CRV'.format(self.prefix, self.name))[0]
        cmds.rebuildCurve(rough_curve, constructionHistory=False, degree=3, spans=4, keepTangents=False)
        cmds.wire(dense_curve, wire=rough_curve, name='{0}_{1}_base_DEF_WIRD'.format(self.prefix, self.name))

        # Create controls/joints for rough curve
        num_controls = 3
        control_percent = 1.0 / (num_controls - 1)
        rough_joints = []
        user_controls_place = [inner_place_group, middle_place_group, outer_place_group]
        user_controls = [inner_control, middle_control, outer_control]
        for idx in range(num_controls):
            pointOnCurve = python_utils.getPointAlongCurve((control_percent * idx), rough_curve)
            rough_joint = cmds.joint(logic_group, name='{0}_{1}_rough_{2}_CTL_JNT'.format(self.prefix, self.name, idx), position=[pointOnCurve.x, pointOnCurve.y, pointOnCurve.z])
            pos_group = cmds.group(name='{0}_{1}_rough_control_{2}_PLC_GRP'.format(self.prefix, self.name, idx), parent=logic_group, empty=True)
            cmds.matchTransform(pos_group, rough_joint)
            cmds.parent(rough_joint, pos_group)

            control_rotate = cmds.getAttr('{0}.rotate'.format(user_controls_place[idx]))[0]
            control_scale = cmds.getAttr('{0}.scale'.format(user_controls_place[idx]))[0]
            cmds.setAttr('{0}.rotate'.format(pos_group), *control_rotate)
            cmds.setAttr('{0}.scale'.format(pos_group), *control_scale)
            rough_joints.append(rough_joint)

            cmds.connectAttr('{0}.translate'.format(user_controls[idx]), '{0}.translate'.format(rough_joint))
            cmds.connectAttr('{0}.rotate'.format(user_controls[idx]), '{0}.rotate'.format(rough_joint))
            cmds.connectAttr('{0}.scale'.format(user_controls[idx]), '{0}.scale'.format(rough_joint))


        # Then skin the rough joints to the rough curve.
        cmds.skinCluster(rough_joints, rough_curve, toSelectedBones=False, bindMethod=0, maximumInfluences=2, obeyMaxInfluences=True, dropoffRate=7, name='{0}_{1}_rough_CTL_SCST'.format(self.prefix, self.name))


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return