import maya.cmds as cmds
import maya.OpenMaya as om


def setNodesFromDict(node_dict):
    for name, attrs in node_dict.items():
        for attr, data in attrs.items():
            cmds.setAttr('{0}.{1}'.format(name, attr), data)


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

def constrainTransformByMatrix(parent, child, maintain_offset=False,):
    offset_matrix = getLocalOffset(parent, child)
    mult_matrix, matrix_decompose = constrainByMatrix('{0}.worldMatrix'.format(parent), child)
    
    if maintain_offset:
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix(i, j) for i in range(4) for j in range(4)], type="matrix")

    return mult_matrix, matrix_decompose

def constrainByMatrix(parentMatrix, childTransform, maintain_offset=False):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(childTransform))

    cmds.connectAttr(parentMatrix, '{0}.matrixIn[1]'.format(mult_matrix))
    cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(childTransform), '{0}.matrixIn[2]'.format(mult_matrix))
    input_matrix = '{0}.matrixSum'.format(mult_matrix)
    matrix_decompose = decomposeAndConnectMatrix(input_matrix, childTransform)

    if maintain_offset:
        parent_mMatrix = getMMatrixFromList(cmds.getAttr(parentMatrix))
        child_mMatrix = getMMatrixFromList(cmds.getAttr('{0}.worldMatrix'.format(childTransform)))
        offset_matrix = child_mMatrix * parent_mMatrix.inverse()
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix(i, j) for i in range(4) for j in range(4)], type="matrix")

        
    return mult_matrix, matrix_decompose

def decomposeAndConnectMatrix(inputMatrix, childTransform):
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(childTransform))
    cmds.connectAttr(inputMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(childTransform))
    cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(childTransform))
    cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(childTransform))
    return matrix_decompose

def copyOverMatrix(parentMatrix, childTransform):
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(childTransform))
    cmds.connectAttr(parentMatrix, '{0}.inputMatrix'.format(matrix_decompose))
    cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(childTransform))
    cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(childTransform))
    cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(childTransform))
    cmds.disconnectAttr(parentMatrix, '{0}.inputMatrix'.format(matrix_decompose))

def duplicateBindJoint(bind_joint, parent, new_purpose_suffix):
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(bind_joint)
    world_position = cmds.xform('{0}'.format(bind_joint), query=True, translation=True, worldSpace=True)
    return cmds.joint(parent, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, new_purpose_suffix, node_type), position=world_position, radius=cmds.getAttr('{0}.radius'.format(bind_joint)))

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
    selection = om.MSelectionList()
    selection.add(node)
    dagPath = om.MDagPath()
    selection.getDagPath(0, dagPath)
    return dagPath

def getMObject(node=None):
    selection = om.MSelectionList()
    selection.add(node)

def getLocalOffset(parent, child):
    parentWorldMatrix = getDagPath(parent).inclusiveMatrix()
    childWorldMatrix = getDagPath(child).inclusiveMatrix()

    return childWorldMatrix * parentWorldMatrix.inverse()

def getMMatrixFromList(list_matrix):
    m_mat = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(list_matrix, m_mat)
    return m_mat

def getTransformDistance(node1, node2):
    transformFuncs = om.MFnTransform()
    node1DAG = getDagPath(node1)
    transformFuncs.setObject(node1DAG)
    node1Vector = transformFuncs.translation(om.MSpace.kWorld)

    node2DAG = getDagPath(node2)
    transformFuncs.setObject(node2DAG)
    node2Vector = transformFuncs.translation(om.MSpace.kWorld)

    distVector = node1Vector - node2Vector
    return distVector.length()


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

def makeDirectControl(name, controlledNode, scale, curveType="circle"):
    if curveType == "circle":
        control = makeCircleControl(name, scale)
    else:
        control = makeSquareControl(name, scale)
    prefix, component_name, joint_name, node_purpose, node_type = getNodeNameParts(name)
    parent = cmds.listRelatives(controlledNode, parent=True)
    position_group = cmds.group(control, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PLC', 'GRP'))
    cmds.matchTransform(position_group, controlledNode)
    cmds.parent(position_group, parent[0])
    cmds.parent(controlledNode, control)
    return position_group, control
    
