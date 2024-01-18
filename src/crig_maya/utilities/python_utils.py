import math
import maya.cmds as cmds
import maya.OpenMaya as om
import maya.api.OpenMaya as om2

from ... import constants


def setNodesFromDict(node_dict):
    for name, attrs in node_dict.items():
        for attr, data in attrs.items():
            try:
                cmds.setAttr('{0}.{1}'.format(name, attr), data)
            except:
                constants.RIGGER_LOG.info('attr {0}.{1} could not be set from saved positions.'.format(name, attr))


def generate_component_base(component_name, component_prefix):
    groups = {}
    groups['component_group'] = cmds.group(name='{0}_{1}_GRP'.format(component_prefix, component_name), parent='rig_GRP', empty=True)
    groups['output_group'] = cmds.group(name='{0}_{1}_output_GRP'.format(component_prefix, component_name), parent=groups['component_group'], empty=True)
    groups['input_group'] = cmds.group(name='{0}_{1}_input_GRP'.format(component_prefix, component_name), parent=groups['component_group'], empty=True)
    groups['controls_group'] = cmds.group(name='{0}_{1}_controls_GRP'.format(component_prefix, component_name), parent=groups['component_group'], empty=True)
    groups['deform_group'] = cmds.group(name='{0}_{1}_deform_GRP'.format(component_prefix, component_name), parent=groups['component_group'], empty=True)
    # Create parent space group
    groups['parent_group'] = cmds.group(name='{0}_{1}_parentSpace_PAR_GRP'.format(component_prefix, component_name), parent=groups['controls_group'], empty=True)
    # Turn off transform inheritance because it's getting it's parent transform from the input group.
    cmds.inheritTransform(groups['parent_group'], off=True)
    # Create placement group to hold the initial offset.
    groups['placement_group'] = cmds.group(name='{0}_{1}_placement_PLC_GRP'.format(component_prefix, component_name), parent=groups['parent_group'], empty=True)
    return groups

def zeroJointOrient(joint):
    # Get rotation and the joint orient.
    orient_vec = cmds.getAttr('{0}.jointOrient'.format(joint))[0]
    rotate_vec = cmds.getAttr('{0}.rotate'.format(joint))[0]

    # Get quaternions 'cause they're good for this
    orient_euler = om2.MEulerRotation([math.radians(deg) for deg in orient_vec])
    orient_quat = orient_euler.asQuaternion()
    rotate_euler = om2.MEulerRotation([math.radians(deg) for deg in rotate_vec])
    rotate_quat = rotate_euler.asQuaternion()

    new_euler = (rotate_quat * orient_quat).asEulerRotation()
    new_vec = [math.degrees(rad) for rad in new_euler]

    # Zero out the joint orient.
    cmds.setAttr('{0}.jointOrient'.format(joint), 0,0,0)
    # Add the joint orient to the rotation.
    cmds.setAttr('{0}.rotate'.format(joint), *new_vec)

def zeroJointRotation(joint):
    # Get rotation and the joint orient.
    orient_vec = cmds.getAttr('{0}.jointOrient'.format(joint))[0]
    rotate_vec = cmds.getAttr('{0}.rotate'.format(joint))[0]

    # Get quaternions 'cause they're good for this
    orient_euler = om2.MEulerRotation([math.radians(deg) for deg in orient_vec])
    orient_quat = orient_euler.asQuaternion()
    rotate_euler = om2.MEulerRotation([math.radians(deg) for deg in rotate_vec])
    rotate_quat = rotate_euler.asQuaternion()

    new_euler = (rotate_quat * orient_quat).asEulerRotation()
    new_vec = [math.degrees(rad) for rad in new_euler]

    # Zero out the joint orient.
    cmds.setAttr('{0}.rotate'.format(joint), 0,0,0)
    # Add the joint orient to the rotation.
    cmds.setAttr('{0}.jointOrient'.format(joint), *new_vec)

