from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class SingleChainIK(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the common groups that all components share if they don't exist already.
        if not self.baseGroups:
            self.baseGroups = python_utils.generate_component_base(self.name, self.prefix)

        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.start_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_start_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        self.end_joint = cmds.joint(self.start_joint, name='{0}_{1}_end_BND_JNT'.format(self.prefix, self.name), position=(1, 0, 0), relative=True, scaleCompensate=False)

        # We have to initialize the components input/output custom attrs so they can be connected later, even if the component rig hasn't been created yet.
        self.initializeInputandoutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        # Create some groups for organization.
        joints_group = cmds.group(name='{0}_{1}_ik_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        controls_group = cmds.group(name='{0}_{1}_ctl_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        msc_group = cmds.group(name='{0}_{1}_msc_HOLD_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.inheritTransform(msc_group, off=True)

        # Create ik joints.
        start_ik_joint = python_utils.duplicateBindJoint(self.start_joint, joints_group, 'IK')
        end_ik_joint = python_utils.duplicateBindJoint(self.end_joint, start_ik_joint, 'IK')

        # Set joint orients, zero out joint orientation and transfer to rotation.
        cmds.select(self.start_joint)
        python_utils.setOrientJoint(start_ik_joint, 'yzx', 'zup')
        python_utils.setOrientJoint(end_ik_joint, 'none', 'zup')

        # Make a parent group that will hold the starting joint orient and negate along the secondary axis to mirror controls.
        orient_group = cmds.group(name='{0}_{1}_orient_PAR_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.matchTransform(orient_group, start_ik_joint)
        cmds.parent(joints_group, orient_group)
        cmds.parent(controls_group, orient_group)
        if self.prefix == 'R':
            cmds.setAttr('{0}.scaleX'.format(orient_group), -1)
        

        # Create controls.
        base_control = python_utils.makeCircleControl('{0}_{1}_end_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(name='{0}_{1}_end_PLC_GRP'.format(self.prefix, self.name), empty=True)
        cmds.matchTransform(base_placement, base_control)
        cmds.parent(base_control, base_placement)
        cmds.parent(base_placement, controls_group)
        cmds.matchTransform(base_placement, end_ik_joint, piv=True, pos=True, rot=True, scale=True)

        cmds.select(base_control)
        cmds.addAttr(longName='length', attributeType='float', defaultValue=1.0, minValue=0.0, keyable=True, hidden=False)
        cmds.addAttr(longName='ikfkswitch', defaultValue=1.0, minValue=0.0, maxValue=1.0, keyable=True, hidden=False)

        python_utils.constrainTransformByMatrix(base_control, end_ik_joint, connectAttrs=['rotate'])

        # Create single solver ik system.
        ik_handle, ik_effector = cmds.ikHandle( name='{0}_{1}_base_IKS_HDL'.format(self.prefix, self.name),
                                                startJoint=start_ik_joint,
                                                endEffector=end_ik_joint,
                                                solver='ikSCsolver' )
        ik_effector = cmds.rename(ik_effector, '{0}_{1}_base_IKS_EFF'.format(self.prefix, self.name))
        # Parent ik to control.
        cmds.matchTransform(ik_handle, base_control)
        cmds.parent(ik_handle, base_control)

        # Create various locators for measurement reasons.
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(start_ik_joint)
        start_locator = cmds.spaceLocator(name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_LEN_LOC'))[0]
        cmds.parent(start_locator, self.baseGroups['placement_group'])
        cmds.matchTransform(start_locator, start_ik_joint)
        cmds.connectAttr('{0}.translate'.format(start_ik_joint), '{0}.translate'.format(start_locator))

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(end_ik_joint)
        base_end_locator = cmds.spaceLocator(name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'base_LEN_LOC'))[0]
        cmds.parent(base_end_locator, orient_group)
        cmds.matchTransform(base_end_locator, end_ik_joint)

        # Create various locators for measurement reasons.
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(start_ik_joint)
        control_start_locator = cmds.spaceLocator(name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'unscale_LEN_LOC'))[0]
        cmds.parent(control_start_locator, msc_group)
        cmds.matchTransform(control_start_locator, start_ik_joint)

        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(end_ik_joint)
        control_end_locator = cmds.spaceLocator(name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'unscale_LEN_LOC'))[0]
        cmds.parent(control_end_locator, msc_group)
        cmds.matchTransform(control_end_locator, end_ik_joint)


        # Create length calc nodes for "length" variable.
        distance = python_utils.getTransformDistance(start_ik_joint, end_ik_joint)
        baseDistNode = cmds.shadingNode('distanceBetween', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'base_LEN_CMATH'), asUtility=True)
        start_matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(start_locator))
        cmds.connectAttr('{0}.worldMatrix'.format(start_locator), '{0}.inputMatrix'.format(start_matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(start_matrix_decompose), '{0}.point1'.format(baseDistNode))
        base_end_matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(base_end_locator))
        cmds.connectAttr('{0}.worldMatrix'.format(base_end_locator), '{0}.inputMatrix'.format(base_end_matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(base_end_matrix_decompose), '{0}.point2'.format(baseDistNode))

        multStartLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'fk_LEN_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(multStartLen), 2)
        cmds.setAttr('{0}.floatA'.format(multStartLen), distance)
        cmds.connectAttr('{0}.length'.format(base_control), '{0}.floatB'.format(multStartLen))


        # Create length calc nodes for distance to IK handle.
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(end_ik_joint)
        jointHandleDist = cmds.shadingNode('distanceBetween', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_LEN_CMATH'), asUtility=True)
        cmds.connectAttr('{0}.outputTranslate'.format(start_matrix_decompose), '{0}.point1'.format(jointHandleDist))
        matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(base_control))
        cmds.connectAttr('{0}.worldMatrix'.format(base_control), '{0}.inputMatrix'.format(matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.point2'.format(jointHandleDist))

        controlDist = cmds.shadingNode('distanceBetween', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'unscale_LEN_CMATH'), asUtility=True)
        matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(control_start_locator))
        cmds.connectAttr('{0}.worldMatrix'.format(control_start_locator), '{0}.inputMatrix'.format(matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.point1'.format(controlDist))
        matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(control_end_locator))
        cmds.connectAttr('{0}.worldMatrix'.format(control_end_locator), '{0}.inputMatrix'.format(matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.point2'.format(controlDist))

        # Divide the distance between the start joint and the control by the original distance between the start and end joints to get rid of 
        # double-scaling.
        getScale = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_1_LEN_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(getScale), 3)
        cmds.connectAttr('{0}.distance'.format(baseDistNode), '{0}.floatA'.format(getScale))
        cmds.connectAttr('{0}.distance'.format(controlDist), '{0}.floatB'.format(getScale))

        divScaleLen = cmds.shadingNode('floatMath', name='{0}_{1}_{2}_{3}'.format(prefix, component_name, joint_name, 'ik_2_LEN_CMATH'), asUtility=True)
        cmds.setAttr('{0}.operation'.format(divScaleLen), 3)
        cmds.connectAttr('{0}.distance'.format(jointHandleDist), '{0}.floatA'.format(divScaleLen))
        cmds.connectAttr('{0}.outFloat'.format(getScale), '{0}.floatB'.format(divScaleLen))

        # Create switch for different length calc methods.
        scalar_blend_node = python_utils.createScalarBlend(
                '{0}.outFloat'.format(multStartLen),
                '{0}.outFloat'.format(divScaleLen),
                '{0}.translateY'.format(end_ik_joint),
                0.0)
        cmds.connectAttr('{0}.ikfkswitch'.format(base_control), '{0}.blender'.format(scalar_blend_node))


        # Connect control to bind joint.
        mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(start_ik_joint, self.start_joint)
        mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(end_ik_joint, self.end_joint)

        # Create a locator to hold the parent space stuff if it exists.
        data_locator = cmds.spaceLocator(name='{0}_{1}_DAT_LOC'.format(self.prefix, self.name))[0]
        data_locator = cmds.parent(data_locator, base_control, relative=True)[0]
        cmds.select(data_locator)
        cmds.addAttr(longName='parentspace', attributeType='matrix')
        cmds.addAttr(longName='parentinvspace', attributeType='matrix')

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return