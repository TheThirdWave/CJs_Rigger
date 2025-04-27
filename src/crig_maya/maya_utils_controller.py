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

    def generateVertexJoints(self, component, joint_data):
        # Get selected vertices.
        verts = cmds.ls(selection=True, flatten=True)
        # Sort the vertices from inner to outer (lowest X to highest X if an L component, reversed if an R)
        reversed = False
        if component.prefix == 'R':
            reversed = True
        sort_func = lambda x : cmds.xform(x, query=True, translation=True)[0]
        verts.sort(reverse=reversed, key=sort_func)
        idx = 0
        # Create/replace the joints in the component and update the relevant component properties.
        if 'numJointsVar' in joint_data:
            component.componentVars[joint_data['numJointsVar']] = len(verts)
            try:
                cmds.delete(*component.joint_dict[joint_data['jointKey']])
            except:
                print('CREATE VERTEX JOINT: could not delete {0}_{1} {2} joints.'.format(component.prefix, component.name, joint_data['name']))
            for vert in verts:
                new_joint = cmds.joint(
                    component.joint_dict['baseJoint'],
                    name='{0}_{1}_{2}_{3}_BND_JNT'.format(component.prefix, component.name, joint_data['name'], idx),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.joint_dict[joint_data['jointKey']].append(new_joint)
                idx += 1
        else:
            try:
                    cmds.delete(component.joint_dict[joint_data['jointKey']])
            except:
                print('CREATE VERTEX JOINT: could not delete {0}_{1} {2} joint.'.format(component.prefix, component.name, joint_data['name']))
            for vert in verts:
                new_joint = cmds.joint(
                    component.joint_dict['baseJoint'],
                    name='{0}_{1}_{2}_BND_JNT'.format(component.prefix, component.name, joint_data['name']),
                    position=cmds.xform(vert, query=True, translation=True, worldSpace=True)
                )
                component.joint_dict[joint_data['jointKey']] = new_joint
                idx += 1
                break

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

    def appendSoftModDeformer(self):
        # Get vertex for softmod location.
        vertex = cmds.ls(selection=True)[0]
        #cmds.select(vertex)
        geo, vert = vertex.split('.')

        # Check for existing softmods in rig_GRP
        character, geo_name, suffix = python_utils.getGeoNameParts(geo)
        mesh_name = geo_name
        character_group = '{0}_GRP'.format(character)
        rig_group = '{0}|rig_GRP'.format(character_group)
        if not cmds.ls(rig_group):
            cmds.group(name='rig_GRP', empty=True, parent=character_group)
        softmod_group = '{0}|POST_softmods_GRP'.format(rig_group)
        if not cmds.ls(softmod_group):
            cmds.group(name='POST_softmods_GRP', empty=True, parent=rig_group)

        softmods = cmds.ls('{0}|{1}_{2}_softmod_*_PCRV'.format(softmod_group, character, geo_name))
        index = 0
        for mod in softmods:
            end_node = mod.split('|')[-1]
            character, geo_name, suffix = python_utils.getGeoNameParts(end_node)
            num = int(geo_name[-1])
            if(index <= num):
                index = num + 1

        # Get deformers on GEO
        deformers = [x for x in cmds.listHistory('Eskah_body_GEO', leaf=True) if cmds.objectType(x, isAType='geometryFilter')]

        # Find softmod combine blendshape and/or last deformer in the chain
        softmod_blendshape = '{0}_{1}_softmodcombine_BSHP'.format(character, mesh_name)
        if not softmod_blendshape in deformers:
            last_deformer = deformers[0]
            # If no existing softmod blendshape, then create one for additional softmods
            cmds.blendShape(geo, name='{0}_{1}_softmodcombine_BSHP'.format(character, mesh_name))
        else:
            last_deformer = cmds.listConnections('{0}.input[0].inputGeometry'.format(softmod_blendshape), source=True)[0]
        last_out_geo = cmds.listConnections('{0}.input[0].inputGeometry'.format(softmod_blendshape), source=True, plugs=True)[0]
        orig_geo = cmds.listConnections('{0}.originalGeometry[0]'.format(softmod_blendshape), source=True, plugs=True)[0]

        # Create the rivet
        # First get the UVs of the selected vertex
        cmds.select(vertex)
        cmds.ConvertSelectionToUVs()
        UVs = cmds.polyEditUV(query=True)

        # If uvPin node doesn't exist, create it.
        uvPin = '{0}_{1}_softmod_UVPN'.format(character, mesh_name)
        if not cmds.ls(uvPin):
            cmds.createNode('uvPin', name=uvPin)
            cmds.setAttr('{0}.normalAxis'.format(uvPin), 1)
            cmds.connectAttr(last_out_geo, '{0}.deformedGeometry'.format(uvPin))
            cmds.connectAttr(orig_geo, '{0}.originalGeometry'.format(uvPin))
            
        # Add UVs to pin coordinates
        uvIdx = python_utils.findNextAvailableMultiIndex('{0}.coordinate'.format(uvPin), 0, sub_attr='')
        cmds.setAttr('{0}.coordinate[{1}].coordinateU'.format(uvPin, uvIdx), UVs[0])
        cmds.setAttr('{0}.coordinate[{1}].coordinateV'.format(uvPin, uvIdx), UVs[1])
        cmds.setAttr('{0}.coordinate[{1}]'.format(uvPin, uvIdx), lock=True)

        # Create sofmod controls
        par_control = python_utils.makeControl('{0}_{1}_softmod_{2}_PCRV'.format(character, mesh_name, index), 0.75, 'sphere')
        cmds.setAttr('{0}.overrideEnabled'.format(par_control), True)
        cmds.setAttr('{0}.overrideColor'.format(par_control), 18)

        def_control = python_utils.makeCircleControl('{0}_{1}_softmod_{2}_CCRV'.format(character, mesh_name, index), 1, 'diamond')
        cmds.addAttr(def_control, longName='falloffRadius', attributeType='float', defaultValue=5.0, minValue=0.0, keyable=True, hidden=False)
        cmds.setAttr('{0}.overrideEnabled'.format(def_control), True)
        cmds.setAttr('{0}.overrideColor'.format(def_control), 18)

        cmds.parent(def_control, par_control)
        cmds.parent(par_control, softmod_group)
        cmds.connectAttr('{0}.outputMatrix[{1}]'.format(uvPin, uvIdx), '{0}.offsetParentMatrix'.format(par_control))

        # Create actual softmod node and hook it up.
        cmds.select(clear=True)
        softmod, softmodHandle = cmds.softMod(name='{0}_{1}_{2}_SFDF'.format(character, mesh_name, index), weightedNode=[def_control, def_control])
        #softmod = 'Eskah_body_0_SFDF'
        cmds.connectAttr(orig_geo, '{0}.originalGeometry[0]'.format(softmod))
        cmds.connectAttr(last_out_geo, '{0}.input[0].inputGeometry'.format(softmod))
        last_target_idx = python_utils.findNextAvailableMultiIndex('{0}.inputTarget[0].inputTargetGroup'.format(softmod_blendshape), 0, sub_attr='inputTargetItem[6000].inputGeomTarget')
        cmds.connectAttr('{0}.outputGeometry[0]'.format(softmod), '{0}.inputTarget[0].inputTargetGroup[{1}].inputTargetItem[6000].inputGeomTarget'.format(softmod_blendshape, last_target_idx))
        cmds.setAttr('{0}.weight[{1}]'.format(softmod_blendshape, last_target_idx), 1.0)
        cmds.connectAttr('{0}.worldInverseMatrix[0]'.format(par_control), '{0}.bindPreMatrix'.format(softmod))
        matrix_decompose = cmds.createNode('decomposeMatrix', name='{0}_MCNST_DCOMP'.format(par_control))
        cmds.connectAttr('{0}.worldMatrix[0]'.format(par_control), '{0}.inputMatrix'.format(matrix_decompose))
        cmds.connectAttr('{0}.outputTranslate'.format(matrix_decompose), '{0}.falloffCenter'.format(softmod))
        cmds.connectAttr('{0}.falloffRadius'.format(def_control), '{0}.falloffRadius'.format(softmod))