def setOrientJoint(joint, orient_string, sao_string):
    # We have to zero out the rotations of the descendent joint and parent joint, because maya won't orient the joint otherwise.  This is dumb.
    zeroJointRotation(joint)
    parent_joint = cmds.listRelatives(joint, type='joint', parent=True)[0] if cmds.listRelatives(joint, type='joint', parent=True) else None
    if parent_joint:
        zeroJointRotation(parent_joint)
    child_joint = cmds.listRelatives(joint, type='joint', allDescendents=False)[0] if cmds.listRelatives(joint, type='joint', allDescendents=False) else None
    if child_joint:
        zeroJointRotation(child_joint)
    cmds.select(joint)
    cmds.joint(edit=True, orientJoint=orient_string, secondaryAxisOrient=sao_string, zeroScaleOrient=True, children=False)
    zeroJointOrient(joint)
    if parent_joint:
        zeroJointOrient(parent_joint)
    if child_joint:
        zeroJointOrient(child_joint)

def reverseJointChainOnX(joint):
    start_jnt_dag = getDagPath(joint)
    jnt_transform = om2.MFnTransform(start_jnt_dag)
    rot_quat = jnt_transform.rotation(asQuaternion=True, space=om2.MSpace.kWorld)
    flip_quatZ = om2.MQuaternion(1, 0, 0, 0)
    flipped_quat = flip_quatZ * rot_quat
    jnt_transform.setRotation(flipped_quat, om2.MSpace.kWorld)
    children = cmds.listRelatives(joint, type='joint', allDescendents=True)
    for child in children:
        child_jnt_dag = getDagPath(child)
        jnt_transform = om2.MFnTransform(child_jnt_dag)
        jnt_translate = jnt_transform.translation(om2.MSpace.kTransform)
        jnt_translate.y = -jnt_translate.y
        jnt_transform.setTranslation(jnt_translate, om2.MSpace.kTransform)
        jnt_quaternion = jnt_transform.rotation(space=om2.MSpace.kTransform, asQuaternion=True)
        jnt_quaternion.z = -jnt_quaternion.z
        jnt_transform.setRotation(jnt_quaternion, om2.MSpace.kTransform)

def connectTransforms(parent, child):
    cmds.connectAttr('{0}.translate'.format(parent), '{0}.translate'.format(child))
    cmds.connectAttr('{0}.rotate'.format(parent), '{0}.rotate'.format(child))
    cmds.connectAttr('{0}.scale'.format(parent), '{0}.scale'.format(child))

def createMatrixSwitch(parent1, parent2, child, world_matrix=True, weight=0.0):
    if world_matrix:
        attr = 'worldMatrix[0]'
    else:
        attr = 'matrix'
    mult_matrix = None
    blend_matrix = cmds.createNode('blendMatrix', name='{0}_BLND_SWTCHM'.format(child))
    cmds.connectAttr('{0}.{1}'.format(parent1, attr), '{0}.inputMatrix'.format(blend_matrix))
    cmds.connectAttr('{0}.{1}'.format(parent2, attr), '{0}.target[0].targetMatrix'.format(blend_matrix))
    cmds.setAttr('{0}.target[0].weight'.format(blend_matrix), weight)
    if world_matrix:
        mult_matrix, matrix_decompose = constrainByMatrix('{0}.outputMatrix'.format(blend_matrix), child)
    else:
        input_matrix = '{0}.outputMatrix'.format(blend_matrix)
        matrix_decompose = decomposeAndConnectMatrix(input_matrix, child)
    return blend_matrix, mult_matrix, matrix_decompose

def createColorBlend(attr1, attr2, child, weight=0.0):
    blend_color = cmds.shadingNode('blendColors', name='{0}_BLND_BLNDC'.format(child), asUtility=True)
    cmds.connectAttr(attr1, '{0}.color1'.format(blend_color))
    cmds.connectAttr(attr2, '{0}.color2'.format(blend_color))
    cmds.setAttr('{0}.blender'.format(blend_color), weight)
    cmds.connectAttr('{0}.output'.format(blend_color), child)
    return blend_color

def createScalarBlend(attr1, attr2, child, weight=0.0):
    blend_color = cmds.shadingNode('blendColors', name='{0}_BLND_BLNDC'.format(child), asUtility=True)
    cmds.connectAttr(attr1, '{0}.color1R'.format(blend_color))
    cmds.connectAttr(attr2, '{0}.color2R'.format(blend_color))
    cmds.setAttr('{0}.blender'.format(blend_color), weight)
    cmds.connectAttr('{0}.outputR'.format(blend_color), child)
    return blend_color

