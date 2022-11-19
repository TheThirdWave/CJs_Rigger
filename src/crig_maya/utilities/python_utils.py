import maya.cmds as cmds
import maya.OpenMaya as om


def setNodesFromDict(node_dict):
    for name, attrs in node_dict.items():
        for attr, data in attrs.items():
            cmds.setAttr('{0}.{1}'.format(name, attr), data)


def generate_component_base(component_name, component_prefix):
    groups = {}
    groups['component_group'] = cmds.group(name='{0}_{1}_GRP'.format(component_prefix, component_name), parent='rig_GRP', empty=True)
    groups['output_group'] = cmds.group(name='output_GRP', parent=groups['component_group'], empty=True)
    groups['input_group'] = cmds.group(name='input_GRP', parent=groups['component_group'], empty=True)
    groups['controls_group'] = cmds.group(name='controls_GRP', parent=groups['component_group'], empty=True)
    groups['deform_group'] = cmds.group(name='deform_GRP', parent=groups['component_group'], empty=True)
    return groups

def constrainByMatrix(parent, child, maintain_offset=False):
    mult_matrix = cmds.createNode('multMatrix', name='{0}_MCNST_MMULT'.format(child))
    if maintain_offset:
        offset_matrix = getLocalOffset(parent, child)
        cmds.setAttr('{0}.matrixIn[0]'.format(mult_matrix), [offset_matrix(i, j) for i in range(4) for j in range(4)], type="matrix'")

    cmds.connectAttr('{0}.worldMatrix'.format(parent), '{0}.matrixIn[1]'.format(mult_matrix))
    cmds.connectAttr('{0}.parentInverseMatrix[0]'.format(child), '{0}.matrixIn[2]'.format(mult_matrix))
    matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(child))
    cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.inputMatrix'.format(matrix_decompose))
    cmds.connectAttr('{0}.outputRotate'.format(matrix_decompose), '{0}.rotate'.format(child))
    cmds.connectAttr('{0}.outputScale'.format(matrix_decompose), '{0}.scale'.format(child))
    cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.translate'.format(child))
    return mult_matrix, matrix_decompose

def getNodeNameParts(node):
    component_part = node.split('_', 2)
    prefix = component_part[0]
    component_name = component_part[1]
    node_part = component_part[2].rspilt('_', 2)
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