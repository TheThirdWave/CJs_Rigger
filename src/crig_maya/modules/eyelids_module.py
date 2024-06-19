from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds
import maya.api.OpenMaya as om2

class EyelidsModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.joint_dict = {}
        self.joint_dict['baseJoint'] = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['innerJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_inner_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.joint_dict['outerJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_outer_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        if 'numUpper' in self.componentVars:
            num_upper = self.componentVars['numUpper']
        else:
            num_upper = 0
        self.joint_dict['upperJoints'] = []
        for idx in range(num_upper):
            self.joint_dict['upperJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_upper_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        if 'numLower' in self.componentVars:
            num_lower = self.componentVars['numLower']
        else:
            num_lower = 0
        self.joint_dict['lowerJoints'] = []
        for idx in range(num_lower):
            self.joint_dict['lowerJoints'].append(cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_lower_{2}_BND_JNT'.format(self.prefix, self.name, idx), position=(0, 0, 0)))

        if 'numCorrectives' in self.componentVars:
            self.num_correctives = self.componentVars['numCorrectives']
        else:
            self.num_correctives = 0

        self.control_place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_control_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.upper_place_joint = cmds.joint(self.control_place_joint, name='{0}_{1}_upper_PLC_JNT'.format(self.prefix, self.name), position=(0, 1, 0))
        self.lower_place_joint = cmds.joint(self.control_place_joint, name='{0}_{1}_lower_PLC_JNT'.format(self.prefix, self.name), position=(0, -1, 0))


    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create a "base" joint for each lid joint.
        upper_base_joints = []
        for upper_joint in self.joint_dict['upperJoints']:
            new_base_joint = python_utils.insertJointAtParent(self.joint_dict['baseJoint'], upper_joint)
            upper_base_joints.append(new_base_joint)

        lower_base_joints = []
        for lower_joint in self.joint_dict['lowerJoints']:
            new_base_joint = python_utils.insertJointAtParent(self.joint_dict['baseJoint'], lower_joint)
            lower_base_joints.append(new_base_joint)

        outer_base_joint = python_utils.insertJointAtParent(self.joint_dict['baseJoint'], self.joint_dict['outerJoint'])
        inner_base_joint = python_utils.insertJointAtParent(self.joint_dict['baseJoint'], self.joint_dict['innerJoint'])

        logic_group = '{0}_{1}_logic_PAR_GRP'.format(self.prefix, self.name)
        upper_locators_group = '{0}_{1}_upper_locators_PAR_GRP'.format(self.prefix, self.name)
        lower_locators_group = '{0}_{1}_lower_locators_PAR_GRP'.format(self.prefix, self.name)
        user_controls_group = '{0}_{1}_user_controls_PAR_GRP'.format(self.prefix, self.name)
        cmds.group(name=logic_group, parent=self.baseGroups['placement_group'], empty=True)
        cmds.inheritTransform(logic_group, off=True)
        cmds.group(name=user_controls_group, parent=self.baseGroups['placement_group'], empty=True)
        cmds.group(name=upper_locators_group, parent=logic_group, empty=True)
        cmds.group(name=lower_locators_group, parent=logic_group, empty=True)


        upper_base_objects = [ {'parentJoint': inner_base_joint, 'joint': self.joint_dict['innerJoint']} ]
        for i in range(len(upper_base_joints)):
            upper_base_objects.append({'parentJoint': upper_base_joints[i], 'joint': self.joint_dict['upperJoints'][i]})
        upper_base_objects.append( {'parentJoint': outer_base_joint, 'joint': self.joint_dict['outerJoint']} )

        lower_base_objects = [ {'parentJoint': inner_base_joint, 'joint': self.joint_dict['innerJoint']} ]
        for i in range(len(lower_base_joints)):
            lower_base_objects.append({'parentJoint': lower_base_joints[i], 'joint': self.joint_dict['lowerJoints'][i]})
        lower_base_objects.append( {'parentJoint': outer_base_joint, 'joint': self.joint_dict['outerJoint']} )

        # duplicate the bind joints for all the middle joints to create the corrective joints
        if self.num_correctives:
            for object in upper_base_objects[1:-1] + lower_base_objects[1:-1]:
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['joint'])
                object['correctivesParentJoint'] = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_{2}_correctives_PAR_JNT'.format(self.prefix, self.name, joint_name))
                object['correctiveBaseJoint'] = []
                object['correctiveJoint'] = []
                for layer in range(self.num_correctives):
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['parentJoint'])
                    object['correctiveBaseJoint'].append(cmds.joint(object['correctivesParentJoint'], name='{0}_{1}_{2}_{3}_CRN_JNT'.format(self.prefix, self.name, joint_name, layer)))
                    cmds.matchTransform(object['correctiveBaseJoint'][layer], object['parentJoint'])
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(object['joint'])
                    object['correctiveJoint'].append(cmds.joint(object['correctiveBaseJoint'][layer], name='{0}_{1}_{2}_{3}_CRN_JNT'.format(self.prefix, self.name, joint_name, layer)))
                    cmds.matchTransform(object['correctiveJoint'][layer], object['joint'])

        inner_base_objects = {'parentJoint': inner_base_joint, 'joint': self.joint_dict['innerJoint']}
        outer_base_objects = {'parentJoint': outer_base_joint, 'joint': self.joint_dict['outerJoint']}

        # First, create the locators

        # The upper locators (including the inner and outer locators)

        for joint in upper_base_objects:
            child = cmds.listRelatives(joint['parentJoint'])[0]
            locator_place_group, locator = python_utils.createLocatorAndParent(child, upper_locators_group, 'CTL', True, False, False)
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(locator_place_group)
            if 'inner' in locator_place_group:
                locator_place_group = cmds.rename(locator_place_group, '{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name.replace('inner', 'upper_in')))
                locator = cmds.rename(locator, locator.replace('inner', 'upper_in'))
            elif 'outer' in locator_place_group:
                locator_place_group = cmds.rename(locator_place_group, '{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name.replace('outer', 'upper_out')))
                locator = cmds.rename(locator, locator.replace('outer', 'upper_out'))
            joint['staticLocator'] = cmds.duplicate(locator, name=locator.replace('CTL', 'static_CTL'))[0]
            cmds.parent(joint['staticLocator'], upper_locators_group)
            cmds.orientConstraint(locator, child,  maintainOffset=True)
            joint['locatorGroup'] = locator_place_group
            joint['locator'] = locator

        # The lower locators (including locs on the "inner" and "outer" joints

        for joint in lower_base_objects:
            child = cmds.listRelatives(joint['parentJoint'])[0]
            locator_place_group, locator = python_utils.createLocatorAndParent(child, lower_locators_group, 'CTL', True, False, False)
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(locator_place_group)
            if 'inner' in locator_place_group:
                locator_place_group = cmds.rename(locator_place_group, '{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name.replace('inner', 'lower_in')))
                locator = cmds.rename(locator, locator.replace('inner', 'lower_in'))
            elif 'outer' in locator_place_group:
                locator_place_group = cmds.rename(locator_place_group, '{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name.replace('outer', 'lower_out')))
                locator = cmds.rename(locator, locator.replace('outer', 'lower_out'))
            joint['staticLocator'] = cmds.duplicate(locator, name=locator.replace('CTL', 'static_CTL'))[0]
            cmds.parent(joint['staticLocator'], lower_locators_group)
            cmds.orientConstraint(locator, child,  maintainOffset=True)
            joint['locatorGroup'] = locator_place_group
            joint['locator'] = locator

        # Inner and Outer locators
        child = cmds.listRelatives(inner_base_objects['parentJoint'])[0]
        inner_locator_place_group, locator = python_utils.createLocatorAndParent(child, logic_group, 'CTL', True, False, False)
        inner_base_objects['locatorGroup'] = inner_locator_place_group
        inner_base_objects['locator'] = locator
        child = cmds.listRelatives(outer_base_objects['parentJoint'])[0]
        outer_locator_place_group, locator = python_utils.createLocatorAndParent(child, logic_group, 'CTL', True, False, False)
        outer_base_objects['locatorGroup'] = outer_locator_place_group
        outer_base_objects['locator'] = locator

        # Create the aim constraints making each "parent" joint look at each locator
        for object in upper_base_objects:
            cmds.aimConstraint(object['locator'], object['parentJoint'], aimVector=[0.0, 1.0, 0.0] , upVector=[0.0, 0.0, 1.0], worldUpType='scene', maintainOffset=True)

        for object in lower_base_objects:
            cmds.aimConstraint(object['locator'], object['parentJoint'], aimVector=[0.0, 1.0, 0.0] , upVector=[0.0, 0.0, 1.0], worldUpType='scene', maintainOffset=True)

        # Create aim constraints for the corrective joints, split between the original locator position (the locator group) and the locator
        if self.num_correctives:
            for object in upper_base_objects[1:-1] + lower_base_objects[1:-1]:
                for layer in range(self.num_correctives):
                    weight = (1.0/(self.num_correctives + 1)) * (layer + 1)
                    aim_constraint = cmds.aimConstraint(object['locator'], object['staticLocator'], object['correctiveBaseJoint'][layer], aimVector=[0.0, 1.0, 0.0] , upVector=[0.0, 0.0, 1.0], worldUpType='scene', maintainOffset=True)[0]
                    cmds.setAttr('{0}.{1}W0'.format(aim_constraint, object['locator']), weight)
                    cmds.setAttr('{0}.{1}W1'.format(aim_constraint, object['staticLocator']), (1 - weight))


        # Then, create the dense curves
        for object in upper_base_objects:
            object['locatorPosition'] = cmds.xform(object['locator'], query=True, worldSpace=True, translation=True)
        upper_curve = cmds.curve(name='{0}_{1}_upper_base_DEF_CRV'.format(self.prefix, self.name), point=[x['locatorPosition'] for x in upper_base_objects], degree=1)
        cmds.parent(upper_curve, logic_group)

        for object in lower_base_objects:
            object['locatorPosition'] = cmds.xform(object['locator'], query=True, worldSpace=True, translation=True)
        lower_curve = cmds.curve(name='{0}_{1}_lower_base_DEF_CRV'.format(self.prefix, self.name), point=[x['locatorPosition'] for x in lower_base_objects], degree=1)
        cmds.parent(lower_curve, logic_group)

        # Next, attach the locators to the curve using pointOnCurveInfo nodes.
        for object in upper_base_objects:
            closestPoint, closestParam = python_utils.getClosestPointOnCurve(object['locator'], upper_curve)
            pointOnCurve = cmds.createNode('pointOnCurveInfo', name=object['locator'].replace('CTL_LOC', 'CTL_POCI'))
            cmds.connectAttr('{0}.worldSpace'.format(upper_curve), '{0}.inputCurve'.format(pointOnCurve))
            cmds.setAttr('{0}.parameter'.format(pointOnCurve), closestParam)
            cmds.connectAttr('{0}.position'.format(pointOnCurve), '{0}.translate'.format(object['locatorGroup']))

        for object in lower_base_objects:
            closestPoint, closestParam = python_utils.getClosestPointOnCurve(object['locator'], lower_curve)
            pointOnCurve = cmds.createNode('pointOnCurveInfo', name=object['locator'].replace('CTL_LOC', 'CTL_POCI'))
            cmds.connectAttr('{0}.worldSpace'.format(lower_curve), '{0}.inputCurve'.format(pointOnCurve))
            cmds.setAttr('{0}.parameter'.format(pointOnCurve), closestParam)
            cmds.connectAttr('{0}.position'.format(pointOnCurve), '{0}.translate'.format(object['locatorGroup']))

        # Create the rough curves and use them to drive the originals with a wire deformer
        rough_upper_curve = cmds.duplicate(upper_curve, name='{0}_{1}_upper_rough_DEF_CRV'.format(self.prefix, self.name))[0]
        cmds.rebuildCurve(rough_upper_curve, constructionHistory=False, degree=3, spans=4, keepTangents=False)
        cmds.wire(upper_curve, wire=rough_upper_curve, name='{0}_{1}_upper_base_DEF_WIRD'.format(self.prefix, self.name))


        rough_lower_curve = cmds.duplicate(lower_curve, name='{0}_{1}_lower_rough_DEF_CRV'.format(self.prefix, self.name))[0]
        cmds.rebuildCurve(rough_lower_curve, constructionHistory=False, degree=3, spans=4, keepTangents=False)
        cmds.wire(lower_curve, wire=rough_lower_curve, name='{0}_{1}_lower_base_DEF_WIRD'.format(self.prefix, self.name))

        # Create controls/joints for rough curves
        # Start and end control locators already exist (the inner/outer locators)
        rough_upper_locs_group = cmds.group(name='{0}_{1}_upper_rough_locators_PAR_GRP'.format(self.prefix, self.name), parent=logic_group, empty=True)
        rough_lower_locs_group = cmds.group(name='{0}_{1}_lower_rough_locators_PAR_GRP'.format(self.prefix, self.name), parent=logic_group, empty=True)
        num_controls = 5
        control_percent = 1.0 / (num_controls - 1)
        inner_rough_joint = cmds.joint(inner_base_objects['locatorGroup'], name='{0}_{1}_inner_rough_CTL_JNT'.format(self.prefix, self.name), position=cmds.xform(inner_base_objects['locatorGroup'], query=True, translation=True, worldSpace=True))
        outer_rough_joint = cmds.joint(outer_base_objects['locatorGroup'], name='{0}_{1}_outer_rough_CTL_JNT'.format(self.prefix, self.name), position=cmds.xform(outer_base_objects['locatorGroup'], query=True, translation=True, worldSpace=True))
        upper_rough_joints = [inner_rough_joint]
        lower_rough_joints = [inner_rough_joint]
        for idx in range(1, num_controls - 1):
            pointOnCurve = python_utils.getPointAlongCurve((control_percent * idx), rough_upper_curve)
            upper_rough_joint = cmds.joint(rough_upper_locs_group, name='{0}_{1}_upper_rough_{2}_CTL_JNT'.format(self.prefix, self.name, idx), position=[pointOnCurve.x, pointOnCurve.y, pointOnCurve.z])
            pos_group = cmds.group(name='{0}_{1}_upper_rough_control_{2}_PLC_GRP'.format(self.prefix, self.name, idx), parent=rough_upper_locs_group, empty=True)
            cmds.matchTransform(pos_group, upper_rough_joint)
            cmds.parent(upper_rough_joint, pos_group)
            upper_rough_joints.append(upper_rough_joint)
            
            pointOnCurve = python_utils.getPointAlongCurve((control_percent * idx), rough_lower_curve)
            lower_rough_joint = cmds.joint(rough_lower_locs_group, name='{0}_{1}_lower_rough_{2}_CTL_JNT'.format(self.prefix, self.name, idx), position=[pointOnCurve.x, pointOnCurve.y, pointOnCurve.z])
            pos_group = cmds.group(name='{0}_{1}_lower_rough_control_{2}_PLC_GRP'.format(self.prefix, self.name, idx), parent=rough_lower_locs_group, empty=True)
            cmds.matchTransform(pos_group, lower_rough_joint)
            cmds.parent(lower_rough_joint, pos_group)
            lower_rough_joints.append(lower_rough_joint)
        upper_rough_joints.append(outer_rough_joint)
        lower_rough_joints.append(outer_rough_joint)

        # Then skin the rough joints to the rough curves.
        cmds.skinCluster(upper_rough_joints, rough_upper_curve, toSelectedBones=False, bindMethod=0, maximumInfluences=2, obeyMaxInfluences=True, dropoffRate=7, name='{0}_{1}_upper_rough_CTL_SCST'.format(self.prefix, self.name))
        cmds.skinCluster(lower_rough_joints, rough_lower_curve, toSelectedBones=False, bindMethod=0, maximumInfluences=2, obeyMaxInfluences=True, dropoffRate=7, name='{0}_{1}_lower_rough_CTL_SCST'.format(self.prefix, self.name))

        # Create the actual controls, make every other control a "fine" control to be initially hidden.
        base_place_transform = om2.MFnTransform(python_utils.getDagPath(self.control_place_joint))
        base_place_vec = base_place_transform.translation(om2.MSpace.kWorld)
        upper_rough_controls = []
        for rough_joint in upper_rough_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(rough_joint)
            joint_relative_vec =  python_utils.getTransformDiffVec(rough_joint, self.joint_dict['baseJoint'])
            new_control_vec = base_place_vec + joint_relative_vec
            control_name = '{0}_{1}_{2}_CTL_CRV'.format(prefix, component_name, joint_name)
            new_control_group, new_control = python_utils.makeControl(control_name, 1.5, curveType="circle")
            cmds.xform(new_control_group, translation=[new_control_vec.x, new_control_vec.y, new_control_vec.z], worldSpace=True)
            cmds.parent(new_control_group, user_controls_group)
            python_utils.connectTransforms(new_control, rough_joint)
            upper_rough_controls.append(control_name)

        lower_rough_controls = []
        for rough_joint in lower_rough_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(rough_joint)
            joint_relative_vec =  python_utils.getTransformDiffVec(rough_joint, self.joint_dict['baseJoint'])
            new_control_vec = base_place_vec + joint_relative_vec
            control_name = '{0}_{1}_{2}_CTL_CRV'.format(prefix, component_name, joint_name, 'PLC', 'GRP')
            # The inner and outer controls will have already been made by the loop for the upper rough joints.
            if not cmds.ls(control_name):
                new_control_group, new_control = python_utils.makeControl(control_name, 1.5, curveType="circle")
                cmds.xform(new_control_group, translation=[new_control_vec.x, new_control_vec.y, new_control_vec.z], worldSpace=True)
                cmds.parent(new_control_group, user_controls_group)
                python_utils.connectTransforms(new_control, rough_joint)
            lower_rough_controls.append(control_name)

        # make every other control a "fine" control
        cmds.addAttr(upper_rough_controls[0], longName='SecondaryControls', attributeType='bool', keyable=True)

        for i in range(1, len(upper_rough_controls)):
            cmds.addAttr(upper_rough_controls[i], longName='SecondaryControls', proxy='{0}.SecondaryControls'.format(upper_rough_controls[0]), keyable=True)
            if (i % 2):
                cmds.connectAttr('{0}.SecondaryControls'.format(upper_rough_controls[i]), '{0}.visibility'.format(upper_rough_controls[i]))

        for i in range(1, len(lower_rough_controls)):
            if not cmds.attributeQuery('SecondaryControls', node=lower_rough_controls[i], exists=True):
                cmds.addAttr(lower_rough_controls[i], longName='SecondaryControls', proxy='{0}.SecondaryControls'.format(lower_rough_controls[0]), keyable=True)
                if (i % 2):
                    cmds.connectAttr('{0}.SecondaryControls'.format(lower_rough_controls[i]), '{0}.visibility'.format(lower_rough_controls[i]))

        # make the fine and/or secondary controls follow the main controls they're between
        for i in range(1, len(upper_rough_controls)-1, 2):
            control_parent_group = cmds.listRelatives(upper_rough_controls[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control_parent_group)
            new_control_parent_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=control_parent_group, empty=True)
            cmds.matchTransform(new_control_parent_group, upper_rough_controls[i])
            cmds.parent(upper_rough_controls[i], new_control_parent_group)

            joint_parent_group = cmds.listRelatives(upper_rough_joints[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_parent_group)
            new_joint_parent_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=joint_parent_group, empty=True)
            cmds.matchTransform(new_joint_parent_group, upper_rough_joints[i])
            cmds.parent(upper_rough_joints[i], new_joint_parent_group)
            
            prev_joint = upper_rough_joints[i-1]
            next_joint = upper_rough_joints[i+1]
            cmds.parentConstraint(prev_joint, next_joint, new_joint_parent_group, maintainOffset=True)
            prev_control = upper_rough_controls[i-1]
            next_control = upper_rough_controls[i+1]
            cmds.parentConstraint(prev_control, next_control, new_control_parent_group, maintainOffset=True)

        for i in range(1, len(lower_rough_controls)-1, 2):
            control_parent_group = cmds.listRelatives(lower_rough_controls[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control_parent_group)
            new_control_parent_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=control_parent_group, empty=True)
            cmds.matchTransform(new_control_parent_group, lower_rough_controls[i])
            cmds.parent(lower_rough_controls[i], new_control_parent_group)

            joint_parent_group = cmds.listRelatives(lower_rough_joints[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_parent_group)
            new_joint_parent_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=joint_parent_group, empty=True)
            cmds.matchTransform(new_joint_parent_group, lower_rough_joints[i])
            cmds.parent(lower_rough_joints[i], new_joint_parent_group)
            
            prev_joint = lower_rough_joints[i-1]
            next_joint = lower_rough_joints[i+1]
            cmds.parentConstraint(prev_joint, next_joint, new_joint_parent_group, maintainOffset=True)
            prev_control = lower_rough_controls[i-1]
            next_control = lower_rough_controls[i+1]
            cmds.parentConstraint(prev_control, next_control, new_control_parent_group, maintainOffset=True)


        #Now create the blink curves.
        #First create the rough curve that will blend between the top and bottom curves, along with the attributes that will drive the blendshape weights.
        blink_curve = cmds.duplicate(rough_upper_curve, name='{0}_{1}_blink_DEF_CRV'.format(self.prefix, self.name))[0]
        blink_blendshape = cmds.blendShape(rough_upper_curve, rough_lower_curve, blink_curve, name='L_headeyeLid_blink_CTL_BSHP')[0]
        all_rough_controls = upper_rough_controls[0:-1] + lower_rough_controls[1:]
        cmds.addAttr(all_rough_controls[0], longName='SmartBlink', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr('{0}.SmartBlink'.format(all_rough_controls[0]), '{0}.{1}'.format(blink_blendshape, rough_lower_curve))
        reverse_node = cmds.createNode('reverse', name=all_rough_controls[0].replace('DEF_CRV', 'smartblink_REV'))
        cmds.connectAttr('{0}.SmartBlink'.format(all_rough_controls[0]), '{0}.inputX'.format(reverse_node))
        cmds.connectAttr('{0}.outputX'.format(reverse_node), '{0}.{1}'.format(blink_blendshape, rough_upper_curve))
        for user_control in all_rough_controls[1:]:
            cmds.addAttr(user_control, longName='SmartBlink', proxy='{0}.SmartBlink'.format(all_rough_controls[0]), keyable=True)

        #Now create the curves that will follow the main blink curve, and which the rough curves will be connected to via blendshape.
        upper_blink_curve = cmds.duplicate(upper_curve, name='{0}_{1}_upper_blink_DEF_CRV'.format(self.prefix, self.name))[0]
        lower_blink_curve = cmds.duplicate(lower_curve, name='{0}_{1}_lower_blink_DEF_CRV'.format(self.prefix, self.name))[0]

        upper_blink_wire = cmds.wire(upper_blink_curve, wire=blink_curve, name='{0}_{1}_upper_blink_CTL_WIRD'.format(self.prefix, self.name))[0]
        cmds.setAttr('{0}.scale[0]'.format(upper_blink_wire), 0)

        cmds.setAttr('{0}.SmartBlink'.format(all_rough_controls[0]), 1.0)
        lower_blink_wire = cmds.wire(lower_blink_curve, wire=blink_curve, name='{0}_{1}_lower_blink_CTL_WIRD'.format(self.prefix, self.name))[0]
        cmds.setAttr('{0}.scale[0]'.format(lower_blink_wire), 0)

        cmds.setAttr('{0}.SmartBlink'.format(all_rough_controls[0]), 0.5)

        #Then we sneak in a "middle" curve that will act as an adjustable inbetween blend shape, this is needed to correct clipping issues from that extra
        #snap-to-the-locators thing we're adding down at the bottom of the file (which is, itself, fixing other, different, clipping issues)
        middle_curve = cmds.duplicate(blink_curve, name='{0}_{1}_middle_CTL_CRV'.format(self.prefix, self.name))[0]
        cmds.blendShape(blink_blendshape, edit=True, inBetween=True, inBetweenType='relative', t=(blink_curve, 1, middle_curve, 0.5))

        #Now we blendshape the base lid curves to their respective blink curves.
        upper_blink_blendshape = cmds.blendShape(upper_blink_curve, '{0}_{1}_upper_base_DEF_CRV'.format(self.prefix, self.name), name='{0}_{1}_upper_blink_CTL_BSHP'.format(self.prefix, self.name))[0]
        lower_blink_blendshape = cmds.blendShape(lower_blink_curve, '{0}_{1}_lower_base_DEF_CRV'.format(self.prefix, self.name), name='{0}_{1}_lower_blink_CTL_BSHP'.format(self.prefix, self.name))[0]
        cmds.addAttr(all_rough_controls[0], longName='UpperBlink', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr('{0}.UpperBlink'.format(all_rough_controls[0]), '{0}.{1}'.format(upper_blink_blendshape, upper_blink_curve))
        cmds.addAttr(all_rough_controls[0], longName='LowerBlink', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr('{0}.LowerBlink'.format(all_rough_controls[0]), '{0}.{1}'.format(lower_blink_blendshape, lower_blink_curve))
        for user_control in all_rough_controls[1:]:
            cmds.addAttr(user_control, longName='UpperBlink', proxy='{0}.UpperBlink'.format(all_rough_controls[0]), keyable=True)
            cmds.addAttr(user_control, longName='LowerBlink', proxy='{0}.LowerBlink'.format(all_rough_controls[0]), keyable=True)

        #Now lets add controls to the rough blink curve so users can tweak it.
        blink_joints_group = cmds.group(name='{0}_{1}_blink_joints_PAR_GRP'.format(self.prefix, self.name), parent=logic_group, empty=True)
        num_controls = 5
        control_percent = 1.0 / (num_controls - 1)
        blink_joints = [inner_rough_joint]
        blink_locs = []
        for idx in range(1, num_controls - 1):
            pointOnCurve = python_utils.getPointAlongCurve((control_percent * idx), blink_curve)
            blink_joint = cmds.joint(blink_joints_group, name='{0}_{1}_blink_{2}_CTL_JNT'.format(self.prefix, self.name, idx), position=[pointOnCurve.x, pointOnCurve.y, pointOnCurve.z])
            pos_group = cmds.group(name='{0}_{1}_blink_control_{2}_PLC_GRP'.format(self.prefix, self.name, idx), parent=blink_joints_group, empty=True)
            cmds.matchTransform(pos_group, blink_joint)
            cmds.parent(blink_joint, pos_group)
            blink_joints.append(blink_joint)
            
            blink_loc = cmds.spaceLocator(name='{0}_{1}_blink_{2}_CTL_LOC'.format(self.prefix, self.name, idx))[0]
            cmds.matchTransform(blink_loc, pos_group)
            cmds.parent(blink_loc, blink_joints_group)
            closestPoint, closestParam = python_utils.getClosestPointOnCurve(blink_loc, blink_curve)
            pointOnCurveNode = cmds.createNode('pointOnCurveInfo', name=blink_loc.replace('CTL_LOC', 'CTL_POCI'))
            cmds.connectAttr('{0}.outputGeometry[0]'.format(blink_blendshape), '{0}.inputCurve'.format(pointOnCurveNode))
            cmds.setAttr('{0}.parameter'.format(pointOnCurveNode), closestParam)
            cmds.connectAttr('{0}.position'.format(pointOnCurveNode), '{0}.translate'.format(blink_loc))
            blink_locs.append(blink_loc)

        blink_joints.append(outer_rough_joint)

        blink_skin_cluster = cmds.skinCluster(blink_joints, blink_curve, toSelectedBones=False, bindMethod=0, maximumInfluences=2, obeyMaxInfluences=True, dropoffRate=7, name='{0}_{1}_blink_CTL_SCST'.format(self.prefix, self.name))[0]
        # We plug in the inner and outer joint's inverse world matrices to the skin cluster bind pre matrix to avoid double-transforms.
        cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(blink_joints[0]), '{0}.bindPreMatrix[0]'.format(blink_skin_cluster))
        cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(blink_joints[-1]), '{0}.bindPreMatrix[{1}]'.format(blink_skin_cluster, len(blink_joints)-1))

        blink_controls = []
        wire_idx = 0
        for blink_joint in blink_joints:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(blink_joint)
            joint_relative_vec =  python_utils.getTransformDiffVec(blink_joint, self.joint_dict['baseJoint'])
            new_control_vec = base_place_vec + joint_relative_vec
            control_name = '{0}_{1}_{2}_CTL_CRV'.format(prefix, component_name, joint_name, 'PLC', 'GRP')
            # The inner and outer controls will have already been made by the loop for the upper rough joints.
            if not cmds.ls(control_name):
                new_control_group, new_control = python_utils.makeControl(control_name, 1.5, curveType="circle")
                cmds.xform(new_control_group, translation=[new_control_vec.x, new_control_vec.y, new_control_vec.z], worldSpace=True)
                cmds.parent(new_control_group, user_controls_group)
                python_utils.connectTransforms(new_control, blink_joint)
                new_control_parent_group = cmds.group(name='{0}_{1}_{2}_0_PAR_GRP'.format(prefix, component_name, joint_name), parent=new_control_group, empty=True)
                cmds.matchTransform(new_control_parent_group, new_control)
                cmds.parent(new_control, new_control_parent_group)
                cmds.parentConstraint(blink_locs[wire_idx], new_control_parent_group, maintainOffset=True)
                wire_idx += 1
            blink_controls.append(control_name)
            
        for i in range(1, len(blink_controls)-1, 2):
            control_parent_group = cmds.listRelatives(blink_controls[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control_parent_group)
            new_control_parent_group = cmds.group(name='{0}_{1}_{2}_1_PAR_GRP'.format(prefix, component_name, joint_name), parent=control_parent_group, empty=True)
            cmds.matchTransform(new_control_parent_group, blink_controls[i])
            cmds.parent(blink_controls[i], new_control_parent_group)

            joint_parent_group = cmds.listRelatives(blink_joints[i], parent=True)[0]
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(joint_parent_group)
            new_joint_parent_group = cmds.group(name='{0}_{1}_{2}_PAR_GRP'.format(prefix, component_name, joint_name), parent=joint_parent_group, empty=True)
            cmds.matchTransform(new_joint_parent_group, blink_joints[i])
            cmds.parent(blink_joints[i], new_joint_parent_group)
            
            prev_joint = blink_joints[i-1]
            next_joint = blink_joints[i+1]
            cmds.parentConstraint(prev_joint, next_joint, new_joint_parent_group, maintainOffset=True)
            prev_control = blink_controls[i-1]
            next_control = blink_controls[i+1]
            cmds.parentConstraint(prev_control, next_control, new_control_parent_group, maintainOffset=True)
        
        
        cmds.addAttr(all_rough_controls[0], longName='BlinkTweakControls', attributeType='bool', keyable=True, defaultValue=False)
        for control in all_rough_controls[1:]:
            cmds.addAttr(control, longName='BlinkTweakControls', proxy='{0}.BlinkTweakControls'.format(all_rough_controls[0]), keyable=True)

        for control in blink_controls[1:-1]:
            cmds.addAttr(control, longName='BlinkTweakControls', proxy='{0}.BlinkTweakControls'.format(all_rough_controls[0]), keyable=True)
            cmds.connectAttr('{0}.BlinkTweakControls'.format(all_rough_controls[0]), '{0}.visibility'.format(control))

        # Create another parent on top of the end joints so the end joint can move between the locators and the surface of the eye.
        for object in upper_base_objects[1:-1]:
            new_joint = cmds.duplicate(object['joint'], name=object['joint'].replace('_BND', '_surface_BND'), parentOnly=True)[0]
            cmds.parent(object['joint'], new_joint)
            point_constraint = cmds.pointConstraint(object['locator'], new_joint, object['joint'], name=object['joint'].replace('_JNT', '_PCNST'))[0]
            set_range = cmds.createNode('setRange', name=object['joint'].replace('_BND_JNT', '_CRN_SRG'))
            cmds.connectAttr('{0}.UpperBlink'.format(all_rough_controls[0]), '{0}.valueX'.format(set_range))
            cmds.setAttr('{0}.oldMinX'.format(set_range), .75)
            cmds.setAttr('{0}.oldMaxX'.format(set_range), 1)
            cmds.setAttr('{0}.maxX'.format(set_range), 1)
            cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.{1}W0'.format(point_constraint, object['locator']))
            
            reverse = cmds.createNode('reverse', name=object['joint'].replace('_BND_JNT', '_CRN_REV'))
            cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.inputX'.format(reverse))
            cmds.connectAttr('{0}.outputX'.format(reverse), '{0}.{1}W1'.format(point_constraint, new_joint))

        for object in lower_base_objects[1:-1]:
            new_joint = cmds.duplicate(object['joint'], name=object['joint'].replace('_BND', '_surface_BND'), parentOnly=True)[0]
            cmds.parent(object['joint'], new_joint)
            point_constraint = cmds.pointConstraint(object['locator'], new_joint, object['joint'], name=object['joint'].replace('_JNT', '_PCNST'))[0]
            set_range = cmds.createNode('setRange', name=object['joint'].replace('_BND_JNT', '_CRN_SRG'))
            cmds.connectAttr('{0}.LowerBlink'.format(all_rough_controls[0]), '{0}.valueX'.format(set_range))
            cmds.setAttr('{0}.oldMinX'.format(set_range), .75)
            cmds.setAttr('{0}.oldMaxX'.format(set_range), 1)
            cmds.setAttr('{0}.maxX'.format(set_range), 1)
            cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.{1}W0'.format(point_constraint, object['locator']))
            
            reverse = cmds.createNode('reverse', name=object['joint'].replace('_BND_JNT', '_CRN_REV'))
            cmds.connectAttr('{0}.outValueX'.format(set_range), '{0}.inputX'.format(reverse))
            cmds.connectAttr('{0}.outputX'.format(reverse), '{0}.{1}W1'.format(point_constraint, new_joint))

        cmds.delete(self.control_place_joint) 

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return