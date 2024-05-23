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

    def generateVertexJoints(self, component, joint_side):
        # Get selected vertices.
        verts = cmds.ls(selection=True, flatten=True)
        # Sort the vertices from inner to outer (lowest X to highest X if an L component, reversed if an R)
        reversed = False
        if component.prefix == 'R':
            reversed = True
        sort_func = lambda x : cmds.xform(x, query=True, translation=True)[0]
        verts.sort(reverse=reversed, key=sort_func)
        idx = 0
        if joint_side == 'upper':
            component.componentVars['numUpper'] = len(verts)
            try:
                cmds.delete(*component.upper_joints)
            except:
                print('CREATE VERTEX JOINT: could not delete component (which one I don\'t know).')
            for vert in verts:
                new_joint = cmds.joint(
                    component.base_joint,
                    name='{0}_{1}_upper_{2}_BND_JNT'.format(component.prefix, component.name, idx),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.upper_joints.append(new_joint)
                idx += 1

        elif joint_side == 'lower':
            component.componentVars['numLower'] = len(verts)
            try:
                cmds.delete(*component.lower_joints)
            except:
                print('CREATE VERTEX JOINT: could not delete component (which one I don\'t know).')
            for vert in verts:
                new_joint = cmds.joint(
                    component.base_joint,
                    name='{0}_{1}_lower_{2}_BND_JNT'.format(component.prefix, component.name, idx),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.lower_joints.append(new_joint)
                idx += 1
        
        elif joint_side == 'inner':
            try:
                cmds.delete(component.inner_corner_joint)
            except:
                print('CREATE VERTEX JOINT: could not delete component (which one I don\'t know).')
            for vert in verts:
                new_joint = cmds.joint(
                    component.base_joint,
                    name='{0}_{1}_inner_BND_JNT'.format(component.prefix, component.name),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.inner_corner_joint = new_joint
                idx += 1
                break
            
        elif joint_side == 'outer':
            try:
                cmds.delete(component.outer_corner_joint)
            except:
                print('CREATE VERTEX JOINT: could not delete component (which one I don\'t know).')
            for vert in verts:
                new_joint = cmds.joint(
                    component.base_joint,
                    name='{0}_{1}_outer_BND_JNT'.format(component.prefix, component.name),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.outer_corner_joint = new_joint
                idx += 1
                break

        elif joint_side == 'base':
            component.componentVars['numJoints'] = len(verts)
            try:
                cmds.delete(*component.bind_joints)
            except:
                print('CREATE VERTEX JOINT: could not delete {0}_{1} joints.'.format(component.prefix, component.name))
            for vert in verts:
                new_joint = cmds.joint(
                    component.bind_joints_group,
                    name='{0}_{1}_base_{2}_BND_JNT'.format(component.prefix, component.name, idx),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.bind_joints.append(new_joint)
                idx += 1
        pass

    def markAttrsForSaving(self):
        selected_node = cmds.ls(selection=True)[-1]
        selected_attrs = cmds.channelBox('mainChannelBox', query=True, selectedMainAttributes=True)
        if not cmds.attributeQuery(constants.SAVE_ATTR_LIST_ATTR, node=selected_node, exists=True):
            cmds.addAttr(selected_node, longName=constants.SAVE_ATTR_LIST_ATTR, dataType='string')

        if selected_attrs:
            existingAttrs = cmds.getAttr('{0}.{1}'.format(selected_node, constants.SAVE_ATTR_LIST_ATTR))
            if not existingAttrs:
                existing_list = selected_attrs
            else:
                existing_list = existingAttrs.split(',')
                for attr in selected_attrs:
                    if attr not in existing_list:
                        existing_list.append(attr)

            cmds.setAttr('{0}.{1}'.format(selected_node, constants.SAVE_ATTR_LIST_ATTR), ','.join(existing_list), type='string')