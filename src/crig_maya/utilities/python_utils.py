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

def renameCurveShape(node, name):
    curve_shape = cmds.listRelatives(node, shapes=True)[0]
    cmds.rename(curve_shape, name)

def getRigGeo():
        return [x for x in cmds.listRelatives(constants.DEFAULT_GROUPS.geometry, allDescendents=True, type='transform') if cmds.listRelatives(x, shapes=True)]

def zeroOutLocal(node):
    try:
        cmds.setAttr('{0}.translate'.format(node), 0,0,0)
    except:
        constants.RIGGER_LOG.info('couldn\'t zero out {0}.translate')
    try:
        cmds.setAttr('{0}.rotate'.format(node), 0,0,0)
    except:
        constants.RIGGER_LOG.info('couldn\'t zero out {0}.rotate')
    try:
        cmds.setAttr('{0}.scale'.format(node), 1,1,1)
    except:
        constants.RIGGER_LOG.info('couldn\'t zero out {0}.scale')

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
    children = cmds.listRelatives(joint, type='joint', allDescendents=True) if cmds.listRelatives else []
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

def createParentSwitchMult(newParentMatrix, newParentInverseMatrix, childWorldMatrix, name):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_PSWTCH_MMULT'.format(name))
    initial_child_matrix = cmds.getAttr(childWorldMatrix)
    cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), initial_child_matrix, type='matrix')

    initial_parent_inverse_matrix = cmds.getAttr(newParentInverseMatrix)
    cmds.setAttr('{0}.matrixIn[1]'.format(mult_matrix), initial_parent_inverse_matrix, type='matrix')

    cmds.connectAttr(newParentMatrix, '{0}.matrixIn[2]'.format(mult_matrix))
    return mult_matrix


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

def mirrorOffset(parent, child, targetParent, mirrorTarget, liveParent=False, liveTParent=False, pivotTransform=None):
    offset_matrix = getLocalOffset(parent, child)
    mult_matrix_1 = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(mirrorTarget))
    if not liveTParent:
        parentWorldMatrix = om2.MTransformationMatrix(getDagPath(parent).inclusiveMatrix())
        targetParentWorldMatrix = om2.MTransformationMatrix(getDagPath(targetParent).inclusiveMatrix())
        tparentTranslation = targetParentWorldMatrix.translation(om2.MSpace.kWorld)
        parentWorldMatrix.setTranslation(tparentTranslation, om2.MSpace.kWorld)
        parentTotParentMat = targetParentWorldMatrix.asMatrix() * parentWorldMatrix.asMatrixInverse()
        cmds.setAttr('{0}.matrixIn[6]'.format(mult_matrix_1), [parentTotParentMat.inverse().getElement(i, j) for i in range(4) for j in range(4)], type='matrix')
        cmds.setAttr('{0}.matrixIn[1]'.format(mult_matrix_1), [parentTotParentMat.getElement(i, j) for i in range(4) for j in range(4)], type='matrix')
    else:
        decomp1, recomp1 = decomposeAndRecompose('{0}.worldInverseMatrix[0]'.format(targetParent), '{0}.matrixIn[7]'.format(mult_matrix_1))
        decomp2, recomp2 = decomposeAndRecompose('{0}.worldMatrix[0]'.format(parent), '{0}.matrixIn[6]'.format(mult_matrix_1))
        #cmds.setAttr('{0}.matrixIn[6]'.format(mult_matrix_1), cmds.getAttr('{0}.worldMatrix[0]'.format(parent)), type='matrix')
        #cmds.setAttr('{0}.matrixIn[2]'.format(mult_matrix_1), cmds.getAttr('{0}.worldInverseMatrix[0]'.format(parent)), type='matrix')
        decomp3, recomp3 = decomposeAndRecompose('{0}.worldInverseMatrix[0]'.format(parent), '{0}.matrixIn[2]'.format(mult_matrix_1))
        decomp4, recomp4 = decomposeAndRecompose('{0}.worldMatrix[0]'.format(targetParent), '{0}.matrixIn[1]'.format(mult_matrix_1))
    if liveParent:
        cmds.connectAttr('{0}.worldInverseMatrix'.format(parent), '{0}.matrixIn[5]'.format(mult_matrix_1))
    else:
        world_inverse = cmds.getAttr('{0}.worldInverseMatrix'.format(parent))
        cmds.setAttr('{0}.matrixIn[5]'.format(mult_matrix_1), world_inverse, type='matrix')
    if pivotTransform:
        targetParentWorldMatrix = om2.MTransformationMatrix(getDagPath(targetParent).inclusiveMatrix())
        pivotWorldMatrix = om2.MTransformationMatrix(getDagPath(pivotTransform).inclusiveMatrix())
        tParentToPivot = om2.MTransformationMatrix(pivotWorldMatrix.asMatrix() * targetParentWorldMatrix.asMatrixInverse())
        translationMatrix = om2.MTransformationMatrix()
        translationMatrix.setTranslation(tParentToPivot.translation(om2.MSpace.kWorld), om2.MSpace.kWorld)
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix_1), [translationMatrix.asMatrixInverse().getElement(i, j) for i in range(4) for j in range(4)], type="matrix")
        cmds.setAttr('{0}.matrixIn[8]'.format(mult_matrix_1), [translationMatrix.asMatrix().getElement(i, j) for i in range(4) for j in range(4)], type="matrix")
        
    cmds.connectAttr('{0}.worldMatrix'.format(child), '{0}.matrixIn[4]'.format(mult_matrix_1))
    cmds.setAttr('{0}.matrixIn[3]'.format(mult_matrix_1), [offset_matrix.getElement(i, j) for i in range(4) for j in range(4)], type="matrix")
    cmds.connectAttr('{0}.matrixSum'.format(mult_matrix_1), '{0}.offsetParentMatrix'.format(mirrorTarget))

    return mult_matrix_1


