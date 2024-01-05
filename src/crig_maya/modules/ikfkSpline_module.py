from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.OpenMaya as om

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
        ik_msc = cmds.group(name='{0}_{1}_ikmsc_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        ik_clst = cmds.group(name='{0}_{1}_clst_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        ik_ctl = cmds.group(name='{0}_{1}_ctl_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        cmds.inheritTransform(ik_msc, off=True)
        parent = ik_group

        # All objects that have a 1:1 relationship with the joints are stored here in an array of dicts:
        # {
        #   'ik_joint': <name of ik joint>
        #   'ik_joint_place_group': <name of base ik joint place group>
        #   'ik_rough_joint': <name of the joint driven by the rough ik curve>
        #   'ik_twist_joint': <name of the joint that takes in the twist data from the ik_control>
        #   'cluster': [<name of cluster>, <name of cluster handle>]
        #   'ik_control': <name of base ik control>
        #   'ik_place_group': <name of base ik control place group>
        # }
        #
        # Note: I lied above, there's a bunch of objects with a 1:1 relationship with joints that are in
        #   their own arrays.  This is because I'm too lazy to go back and refactor everything.
        joint_objects = []

        idx = 0
        for joint in self.bind_joints:
            joint_objects.append( { 'ik_joint': python_utils.duplicateBindJoint(joint, parent, 'IK') })
            parent = joint_objects[idx]['ik_joint']
            idx += 1

        #Also get joints for the rough controls
        parent = ik_group
        idx = 0
        for joint in self.bind_joints:
            joint_objects[idx]['ik_rough_joint'] = python_utils.duplicateBindJoint(joint, parent, 'rough_IK')
            parent = joint_objects[idx]['ik_rough_joint']
            idx += 1

        # Also also get joints to carry the twist rotation (and since we're here go ahead and attach the base ik world space to the offset parent matrix)
        # TODO: Figure out how to connect the rough controls twist to the fine controls twist, probably with a color blend.
        ik_rough_group = cmds.group(name='{0}_{1}_ik_twist_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        parent = ik_rough_group
        idx = 0
        for joint in self.bind_joints:
            joint_objects[idx]['ik_twist_joint'] = python_utils.duplicateBindJoint(joint, parent, 'twist_IK')
            cmds.setAttr('{0}.translate'.format(joint_objects[idx]['ik_twist_joint']), 0,0,0)
            cmds.makeIdentity(joint_objects[idx]['ik_twist_joint'])
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_objects[idx]['ik_twist_joint'])
            position_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'), empty=True)
            cmds.matchTransform(position_group, joint_objects[idx]['ik_twist_joint'])
            cmds.parent(position_group, ik_rough_group)
            cmds.parent(joint_objects[idx]['ik_twist_joint'], position_group)
            python_utils.constrainTransformByMatrix(joint_objects[idx]['ik_joint'], position_group, False, False)
            idx += 1

        #parent = ik_group
        #for object in joint_objects:
            #prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['ik_joint'])
            #position_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PLC', 'GRP'), empty=True)
            #cmds.matchTransform(position_group, object['ik_joint'])
            #cmds.parent(position_group, parent)
            #cmds.parent(object['ik_joint'], parent)
            #parent = object['ik_joint']
            #object['ik_joint_place_group'] = position_group
        
        ik_handle, ik_effector, ik_curve = cmds.ikHandle(name='{0}_{1}_base_IKS_HDL'.format(self.prefix, self.name),
                                                        startJoint=joint_objects[0]['ik_joint'],
                                                        endEffector=joint_objects[-1]['ik_joint'],
                                                        solver='ikSplineSolver',
                                                        simplifyCurve=False)
        
        ik_effector = cmds.rename(ik_effector, '{0}_{1}_base_IKS_EFF'.format(self.prefix, self.name))
        ik_curve = cmds.rename(ik_curve, '{0}_{1}_base_IKS_CRV'.format(self.prefix, self.name))
        cmds.parent(ik_curve, ik_msc)
        cmds.parent(ik_handle, ik_msc)
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(ik_curve)

        curve_shape = cmds.listRelatives(ik_curve, children=True, shapes=True)[0]
        curve_info = cmds.shadingNode('curveInfo', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'SAS_CINFO'), asUtility=True)
        cmds.connectAttr('{0}.worldSpace[0]'.format(curve_shape), '{0}.inputCurve'.format(curve_info))

        # Create duplicate curve that serves as a baseline, it will not be controlled by any clusters or anything, it's job is just to
        # Be transformed by anything upstream of the current component.
        ik_baseline_curve = cmds.duplicate(ik_curve)
        ik_baseline_curve = cmds.rename(ik_baseline_curve, '{0}_{1}_standard_IKS_CRV'.format(self.prefix, self.name))
        cmds.parent(ik_baseline_curve, ik_group)

        baseline_curve_info = cmds.shadingNode('curveInfo', name='{0}_{1}_{2}'.format(self.prefix, self.name, 'standard_SAS_CINFO'), asUtility=True)
        baseline_curve_shape = cmds.listRelatives(ik_baseline_curve, shapes=True)[0]
        cmds.connectAttr('{0}.worldSpace[0]'.format(baseline_curve_shape), '{0}.inputCurve'.format(baseline_curve_info))


        # Attach control clusters to each of the curve CVs
        curve_cvs = cmds.ls('{0}.cv[:]'.format(ik_curve), fl=True)
        #The first two and last two cvs we cluster together since they control the ends.
        cluster = cmds.cluster('{0}.cv[0:1]'.format(ik_curve), name='{0}_{1}_{2}_cv0_1_CTL_CLST'.format(self.prefix, self.name, joint_name))
        prefix, component_name, cluster_name, node_purpose, node_type = python_utils.getNodeNameParts(cluster[1])
        position_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PLC', 'GRP'), empty=True)
        parent_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PAR', 'GRP'), empty=True)
        cmds.matchTransform(position_group, cluster[1])
        cmds.matchTransform(parent_group, cluster[1])
        cmds.parent(position_group, ik_clst)
        cmds.parent(parent_group, position_group)
        cmds.parent(cluster[1], parent_group)
        joint_objects[0]['cluster'] = cluster
        cvnum = 2
        for cv in range(2, len(curve_cvs) - 2):
            cluster = cmds.cluster(curve_cvs[cv], name='{0}_{1}_{2}_cv{3}_CTL_CLST'.format(self.prefix, self.name, joint_name, cvnum))
            prefix, component_name, cluster_name, node_purpose, node_type = python_utils.getNodeNameParts(cluster[1])
            position_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PLC', 'GRP'), empty=True)
            parent_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PAR', 'GRP'), empty=True)
            cmds.matchTransform(position_group, cluster[1])
            cmds.matchTransform(parent_group, cluster[1])
            cmds.parent(position_group, ik_clst)
            cmds.parent(parent_group, position_group)
            cmds.parent(cluster[1], parent_group)
            joint_objects[cvnum-1]['cluster'] = cluster
            cvnum += 1

        cluster = cmds.cluster('{0}.cv[{1}:]'.format(ik_curve, len(curve_cvs)-2),
                               name='{0}_{1}_{2}_cv{3}_{4}_CTL_CLST'.format(self.prefix, self.name, joint_name, len(curve_cvs)-2, len(curve_cvs)-1))
        prefix, component_name, cluster_name, node_purpose, node_type = python_utils.getNodeNameParts(cluster[1])
        position_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PLC', 'GRP'), empty=True)
        parent_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, cluster_name, 'PAR', 'GRP'), empty=True)
        cmds.matchTransform(position_group, cluster[1])
        cmds.matchTransform(parent_group, cluster[1])
        cmds.parent(position_group, ik_clst)
        cmds.parent(parent_group, position_group)
        cmds.parent(cluster[1], parent_group)
        joint_objects[-1]['cluster'] = cluster
        
        # Add base level controls
        for object in joint_objects:
            cluster = object['cluster']
            parent = cmds.listRelatives(cluster[1], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['ik_joint'])
            control_place_group, cluster_control, mult_matrix, matrix_compose = python_utils.makeConstraintControl(
                                                        '{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'IK', 'CTL', 'CRV'),
                                                        ik_ctl,
                                                        parent,
                                                        1.0,
                                                        'circle',
                                                        object['ik_joint'])
            #Connect control Y rotate to twist joint
            mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(cluster_control, object['ik_twist_joint'], True, False)
            cmds.disconnectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(object['ik_twist_joint']))
            cmds.disconnectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(object['ik_twist_joint']))
            cmds.disconnectAttr('{0}.outputShear'.format(matrix_decompose), '{0}.shear'.format(object['ik_twist_joint']))
            cmds.disconnectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(object['ik_twist_joint']))
            cmds.connectAttr('{0}.outputRotateY'.format(matrix_decompose), '{0}.rotateY'.format(object['ik_twist_joint']))
            object['ik_control'] = cluster_control
            object['ik_place_group'] = control_place_group

        # Scale the joints with the length of the curve/implement squash and stretch.
        # This should be the same as the FK squash and stretch (see below), but the length value is determined by the
        # length of the curve rather than a length attribute at the control.
        self.create_ik_math_nodes(curve_info, baseline_curve_info, joint_objects, 'ik_joint')

        #TODO: create secondary/tertiary ik curves/controls for more convenient handling.
        #Bind rough joint chain to new control curve
        ik_rough_handle, ik_rough_effector, ik_rough_curve = cmds.ikHandle(name='{0}_{1}_rough_IKS_HDL'.format(self.prefix, self.name),
                                                        startJoint=joint_objects[0]['ik_rough_joint'],
                                                        endEffector=joint_objects[-1]['ik_rough_joint'],
                                                        solver='ikSplineSolver',
                                                        simplifyCurve=False,
                                                        )
        # This curve should be the same as the fine curve because the joints are in the same place (hopefully!)
        ik_rough_curve = cmds.rename(ik_rough_curve, '{0}_{1}_rough_IKS_CRV'.format(self.prefix, self.name))
        
        cmds.parent(ik_rough_curve, ik_msc)
        cmds.parent(ik_rough_handle, ik_msc)
        
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(ik_rough_curve)
        
        rough_curve_info = cmds.shadingNode('curveInfo', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'SAS_CINFO'), asUtility=True)
        rough_curve_shape = cmds.listRelatives(ik_rough_curve, shapes=True)[0]
        cmds.connectAttr('{0}.worldSpace[0]'.format(rough_curve_shape), '{0}.inputCurve'.format(rough_curve_info))

        self.create_ik_math_nodes(rough_curve_info, baseline_curve_info, joint_objects, 'ik_rough_joint')

        #Put new group on top of the fine controls that's driven by the new joint
        for object in joint_objects:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['ik_control'])
            base_control_parent = cmds.listRelatives(object['ik_control'], parent=True)[0]
            new_parent_group = cmds.group(name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PAR', 'GRP'), empty=True)
            cmds.matchTransform(new_parent_group, object['ik_control'])
            cmds.parent(new_parent_group, base_control_parent)
            cmds.parent(object['ik_control'], new_parent_group)
            python_utils.constrainByMatrix('{0}.worldMatrix[0]'.format(object['ik_rough_joint']), new_parent_group, False)

        #Create joints for each rough control (3 by default probably) and skin them to the rough curve
        #TODO: change this section so there can be any number of rough controls.
        ik_rough_control_joints = []
        idx = 0
        ik_rough_group = cmds.group(name='{0}_{1}_ik_rough_HOLD_GRP'.format(self.prefix, self.name), parent=ik_group, empty=True)
        base_rough_control_joint = python_utils.duplicateBindJoint(joint_objects[0]['ik_rough_joint'], ik_rough_group, 'CTL')
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(base_rough_control_joint)
        ik_rough_control_joints.append(base_rough_control_joint)
        base_joint_DAG = python_utils.getDagPath(base_rough_control_joint)
        transformFuncs = om.MFnTransform()
        transformFuncs.setObject(base_joint_DAG)
        base_joint_vec = transformFuncs.translation(om.MSpace.kWorld)
        end_rough_control_joint = python_utils.duplicateBindJoint(joint_objects[-1]['ik_rough_joint'], ik_rough_group, 'CTL')
        start_to_end_vec = python_utils.getTransformDiffVec(end_rough_control_joint, base_rough_control_joint)
        num_segments = 2
        segment_vec = start_to_end_vec / num_segments
        for seg_num in range(num_segments - 1):
            new_transform_vec = base_joint_vec + (segment_vec * (seg_num + 1))
            new_rough_control_joint = cmds.joint(
                ik_rough_group,
                name='{0}_{1}_{2}_{3}_{4}_JNT'.format(prefix, component_name, seg_num + 1, 'rough', node_purpose),
                position=(new_transform_vec.x, new_transform_vec.y, new_transform_vec.z),
                scaleCompensate=False
                )
            ik_rough_control_joints.append(new_rough_control_joint)
        ik_rough_control_joints.append(end_rough_control_joint)
        cmds.skinCluster(ik_rough_control_joints, ik_rough_curve, toSelectedBones=True, bindMethod=0, maximumInfluences=2, obeyMaxInfluences=True, dropoffRate=7)

        parent = joint_objects[idx]['ik_rough_joint']

        #Create rough controls (3 by default probably) and constrain the rough joints to them
        ik_rough_controls = []
        for joint in ik_rough_control_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint)
            control_place_group, rough_control, mult_matrix, matrix_compose = python_utils.makeConstraintControl(
                                                            '{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'CTL', 'CRV'),
                                                            ik_ctl,
                                                            joint,
                                                            1.5,
                                                            'circle',
                                                            joint,
                                                            False,
                                                            False)
            ik_rough_controls.append(rough_control)
            
        #Add rough control twist to the fine controls, blending based on the dot product
        rough_idx = 0
        prev_rough_control = ik_rough_controls[rough_idx]
        next_rough_control = ik_rough_controls[rough_idx + 1]
        for joint in joint_objects:
            #Get the fine control's distance from the two rough controls bracketing it
            rough_diff_vec = python_utils.getTransformDiffVec(prev_rough_control, next_rough_control)
            base_diff_vec = python_utils.getTransformDiffVec(prev_rough_control, joint['ik_control'])
            dot = rough_diff_vec * base_diff_vec
            percent_along_rough_vec = dot/(rough_diff_vec.length() * rough_diff_vec.length())
            #If we're past the next rough control, grab the next one and recalculate the vectors
            if percent_along_rough_vec > 1:
                rough_idx += 1
                #...unless we're at the end of the rough controls for some reason, in which case we just 
                if rough_idx >= len(ik_rough_controls) - 1:
                    percent_along_rough_vec = 1
                else:
                    prev_rough_control = ik_rough_controls[rough_idx]
                    next_rough_control = ik_rough_controls[rough_idx + 1]
                    rough_diff_vec = python_utils.getTransformDiffVec(prev_rough_control, next_rough_control)
                    base_diff_vec = python_utils.getTransformDiffVec(prev_rough_control, joint['ik_control'])
                    dot = rough_diff_vec * base_diff_vec
                    percent_along_rough_vec = dot/(rough_diff_vec.length() * rough_diff_vec.length())
                    if percent_along_rough_vec < 0:
                        percent_along_rough_vec = 0

            #Create a new parent group for the fine control and connect the rough controls to it's Y rotation with a color blend.
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint['ik_control'])
            new_rot_group = cmds.group(joint['ik_control'], name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'rotY', 'PAR', 'GRP'))
            cmds.matchTransform(new_rot_group, joint['ik_control'], piv=True)
            blend_node = python_utils.createScalarBlend(
                '{0}.rotateY'.format(prev_rough_control),
                '{0}.rotateY'.format(next_rough_control),
                '{0}.rotateY'.format(new_rot_group),
                1 - percent_along_rough_vec
            )


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

        # Connect ik/fk joints to bind joints and controls, except the last bind joint, that is attached to the rough control joint because I can't think
        # of a better way to control the rotation of the final joint in the spine (having it just follow the ik doesn't seem intuitive).
        for idx in range(len(self.bind_joints)):
            if idx < len(self.bind_joints) - 1:
                blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(joint_objects[idx]['ik_twist_joint'], fk_joints[idx], self.bind_joints[idx])
            else:
                blend_matrix, mult_matrix, matrix_decompose = python_utils.createMatrixSwitch(ik_rough_control_joints[-1], fk_joints[idx], self.bind_joints[idx])
            cmds.connectAttr('{0}.ikfkswitch'.format(data_locator), '{0}.target[0].weight'.format(blend_matrix))
            cmds.setDrivenKeyframe('{0}.visibility'.format(joint_objects[idx]['ik_control']), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=1)
            cmds.setDrivenKeyframe('{0}.visibility'.format(joint_objects[idx]['ik_control']), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=0)
            cmds.setDrivenKeyframe('{0}.visibility'.format(fk_base_controls[idx]), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=0)
            cmds.setDrivenKeyframe('{0}.visibility'.format(fk_base_controls[idx]), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=1)

        for control in ik_rough_controls:
            cmds.setDrivenKeyframe('{0}.visibility'.format(control), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=1)
            cmds.setDrivenKeyframe('{0}.visibility'.format(control), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=0)

        for control in fk_rough_controls_1:
            cmds.setDrivenKeyframe('{0}.visibility'.format(control), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=0, value=0)
            cmds.setDrivenKeyframe('{0}.visibility'.format(control), currentDriver='{0}.ikfkswitch'.format(data_locator), driverValue=1, value=1)


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        # Copy inv world space to placement_GRP to keep the offset around.
        python_utils.copyOverMatrix('{0}.parentinvspace'.format(data_locator), self.baseGroups['placement_group'])
        
        return
    
    def create_ik_math_nodes(self, curve_info, baseline_curve_info, joint_objects, chain_key):
        # Scale the joints with the length of the curve/implement squash and stretch.
        # This should be the same as the FK squash and stretch (see below), but the length value is determined by the
        # length of the curve rather than a length attribute at the control.
        for i in range(len(joint_objects)):
            # Create squash and stretch parent group
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_objects[i]['ik_control'])
            #new_sas_group = cmds.group(joint_objects[i]['ik_joint'], name='{0}_{1}_{2}_{3}_{4}_{5}'.format(prefix, component_name, joint_name, 'SAS', 'PAR', 'GRP'))
            #cmds.matchTransform(new_sas_group, joint_objects[i]['ik_joint'], piv=True)

            # Add length and scale factor attributes to the FK control.
            currentControl = joint_objects[i]['ik_control']
            cmds.select(currentControl)
            try:
                cmds.addAttr(longName='ScaleA', attributeType='float', defaultValue=1.0, hidden=False, keyable=True)
            except:
                constants.RIGGER_LOG.info('control curve already has ScaleA attribute, skipping.')
            
            try:
                cmds.addAttr(longName='ScaleB', attributeType='float', defaultValue=1.0, hidden=False, keyable=True)
            except:
                constants.RIGGER_LOG.info('control curve already has ScaleB attribute, skipping.')

            # Get starting distances between joints.
            currentJoint = joint_objects[i][chain_key]
            distance1 = 0
            if i > 0:
                previousJoint = joint_objects[i - 1][chain_key]
                distance1 = python_utils.getTransformDistance(currentJoint, previousJoint)
            distance2 = 0
            if i < len(joint_objects) - 1:
                nextJoint = joint_objects[i + 1][chain_key]
                distance2 = python_utils.getTransformDistance(currentJoint, nextJoint)

            totalDistance = distance1 + distance2
            # Divide starting arc_length by current arc_length to get the Length value that hooks into the rest of
            # the squash and stretch math (again, see FK section for more details)
            normalizeLength = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '9_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(normalizeLength), 3)
            cmds.connectAttr('{0}.arcLength'.format(curve_info), '{0}.floatA'.format(normalizeLength))
            cmds.connectAttr('{0}.arcLength'.format(baseline_curve_info), '{0}.floatB'.format(normalizeLength))

            # Start makin' math nodes babey
            scaleMultNode = cmds.shadingNode('colorMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '1_SAS_CMATH'), asUtility=True)
            cmds.setAttr('{0}.operation'.format(scaleMultNode), 2)
            cmds.connectAttr('{0}.outFloat'.format(normalizeLength), '{0}.colorAR'.format(scaleMultNode))
            cmds.connectAttr('{0}.outFloat'.format(normalizeLength), '{0}.colorAG'.format(scaleMultNode))
            cmds.connectAttr('{0}.outFloat'.format(normalizeLength), '{0}.colorAB'.format(scaleMultNode))
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

            # Get current joint translate and add it to the Y displacement so we don't override it's current position because we can't use a placement group to layer
            # the initial transform because it breaks Maya's spline IK system for some reason.
            addStartingTranslateNode = cmds.shadingNode('colorMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, '4_SAS_CMATH'), asUtility=True)
            translateX = cmds.getAttr('{0}.translateX'.format(joint_objects[i][chain_key]))
            translateY = cmds.getAttr('{0}.translateY'.format(joint_objects[i][chain_key]))
            translateZ = cmds.getAttr('{0}.translateZ'.format(joint_objects[i][chain_key]))
            cmds.setAttr('{0}.operation'.format(addStartingTranslateNode), 0)
            cmds.setAttr('{0}.colorAR'.format(addStartingTranslateNode), translateX)
            cmds.setAttr('{0}.colorAG'.format(addStartingTranslateNode), translateY)
            cmds.setAttr('{0}.colorAB'.format(addStartingTranslateNode), translateZ)
            cmds.connectAttr('{0}.outColorR'.format(multByScaleFactorNode), '{0}.colorBG'.format(addStartingTranslateNode))

            # Finally Connect the initial position plus the Y displacement to the joint translate.
            cmds.connectAttr('{0}.outColorR'.format(addStartingTranslateNode), '{0}.translateX'.format(joint_objects[i][chain_key]))
            cmds.connectAttr('{0}.outColorG'.format(addStartingTranslateNode), '{0}.translateY'.format(joint_objects[i][chain_key]))
            cmds.connectAttr('{0}.outColorB'.format(addStartingTranslateNode), '{0}.translateZ'.format(joint_objects[i][chain_key]))

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