def constrainTransformByMatrix(parent, child, maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear']):
    offset_matrix = getLocalOffset(parent, child)
    mult_matrix, matrix_decompose = constrainByMatrix('{0}.worldMatrix'.format(parent), child, maintain_offset, use_parent_offset, connectAttrs)
    
    if maintain_offset:
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix.getElement(i, j) for i in range(4) for j in range(4)], type="matrix")

    return mult_matrix, matrix_decompose

def createRotDiffNodes(child_matrix, parent_matrix, rot_axis=['Y']):
    child_node_name = child_matrix.split('.')[0]
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(child_node_name))

    cmds.connectAttr(child_matrix, '{0}.matrixIn[0]'.format(mult_matrix))
    cmds.connectAttr(parent_matrix, '{0}.matrixIn[1]'.format(mult_matrix))

    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(child_node_name))
    cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.inputMatrix'.format(matrix_decompose))

    quat_to_euler = cmds.shadingNode('quatToEuler', name='{0}_BLND_BLNDC'.format(child_node_name), asUtility=True)
    rot_axis.append('W')
    for axis in rot_axis:
        cmds.connectAttr('{0}.outputQuat{1}'.format(matrix_decompose, axis), '{0}.inputQuat{1}'.format(quat_to_euler, axis))
    
    return mult_matrix, matrix_decompose, quat_to_euler


def constrainByMatrix(parentMatrix, childTransform, maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear']):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(childTransform))
    child_parent = cmds.listRelatives(childTransform, parent=True)[0]

    cmds.connectAttr(parentMatrix, '{0}.matrixIn[1]'.format(mult_matrix))
    cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(child_parent), '{0}.matrixIn[2]'.format(mult_matrix))
    input_matrix = '{0}.matrixSum'.format(mult_matrix)
    if not use_parent_offset:
        matrix_decompose = decomposeAndConnectMatrix(input_matrix, childTransform, connectAttrs)
    else:
        cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.offsetParentMatrix'.format(childTransform))
        matrix_decompose = ''

    if maintain_offset:
        parent_mMatrix = om2.MMatrix(cmds.getAttr(parentMatrix))
        child_mMatrix = om2.MMatrix(cmds.getAttr('{0}.worldMatrix'.format(childTransform)))
        offset_matrix = child_mMatrix * parent_mMatrix.inverse()
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix.getElement(i, j) for i in range(4) for j in range(4)], type="matrix")

        
    return mult_matrix, matrix_decompose

def createDistNode(node1, node2, decompose_1='', decompose_2='', space_matrix=''):
    distNode = cmds.shadingNode('distanceBetween', name='{0}_{1}_DIST'.format(node2, node1), asUtility=True)
    if not decompose_1: 
        decompose_1 = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(node1))
        cmds.connectAttr('{0}.worldMatrix'.format(node1), '{0}.inputMatrix'.format(decompose_1))
    cmds.connectAttr('{0}.outputTranslate'.format(decompose_1), '{0}.point1'.format(distNode))
    if space_matrix:
        cmds.connectAttr(space_matrix, '{0}.inMatrix1'.format(distNode))
    if not decompose_2:
        decompose_2 = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(node2))
        cmds.connectAttr('{0}.worldMatrix'.format(node2), '{0}.inputMatrix'.format(decompose_2))
    cmds.connectAttr('{0}.outputTranslate'.format(decompose_2), '{0}.point2'.format(distNode))
    if space_matrix:
        cmds.connectAttr(space_matrix, '{0}.inMatrix2'.format(distNode))
    return distNode, decompose_1, decompose_2

def decomposeAndConnectMatrix(inputMatrix, childTransform, connectAttrs=['rotate', 'scale', 'translate', 'shear']):
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(childTransform))
    cmds.connectAttr(inputMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    if 'rotate' in connectAttrs:
        cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(childTransform))
    if 'scale' in connectAttrs:
        cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(childTransform))
    if 'translate' in connectAttrs:
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(childTransform))
    if 'shear' in connectAttrs:
        cmds.connectAttr('{0}.outputShear'.format(matrix_decompose), '{0}.shear'.format(childTransform))
    return matrix_decompose