def createRotDiffNodes(child_matrix, parent_matrix, rot_axis=['Y']):
    child_node_name = child_matrix.split('.')[0]
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(child_node_name))

    cmds.connectAttr(child_matrix, '{0}.matrixIn[0]'.format(mult_matrix))
    cmds.connectAttr(parent_matrix, '{0}.matrixIn[1]'.format(mult_matrix))

    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(child_node_name))
    cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.inputMatrix'.format(matrix_decompose))

    quat_to_euler = cmds.shadingNode('quatToEuler', name='{0}_BLND_BLNDC'.format(child_node_name), asUtility=True)
    rot_axis.append('W')
    # TODO: Make this not a hack
    if rot_axis[0] == 'Y':
        cmds.setAttr('{0}.inputRotateOrder'.format(quat_to_euler), 1)
    elif rot_axis[0] == 'X':
        cmds.setAttr('{0}.inputRotateOrder'.format(quat_to_euler), 0)
    if rot_axis[0] == 'Z':
        cmds.setAttr('{0}.inputRotateOrder'.format(quat_to_euler), 2)
    for axis in rot_axis:
        cmds.connectAttr('{0}.outputQuat{1}'.format(matrix_decompose, axis), '{0}.inputQuat{1}'.format(quat_to_euler, axis))
    
    return mult_matrix, matrix_decompose, quat_to_euler


def constrainByMatrix(parentMatrix, childTransform, maintain_offset=False, use_parent_offset=False, connectAttrs=['rotate', 'scale', 'translate', 'shear'], world_space=True):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(childTransform))
    child_parent = cmds.listRelatives(childTransform, parent=True)[0]

    cmds.connectAttr(parentMatrix, '{0}.matrixIn[1]'.format(mult_matrix))
    if world_space:
        cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(child_parent), '{0}.matrixIn[2]'.format(mult_matrix))
    input_matrix = '{0}.matrixSum'.format(mult_matrix)
    if maintain_offset:
        parent_mMatrix = om2.MMatrix(cmds.getAttr(parentMatrix))
        child_mMatrix = om2.MMatrix(cmds.getAttr('{0}.worldMatrix'.format(childTransform)))
        offset_matrix = child_mMatrix * parent_mMatrix.inverse()
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix.getElement(i, j) for i in range(4) for j in range(4)], type="matrix")
    if not use_parent_offset:
        matrix_decompose = decomposeAndConnectMatrix(input_matrix, childTransform, connectAttrs)
    else:
        cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.offsetParentMatrix'.format(childTransform))
        matrix_decompose = ''

        
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

