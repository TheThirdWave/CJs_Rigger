from maya import cmds
from maya import OpenMaya as om
from .utilities import python_utils
from .. import utils_controller, constants

class UtilsController(utils_controller.UtilsController):

    def __init__(self):
        return

    def constrainByMatrix(self):
        selection = cmds.ls(selection=True)
        if len(selection) > 2:
            constants.RIGGER_LOG.error('Cannot constrain by matrix, more than two objects selected!')
            return
        
        python_utils.constrainTransformByMatrix(selection[0], selection[1], True, False)

    def makeRLMatch(self):
        node = cmds.ls(selection=True, transforms=True)[0]
        node_children = cmds.listRelatives(node, allDescendents=True) if cmds.listRelatives(node, allDescendents=True) else []
        node_children.reverse()
        prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(node)
        if prefix != 'L' and prefix != 'R':
            constants.RIGGER_LOG.error('Cannot match component, must select an L_ or R_ object!')
            return
        opposite_prefix = ''
        if prefix == 'L':
            opposite_prefix = 'R'
        if prefix == 'R':
            opposite_prefix = 'L'
        opposite_node = cmds.ls('{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, component_name, joint_name, node_purpose, node_type), transforms=True)[0]
        opposite_children = cmds.listRelatives(opposite_node, allDescendents=True) if cmds.listRelatives(opposite_node, allDescendents=True) else []
        opposite_children.reverse()

        python_utils.setOrientJoint(opposite_node, 'yzx', 'zup')
        for joint in opposite_children:
            python_utils.setOrientJoint(joint, 'yzx', 'zup')

        cmds.matchTransform(opposite_node, node)
        i = 0
        for child in node_children:
            python_utils.copyOverMatrix('{0}.matrix'.format(child), opposite_children[i])
            i += 1

        opposite_translateX = cmds.getAttr('{0}.translateX'.format(opposite_node))
        opposite_rotateY = cmds.getAttr('{0}.rotateY'.format(opposite_node))
        opposite_rotateZ = cmds.getAttr('{0}.rotateZ'.format(opposite_node))
        cmds.setAttr('{0}.translateX'.format(opposite_node), -opposite_translateX)
        cmds.setAttr('{0}.rotateY'.format(opposite_node), -opposite_rotateY)
        cmds.setAttr('{0}.rotateZ'.format(opposite_node), -opposite_rotateZ)
        python_utils.zeroJointOrient(opposite_node)
        for joint in opposite_children:
            python_utils.zeroJointOrient(joint)
        python_utils.reverseJointChainOnX(opposite_node)

    def selectBindJoints(self):
        selection = cmds.ls('*_BND_JNT', type='joint')
        cmds.select(selection)

    def mirrorDrivenKeys(self):
        selected = cmds.ls(selection=True, transforms=True)
        for node in selected:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(node)
            # We only mirror if there's an opposite node
            if prefix == 'R':
                opposite_prefix = 'L'
            elif prefix == 'L':
                opposite_prefix = 'R'
            else:
                continue
            opposite_node = cmds.ls('{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, component_name, joint_name, node_purpose, node_type))
            if not opposite_node:
                constants.RIGGER_LOG.info('No opposite node found for {0}, skipping'.format(node))
                continue
            # Get attrs driven by keys
            driven_attrs = cmds.setDrivenKeyframe(node, query=True, driven=True)
            if not driven_attrs:
                constants.RIGGER_LOG.info('No driven attrs found for {0}, skipping'.format(opposite_node))
                continue
            # Get animCurve nodes driving attr
            for attr in driven_attrs:
                drivers = cmds.listConnections(attr, source=True, type='animCurve')
                # for each driver get the connections, then copy it and connect it to the opposite nodes.
                for driver in drivers:
                    driver_split = list(python_utils.getNodeNameParts(driver))
                    d_connections = cmds.listConnections(driver, destination=False, connections=True, plugs=True)
                    s_connections = cmds.listConnections(driver, source=False, connections=True, plugs=True)
                    opposite_driver = cmds.duplicate(driver, name='{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, driver_split[1], driver_split[2], driver_split[3], driver_split[4]))
                    for i in range(0, len(d_connections), 2):
                        driver_connection = list(python_utils.getNodeNameParts(d_connections[i]))
                        source_connection = list(python_utils.getNodeNameParts(d_connections[i + 1]))
                        if source_connection[0] == 'R':
                            source_connection[0] = 'L'
                        elif source_connection[0] == 'L':
                            source_connection[0] = 'R'
                        cmds.connectAttr(
                            '{0}_{1}_{2}_{3}_{4}'.format(source_connection[0], source_connection[1], source_connection[2], source_connection[3], source_connection[4]),
                            '{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, driver_connection[1], driver_connection[2], driver_connection[3], driver_connection[4]),
                        )
                    for i in range(0, len(s_connections), 2):
                        driver_connection = list(python_utils.getNodeNameParts(s_connections[i]))
                        dest_connection = list(python_utils.getNodeNameParts(s_connections[i + 1]))
                        if dest_connection[0] == 'R':
                            dest_connection[0] = 'L'
                        elif dest_connection[0] == 'L':
                            dest_connection[0] = 'R'
                        cmds.connectAttr(
                            '{0}_{1}_{2}_{3}_{4}'.format(opposite_prefix, driver_connection[1], driver_connection[2], driver_connection[3], driver_connection[4]),
                            '{0}_{1}_{2}_{3}_{4}'.format(dest_connection[0], dest_connection[1], dest_connection[2], dest_connection[3], dest_connection[4])
                        )

