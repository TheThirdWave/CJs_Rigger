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

def createMatrixSwitch(parent1, parent2, child):
    blend_matrix = cmds.createNode('blendMatrix', name='{0}_BLND_SWTCHM'.format(child))
    cmds.connectAttr('{0}.worldMatrix[0]'.format(parent1), '{0}.inputMatrix'.format(blend_matrix))
    cmds.connectAttr('{0}.worldMatrix[0]'.format(parent2), '{0}.target[0].targetMatrix'.format(blend_matrix))
    mult_matrix, matrix_decompose = constrainByMatrix('{0}.outputMatrix'.format(blend_matrix), child)
    return blend_matrix, mult_matrix, matrix_decompose

def constrainTransformByMatrix(parent, child, maintain_offset=False):
    mult_matrix, matrix_decompose = constrainByMatrix('{0}.worldMatrix'.format(parent), child)
    if maintain_offset:
        offset_matrix = getLocalOffset(parent, child)
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix(i, j) for i in range(4) for j in range(4)], type="matrix")

    return mult_matrix, matrix_decompose

def constrainByMatrix(parentMatrix, childTransform, maintain_offset=False):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(childTransform))

    cmds.connectAttr(parentMatrix, '{0}.matrixIn[1]'.format(mult_matrix))
    cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(childTransform), '{0}.matrixIn[2]'.format(mult_matrix))
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(childTransform))
    cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.inputMatrix'.format(matrix_decompose))
    cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(childTransform))
    cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(childTransform))
    cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(childTransform))

    if maintain_offset:
        print(parentMatrix)
        parent_mMatrix = getMMatrixFromList(cmds.getAttr(parentMatrix))
        print([parent_mMatrix(i, j) for i in range(4) for j in range(4)])
        child_mMatrix = getMMatrixFromList(cmds.getAttr('{0}.worldMatrix'.format(childTransform)))
        print([child_mMatrix(i, j) for i in range(4) for j in range(4)])
        offset_matrix = child_mMatrix * parent_mMatrix.inverse()
        print([offset_matrix(i, j) for i in range(4) for j in range(4)])
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix(i, j) for i in range(4) for j in range(4)], type="matrix")

        
    return mult_matrix, matrix_decompose

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

def getLocalOffset(parent, child):
    parentWorldMatrix = getDagPath(parent).inclusiveMatrix()
    childWorldMatrix = getDagPath(child).inclusiveMatrix()

    return childWorldMatrix * parentWorldMatrix.inverse()

def getMMatrixFromList(list_matrix):
    m_mat = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(list_matrix, m_mat)
    return m_mat

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
    position_group = cmds.group(control, name='{0}_{1}_{2}_{3}_{4}'.format(prefix, component_name, joint_name, 'PLC', 'GRP'), parent=parent[0])
    cmds.matchTransform(position_group, controlledNode)
    cmds.parent(controlledNode, control)
    return position_group, control
    