def hookUpPointOnSurfaceTo4x4Mat(pointOnSurfaceNode, fourByFourMatNode):
    cmds.connectAttr(pointOnSurfaceNode + '.positionX', fourByFourMatNode + '.in30')
    cmds.connectAttr(pointOnSurfaceNode + '.positionY', fourByFourMatNode + '.in31')
    cmds.connectAttr(pointOnSurfaceNode + '.positionZ', fourByFourMatNode + '.in32')
    cmds.connectAttr(pointOnSurfaceNode + '.normalX', fourByFourMatNode + '.in00')
    cmds.connectAttr(pointOnSurfaceNode + '.normalY', fourByFourMatNode + '.in01')
    cmds.connectAttr(pointOnSurfaceNode + '.normalZ', fourByFourMatNode + '.in02')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentUx', fourByFourMatNode + '.in10')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentUy', fourByFourMatNode + '.in11')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentUz', fourByFourMatNode + '.in12')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentVx', fourByFourMatNode + '.in20')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentVy', fourByFourMatNode + '.in21')
    cmds.connectAttr(pointOnSurfaceNode + '.tangentVz', fourByFourMatNode + '.in22')

def duplicateBindJoint(bind_joint, parent, new_purpose_suffix):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(bind_joint)
    world_position = cmds.xform('{0}'.format(bind_joint), query=True, translation=True, worldSpace=True)
    world_rotation = cmds.xform('{0}'.format(bind_joint), query=True, rotation=True, worldSpace=True)
    new_joint = cmds.joint(
                        parent,
                        name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, new_purpose_suffix, node_type),
                        orientation=world_rotation,
                        position=world_position,
                        radius=cmds.getAttr('{0}.radius'.format(bind_joint))
                    )
    return new_joint

def duplicateBindChain(bind_joint, parent, new_purpose_suffix):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(bind_joint)
    dupe_joints = cmds.duplicate(bind_joint, name=bind_joint.replace(node_purpose, new_purpose_suffix))
    children = cmds.listRelatives(dupe_joints[0], allDescendents=True, fullPath=True, type='transform')
    for child in children:
        short_name = child.split('|')[-1]
        cmds.rename(child, short_name.replace(node_purpose, new_purpose_suffix))
    for i in range(len(dupe_joints)):
        short_name = dupe_joints[i].split('|')[-1]
        dupe_joints[i] = short_name.replace(node_purpose, new_purpose_suffix)
    cmds.parent(dupe_joints[0], parent)
    return dupe_joints

def createLocAt(joint, parent, loc_purpose_suffix):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(joint)
    new_locator = cmds.spaceLocator(name='{0}_{1}_{2}_{3}_LOC'.format(prefix, component_name, joint_name, loc_purpose_suffix))[0]
    cmds.parent(new_locator, parent)
    cmds.matchTransform(new_locator, joint, pos=True, rot=False, scale=False)
    return new_locator