def decomposeAndRecompose(inputMatrix, outputMatrix, keepList=['rotate', 'scale', 'translate', 'shear']):
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(inputMatrix))
    matrix_recompose = cmds.createNode('composeMatrix', name='{0}_MCNST_RCOMP'.format(outputMatrix))
    cmds.connectAttr(inputMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    if 'rotate' in keepList:
        cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.inputRotate'.format(matrix_recompose))
    if 'scale' in keepList:
        cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.inputScale'.format(matrix_recompose))
    if 'translate' in keepList:
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.inputTranslate'.format(matrix_recompose))
    if 'shear' in keepList:
        cmds.connectAttr('{0}.outputShear'.format(matrix_decompose), '{0}.inputShear'.format(matrix_recompose))
    cmds.connectAttr('{0}.outputMatrix'.format(matrix_recompose), outputMatrix)
    return matrix_decompose, matrix_recompose

def copyOverMatrix(parentMatrix, childTransform):
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(childTransform))
    cmds.connectAttr(parentMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(childTransform))
    cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(childTransform))
    cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(childTransform))
    cmds.connectAttr('{0}.outputShear'.format(matrix_decompose), '{0}.shear'.format(childTransform))
    cmds.disconnectAttr(parentMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    cmds.delete(matrix_decompose)

def duplicateBindJoint(bind_joint, parent, new_purpose_suffix):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(bind_joint)
    world_position = cmds.xform('{0}'.format(bind_joint), query=True, translation=True, worldSpace=True)
    new_joint = cmds.joint(parent, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, new_purpose_suffix, node_type), position=world_position, radius=cmds.getAttr('{0}.radius'.format(bind_joint)))
    return new_joint

def getNodeNameParts(node):
    component_part = node.split('_', 2)
    prefix = component_part[0]
    component_name = component_part[1]
    node_part = component_part[2].rsplit('_', 2)
    joint_name = node_part[0]
    node_purpose = node_part[1]
    node_type = node_part[2]
    return prefix, component_name, joint_name, node_purpose, node_type

def dictionizeAttrs(node_list, attr_list):
    attr_dict = {}
    for node in node_list:
        attr_dict[node] = {}
        for attr in attr_list:
            attr_dict[node][attr] = cmds.getAttr('{0}.{1}'.format(node, attr))
    return attr_dict

def getDagPath(node=None):
    selection = om2.MSelectionList()
    selection.add(node)
    dagPath = selection.getDagPath(0)
    return dagPath

def getLocalOffset(parent, child):
    parentWorldMatrix = getDagPath(parent).inclusiveMatrix()
    childWorldMatrix = getDagPath(child).inclusiveMatrix()

    return childWorldMatrix * parentWorldMatrix.inverse()

def getTransformDistance(node1, node2):
    diffVector = getTransformDiffVec(node1, node2)
    return diffVector.length()

def getTransformDiffVec(node1, node2):
    transformFuncs = om2.MFnTransform()
    node1DAG = getDagPath(node1)
    transformFuncs.setObject(node1DAG)
    node1Vector = transformFuncs.translation(om2.MSpace.kWorld)

    node2DAG = getDagPath(node2)
    transformFuncs.setObject(node2DAG)
    node2Vector = transformFuncs.translation(om2.MSpace.kWorld)

    diffVector = node1Vector - node2Vector
    return diffVector

def getPoleVec(lineNode1, lineNode2, poleNode):
    ln1_trans = om2.MFnTransform(getDagPath(lineNode1))
    ln2_trans = om2.MFnTransform(getDagPath(lineNode2))
    pole_trans = om2.MFnTransform(getDagPath(poleNode))

    line_vec = ln2_trans.translation(om2.MSpace.kWorld) - ln1_trans.translation(om2.MSpace.kWorld)
    pole_vec = pole_trans.translation(om2.MSpace.kWorld) - ln1_trans.translation(om2.MSpace.kWorld)
    dot = line_vec.normal() * pole_vec
    mid_vec = line_vec.normal() * dot
    out_vec = pole_vec - mid_vec
    return out_vec


def getNumCVs(curve):
    dagPath = getDagPath(curve)
    fnNurbsCurve = om2.MFnNurbsCurve(dagPath)
    return fnNurbsCurve.numCVs()

