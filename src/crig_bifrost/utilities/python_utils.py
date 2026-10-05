import math
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import maya.api.OpenMaya as om2

from ... import constants

def publishModule(graph, nodeName, publishName):
    cmds.vnnCompound(graph, nodeName, publish=[constants.BIFROST_MODULES_PATH, constants.BIFROST_NODE_NAMESPACE, publishName, False])

def getNodeNameParts(node):
    parent_path, node_part = node.rsplit('/', 1)
    node_part = node_part.rsplit('_', 2)
    joint_name = node_part[0]
    node_purpose = node_part[1]
    node_type = node_part[2]
    return parent_path, joint_name, node_purpose, node_type

def attrConnectDown(higherLevelAttr, lowerLevelAttr):
    path_array = [x for x in lowerLevelAttr.node.parent.split('/') if x not in higherLevelAttr.node.path.split('/')]
    top_node = higherLevelAttr.node
    for node in path_array:
        new_path = '/' + node
        top_node[higherLevelAttr.name] >> top_node[new_path + '.' + higherLevelAttr.name]
        top_node = top_node[new_path]
    top_node[higherLevelAttr.name] >> lowerLevelAttr

def attrConnectUp(lowerLevelAttr, higherLevelAttr):
    bottom_attr = lowerLevelAttr
    relative_path = [x for x in lowerLevelAttr.node.parent.split('/') if x not in higherLevelAttr.node.path.split('/')]
    
    for i in range(len(relative_path)):
        parent_node = higherLevelAttr.node['/' + '/'.join(relative_path)]
        if not parent_node[higherLevelAttr.name].exists:
            parent_node[higherLevelAttr.name].add('output', lowerLevelAttr.type)
        bottom_attr >> parent_node[higherLevelAttr.name]
        bottom_attr = parent_node[higherLevelAttr.name]
        relative_path.pop()
    if not higherLevelAttr.exists:
        higherLevelAttr.add('output', lowerLevelAttr.type)
    bottom_attr >> higherLevelAttr