def createLocatorAndParent(joint, parent, loc_purpose_suffix, position=True, rotation=False, scale=False):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(joint)
    locator_place_group = cmds.group(name='{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, joint_name), parent=parent, empty=True)
    cmds.matchTransform(locator_place_group, joint, position=position, rotation=rotation, scale=scale)
    locator = createLocAt(locator_place_group, locator_place_group, loc_purpose_suffix)
    return locator_place_group, locator


def getNodeNameParts(node):
    component_part = node.split('_', 2)
    prefix = component_part[0]
    component_name = component_part[1]
    node_part = component_part[2].rsplit('_', 2)
    joint_name = node_part[0]
    node_purpose = node_part[1]
    node_type = node_part[2]
    return prefix, component_name, joint_name, node_purpose, node_type

def findNextAvailableMultiIndex(attr_name, start_index, sub_attr=''):
    # Assume less than 1 million connections.
    for i in range(start_index, 1000000):
        attr_string = '{0}[{1}]'.format(attr_name, i)
        if sub_attr:
            attr_string = '{0}.{1}'.format(attr_string, sub_attr)
        if not cmds.connectionInfo(attr_string, sourceFromDestination=True):
            return i

def dictionizeAttrs(node_list, attr_list, type=False):
    attr_dict = {}
    for node in node_list:
        attr_dict[node] = {}
        if not type:
            for attr in attr_list:
                try:
                    attr_dict[node][attr] = cmds.getAttr('{0}.{1}'.format(node, attr))
                except:
                    constants.RIGGER_LOG.warning('Node {0} does not have attribute {1}  Could not extract.'.format(node, attr))
        else:
            for attr in attr_list:
                try:
                    attr_dict[node][attr] = {}
                    attr_dict[node][attr]['data'] = cmds.getAttr('{0}.{1}'.format(node, attr))
                    attr_dict[node][attr]['type'] = cmds.getAttr('{0}.{1}'.format(node, attr), type=True)
                except:
                    constants.RIGGER_LOG.warning('Node {0} does not have attribute {1}  Could not extract.'.format(node, attr))

    return attr_dict

def getDagPath(node=None):
    selection = om2.MSelectionList()
    selection.add(node)
    dagPath = selection.getDagPath(0)
    return dagPath

def getDependNode(node=None):
    selection = om2.MSelectionList()
    selection.add(node)
    dagPath = selection.getDependNode(0)
    return dagPath

def getLocalOffset(parent, child):
    parentWorldMatrix = getDagPath(parent).inclusiveMatrix()
    childWorldMatrix = getDagPath(child).inclusiveMatrix()

    return childWorldMatrix * parentWorldMatrix.inverse()

def getTransformDistance(node1, node2):
    diffVector = getTransformDiffVec(node1, node2)
    return diffVector.length()

def getIsProxyAttr(node, attribute):
    dependNode = om2.MFnDependencyNode(getDependNode(node))
    attr = om2.MFnAttribute(dependNode.attribute(attribute))
    return attr.isProxyAttribute

def setIsProxyAttr(node, attribute, isProxy):
    dependNode = om2.MFnDependencyNode(getDependNode(node))
    attr = om2.MFnAttribute(dependNode.attribute(attribute))
    attr.isProxyAttribute = isProxy

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

def getClosestPointOnCurve(transform, curve):
        transformDag = om2.MFnTransform(getDagPath(transform))
        curve = om2.MFnNurbsCurve(getDagPath(curve))
        closestPoint, closestParam = curve.closestPoint(transformDag.rotatePivot(om2.MSpace.kWorld), space=om2.MSpace.kWorld)
        return closestPoint, closestParam

def getClosestPointOnSurface(transform, surface):
        transformDag = om2.MFnTransform(getDagPath(transform))
        surface = om2.MFnNurbsSurface(getDagPath(surface))
        closestPoint, closestU, closestV = surface.closestPoint(transformDag.rotatePivot(om2.MSpace.kWorld), space=om2.MSpace.kWorld)
        return closestPoint, closestU, closestV

def pinTransformToSurface(transform, surface, connectionsList=['rotate', 'translate', 'scale']):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(transform)
    pOSurface = cmds.createNode('pointOnSurfaceInfo', name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'DEF', 'POSI'))
    closestPoint, closestU, closestV = getClosestPointOnSurface(transform, surface)
    cmds.connectAttr('{0}.local'.format(surface), '{0}.inputSurface'.format(pOSurface))
    cmds.setAttr('{0}.parameterU'.format(pOSurface), closestU)
    cmds.setAttr('{0}.parameterV'.format(pOSurface), closestV)
    fourByFour = cmds.createNode('fourByFourMatrix', name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'DEF', '4X4'))
    hookUpPointOnSurfaceTo4x4Mat(pOSurface, fourByFour)
    mult_matrix, matrix_decompose = constrainByMatrix(fourByFour + '.output', transform, False, False, connectionsList)
    return mult_matrix, matrix_decompose, fourByFour, pOSurface

# Basically pass in a 0-1 U coordinate and get back the associated param along the curve.
def getCurveParam(fakeParam, curve):
    curve = om2.MFnNurbsCurve(getDagPath(curve))
    curveLen = curve.length()
    actualParam = curve.findParamFromLength(curveLen * fakeParam)
    return actualParam

def getPointAlongCurve(fakeParam, curve):
    curve = om2.MFnNurbsCurve(getDagPath(curve))
    curveLen = curve.length()
    actualParam = curve.findParamFromLength(curveLen * fakeParam)
    point = curve.getPointAtParam(actualParam, space=om2.MSpace.kWorld)
    return point

def getPointAlongSurface(fakeParamU, fakeParamV, surf):
    surface = om2.MFnNurbsSurface(getDagPath(surf))
    uDomain = surface.knotDomainInU
    uParamLen = uDomain[1] - uDomain[0]
    vDomain = surface.knotDomainInV
    vParamLen = vDomain[1] - vDomain[0]
    paramU = uDomain[0] + (uParamLen * fakeParamU)
    paramV = vDomain[0] + (vParamLen * fakeParamV)
    point = surface.getPointAtParam(paramU, paramV, space=om2.MSpace.kWorld)
    return point, paramU, paramV

def getNumCVs(curve):
    dagPath = getDagPath(curve)
    fnNurbsCurve = om2.MFnNurbsCurve(dagPath)
    return fnNurbsCurve.numCVs