def invertQuatAxis(object, rotateAxis):
    transform = om2.MFnTransform(getDagPath(object))
    quaternion = transform.rotation(asQuaternion=True)
    if 'x' in rotateAxis:
        quaternion.x = -quaternion.x
    if 'y' in rotateAxis:
        quaternion.y = -quaternion.y
    if 'z' in rotateAxis:
        quaternion.z = -quaternion.z
    transform.setRotation(quaternion, om2.MSpace.kTransform)


def insertJoints(start_joint, end_joint, name, num_joints):
    joint_list = []
    joint_list.append(start_joint)
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(start_joint)
    start_joint_DAG = getDagPath(start_joint)
    transformFuncs = om2.MFnTransform()
    transformFuncs.setObject(start_joint_DAG)
    start_joint_vec = transformFuncs.translation(om2.MSpace.kWorld)
    start_to_end_vec = getTransformDiffVec(end_joint, start_joint)
    num_segments = num_joints
    segment_vec = start_to_end_vec / num_segments
    parent = start_joint
    for seg_num in range(num_segments - 1):
        new_transform_vec = start_joint_vec + (segment_vec * (seg_num + 1))
        new_joint = cmds.joint(
            parent,
            name='{0}_{1}_{2}_{3}_{4}_JNT'.format(prefix, component_name, name, seg_num + 1, node_purpose),
            position=(new_transform_vec.x, new_transform_vec.y, new_transform_vec.z),
            scaleCompensate=False
            )
        joint_list.append(new_joint)
        parent = new_joint
    cmds.parent(end_joint, new_joint)
    return joint_list

def  makeCircleControl(name, scale):
    curve_points = [[0.7836116248912245, 4.798237340988473e-17, -0.7836116248912246], [6.785732323110912e-17, 6.785732323110912e-17, -1.1081941875543877], [-0.7836116248912246, 4.798237340988472e-17, -0.7836116248912244], [-1.1081941875543881, 3.517735619006027e-33, -5.74489823752483e-17], [-0.7836116248912246, -4.7982373409884725e-17, 0.7836116248912245], [-1.1100856969603225e-16, -6.785732323110917e-17, 1.1081941875543884], [0.7836116248912245, -4.798237340988472e-17, 0.7836116248912244], [1.1081941875543881, -9.253679210110099e-33, 1.511240500779959e-16]]
    scaled_points = [[num*scale for num in point] for point in curve_points]
    control = cmds.curve(name=name, d=3, p=scaled_points)
    cmds.closeCurve(name, ch=False, ps=False, rpo=True)
    return control

def makeSquareControl(name, scale):
    curve_points = [(1,0,1), (-1,0,1), (-1,0,-1), (1,0,-1),(1,0,1)]
    scaled_points = [[num*scale for num in point] for point in curve_points]
    control = cmds.curve(name=name, degree=1, point=scaled_points)
    cmds.closeCurve(name, ch=False, ps=False, rpo=True)
    return control

def makeControl(name, scale, curveType="circle"):
    if curveType == "circle":
        control = makeCircleControl(name, scale)
    else:
        control = makeSquareControl(name, scale)
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(name)
    position_group = cmds.group(control, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PLC', 'GRP'))
    return position_group, control

def makeDirectControl(name, controlledNode, scale, curveType="circle", matchTransform=''):
    position_group, control = makeControl(name, scale, curveType)
    parent = cmds.listRelatives(controlledNode, parent=True)
    if not matchTransform:
        cmds.matchTransform(position_group, controlledNode)
    else:
        cmds.matchTransform(position_group, matchTransform)
    cmds.parent(position_group, parent[0])
    cmds.parent(controlledNode, control)
    return position_group, control

def makeConstraintControl(name, parent, controlledNode, scale, curveType="circle", matchTransform='', maintainOffset=True, useParentOffset=True):
    position_group, control = makeControl(name, scale, curveType)
    if not matchTransform:
        cmds.matchTransform(position_group, parent)
    else:
        cmds.matchTransform(position_group, matchTransform)
    cmds.parent(position_group, parent)
    mult_matrix, matrix_compose = constrainTransformByMatrix(control, controlledNode, maintainOffset, useParentOffset)
    return position_group, control, mult_matrix, matrix_compose

def makeControlMatchTransform(name, matchedNode, scale=1, curveType="circle"):
    position_group, control = makeControl(name, scale, curveType)
    cmds.matchTransform(position_group, matchedNode)
    return position_group, control