def getNumSurfCVs(node):
    surf = om2.MFnNurbsSurface(getDagPath(node))
    return surf.numCVsInU, surf.numCVsInV

def getDrivenKeys(node):
    keys_dict = {}
    driven_attrs = cmds.setDrivenKeyframe(node, query=True, driven=True)
    if driven_attrs:
        for attr in cmds.setDrivenKeyframe(node, query=True, driven=True):
            keys_dict[attr] = {}
    for attr, dict in keys_dict.items():
        dict['driver'] = cmds.setDrivenKeyframe(attr, query=True, driver=True)[0]
        dict['keyframes'] = cmds.keyframe(attr, query=True, floatChange=True, valueChange=True, absolute=True, index=())
        dict['keytangents'] = cmds.keyTangent(attr, query=True, inAngle=True, inTangentType=True, outAngle=True, outTangentType=True, index=())
        dict['infinites'] = cmds.setInfinity(attr, query=True, preInfinite=True, postInfinite=True)
    return keys_dict

def getCurveData(node):
    curve = om2.MFnNurbsCurve(getDagPath(node))
    point_array = curve.cvPositions()
    knot_array = curve.knots()
    out_dict = {
        'points': [],
        'knots': []
    }
    for point in point_array:
        out_dict['points'].append([point[0], point[1], point[2]])
    for knot in knot_array:
        out_dict['knots'].append(knot)
    return out_dict


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

def insertJointAtParent(parent_joint, child_joint):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(child_joint)
    new_parent_joint = cmds.joint(parent_joint, name='{0}_{1}_{2}_parent_PAR_JNT'.format(prefix, component_name, joint_name))
    cmds.matchTransform(new_parent_joint, parent_joint)
    cmds.parent(child_joint, new_parent_joint)
    setOrientJoint(new_parent_joint, 'yzx', 'zup')
    return new_parent_joint

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

def makeConstraintControl(name, parent, controlledNode, scale, curveType="circle", matchTransform='', maintainOffset=True, useParentOffset=True, connectAttrs=['rotate', 'scale', 'translate', 'shear'], reverse=False):
    position_group, control = makeControl(name, scale, curveType)
    if not matchTransform:
        cmds.matchTransform(position_group, parent)
    else:
        cmds.matchTransform(position_group, matchTransform)
    cmds.parent(position_group, parent)
    if reverse:
        cmds.setAttr('{0}.scale'.format(position_group), -1, -1, -1)
    mult_matrix, matrix_compose = constrainTransformByMatrix(control, controlledNode, maintainOffset, useParentOffset, connectAttrs=connectAttrs)
    return position_group, control, mult_matrix, matrix_compose

def makeControlMatchTransform(name, matchedNode, scale=1, curveType="circle"):
    position_group, control = makeControl(name, scale, curveType)
    cmds.matchTransform(position_group, matchedNode)
    return position_group, control

def replaceJointWithControl(joint, control_name, parent):
        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(joint)
        control = makeCircleControl('{0}_{1}_{2}_CTL_CRV'.format(prefix, component_name, control_name), 2)
        placement_group = cmds.group(name='{0}_{1}_{2}_PLC_GRP'.format(prefix, component_name, control_name), parent=parent, empty=True)
        cmds.matchTransform(placement_group, control)
        cmds.parent(control, placement_group)

        # Match the control to the place joint then delete the joint.
        cmds.matchTransform(placement_group, joint)
        child = cmds.listRelatives(joint)
        if child:
            parent_node = cmds.listRelatives(joint, parent=True)[0]
            cmds.parent(child, parent_node)
        cmds.delete(joint)
        return placement_group, control

def createRibbonFromJoints(front_joints, back_joints, parent_node, name):
    temp_curve_1 = cmds.curve(name='{0}_{1}_temp_1_DEF_CRV'.format(self.prefix, self.name), point=front_joints, degree=1)
    temp_curve_2 = cmds.curve(name='{0}_{1}_temp_2_DEF_CRV'.format(self.prefix, self.name), point=back_joints, degree=1)
    
    new_ribbon = cmds.loft(temp_curve_1, temp_curve_2, constructionHistory=False, degree=1, name='{0}_{1}_{2}_DEF_RBN'.format(self.prefix, self.name, name))[0]
    cmds.parent(new_ribbon, parent_node)
    cmds.xform(new_ribbon, centerPivots=True)
    cmds.delete(temp_curve_1)
    cmds.delete(temp_curve_2)
    return new_ribbon