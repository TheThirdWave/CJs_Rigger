import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2

from .utilities import python_utils
from .. import base_controller, constants, graph_utils

class MayaController(base_controller.BaseController):

    def __init__(self):
        self._modulePath = constants.MAYA_MODULES_PATH
        self._dccPath = constants.MAYA_CRIG_PATH
        self._components = []
        self._loadedBlueprints = {}
        self._componentGraph = None
        self._bindPositionData = {}
        self._controlsData = {}
        self._utils = python_utils

    @property
    def modulePath(self):
        return self._modulePath

    @modulePath.setter
    def modulePath(self, m):
        self._modulePath = m

    @property
    def dccPath(self):
        return self._dccPath

    @dccPath.setter
    def dccPath(self, dcc):
        self._dccPath = dcc

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self, c):
        self._components = c

    @property
    def loadedBlueprints(self):
        return self._loadedBlueprints

    @loadedBlueprints.setter
    def loadedBlueprints(self, lb):
        self._loadedBlueprints = lb

    @property
    def componentGraph(self):
        return self._componentGraph
    
    @componentGraph.setter
    def componentGraph(self, cg):
        self._componentGraph = cg

    @property
    def bindPositionData(self):
        return self._bindPositionData

    @bindPositionData.setter
    def bindPositionData(self, m):
        self._bindPositionData = m

    @property
    def controlsData(self):
        return self._controlsData
    
    @controlsData.setter
    def controlsData(self, c):
        self._controlsData = c

    @property
    def utils(self):
        return self._utils
    
    @utils.setter
    def utils(self, u):
        self._utils = u

    def generateLocs(self):
        # First, have the modules generate their bind/location joints.
        iter = graph_utils.ComponentGraphIterator()
        iter.breadthFirstIteration(self.componentGraph, self.callCreateBindJoints)

        # Then, set those joints to the saved positions (if any)
        for component, data in self.bindPositionData.items():
            python_utils.setNodesFromDict(data)

    def callCreateBindJoints(self, component):
        # Create all the basic groups components are assumed to have.
        component.generateComponentBase()
        # Create individual bind joints.
        component.createBindJoints()
        # We have to initialize the components input/output custom attrs so they can be connected later, even if the component rig hasn't been created yet.
        component.initializeInputandoutputAttrs()

    def generateJoints(self):
        #We generate and connect the control rigs from the root down to ensure that
        #Parents are always created before we connect them to their children.  Otherwise,
        #the data won't be there when the child components are created which will mess up
        #any intended offsets in the child components.
        #
        #The parent/child relationships are defined in the template.
        iter = graph_utils.ComponentGraphIterator()
        iter.breadthFirstIteration(self.componentGraph, self.callControlRigAndConnect)

        #After the initial connections are made, if there are any special cases we handle them here.
        self.handleParentConnections()

        #Attributes that were just copied between components rather than directly plugged in might not have been
        #initialized properly due to ordering issues.  We re-copy them here in order to make sure they're correct.
        self.refreshCopiedAttrs()

        #After all the parent-child relationships are propagated properly, loop through again to set up
        #The attribute limits.
        self.propagateLimits()

        #Similarly, we have to wait to hook up any "parent" type attributes until after everyting else is made
        #because otherwise the offsets will be wrong for any bottom-up connections.
        self.activateParentAttrs()

        #Load in the saved out curve data for the controls (or I guess any curve under the controls )
        self.updateControlCurves()
        #Load the saved out driven key data for the KEY joints
        self.createDrivenKeys()
        #Load saved out attrs
        self.setSavedAttrs()

        # Handle any special bindings to the geometry.
        # You'd think this would be in the bindSkin function, but it's not.  For reasons.
        self.handleSpecialBindOps()

        self.setControlColors()


    def callControlRigAndConnect(self, component):
        component.createControlRig()
        self.connectModuleToChildren(component)


    # Loads skin data from the bind_skin .json file and binds it to the bind joints
    def bindSkin(self, skin_data_path):
        self.loadSmoothBind(skin_data_path)


    def handleParentConnections(self):
        for component in self.components:
            for child in component.children:
                for ccomponent in self.components:
                    if self.isComponent(child['childName'], child['childPrefix'], ccomponent):
                        self.connectParentLogic(child, ccomponent, component)


    def refreshCopiedAttrs(self):
        for component in self.components:
            component.refreshCopiedAttrs()


    def handleSpecialBindOps(self):
        for component in self.components:
            for bind in component.geomData:
                if bind['bindType'] == 'offsetParentMatrix':
                    self.offsetParentMatrixBind(component, bind)
                elif bind['bindType'] == 'keepChildPositions':
                    self.keepChildPositionsBind(component, bind)
                else:
                    constants.RIGGER_LOG.error('Unknown component bindGeometry type {0} in component {1}!  I don\'t actually use this for much.'.format(bind['bindType'], component.name))

    def setControlColors(self):
        controls = cmds.ls('*_CTL_CRV')
        for control in controls:
            prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(control)
            cmds.setAttr('{0}.overrideEnabled'.format(control), 1)
            cmds.setAttr('{0}.overrideRGBColors'.format(control), 1)
            if prefix == 'C':
                cmds.setAttr('{0}.overrideColorRGB'.format(control), 1.0, 1.0, 0.0)
            elif prefix == 'R':
                cmds.setAttr('{0}.overrideColorRGB'.format(control), 1.0, 0.0, 0.0)
            else:
                cmds.setAttr('{0}.overrideColorRGB'.format(control), 0.0, 0.0, 1.0)

    
    def offsetParentMatrixBind(self, component, bindData):
        geometry_name = '{0}_{1}'.format(component.prefix, bindData['bindGeo'])
        joint_name = '{0}_{1}_{2}'.format(component.prefix, component.name, bindData['bindJoint'])
        python_utils.constrainTransformByMatrix(geometry_name, joint_name, False, True)
        python_utils.zeroOutLocal(joint_name)


    def keepChildPositionsBind(self, component, bindData):
        geometry_name = '{0}_{1}'.format(component.prefix, bindData['bindGeo'])
        joint_name = '{0}_{1}_{2}'.format(component.prefix, component.name, bindData['bindJoint'])
        children = [ { 'name': x } for x in cmds.listRelatives(joint_name, allDescendents=True, type='transform') ]
        for child in children:
            child['translation'] = cmds.xform(child['name'], query=True, worldSpace=True, translation=True)
        python_utils.constrainTransformByMatrix(geometry_name, joint_name, False, True)
        python_utils.zeroOutLocal(joint_name)
        for child in children:
            cmds.xform(child['name'], worldSpace=True, translation=child['translation'])

    def loadSmoothBind(self, skin_data_path):
        bind_data = self.loadJSON(skin_data_path)
        for shape, data in bind_data.items():
            bind_joints = []
            for vertex, touple in data.items():
                [bind_joints.append(x[0]) for x in touple if x[0] not in bind_joints and cmds.ls(x[0])]
            skinCluster = mel.eval('findRelatedSkinCluster ' + shape)
            if not skinCluster:
                try:
                    skinCluster = cmds.skinCluster(bind_joints, shape, name='{0}'.format(shape.split('|')[-1].replace('GEOShape', 'SCLST')), maximumInfluences=3, dropoffRate=7, toSelectedBones=True)[0]
                except:
                    constants.RIGGER_LOG.warning('Could not bind skincluster to {0}'.format(shape))
                    continue

            for vertex, touple in data.items():
                cmds.skinPercent(skinCluster, vertex, transformValue=[x for x in touple if cmds.ls(x[0])])
        return

    def saveBindJointPositions(self, positions_path):
        position_dict = {}
        for component in self.components:
            deform_group = component.baseGroups['deform_group']
            children = cmds.listRelatives(deform_group, allDescendents=True, type='transform')
            if children:
                position_dict['{0}_{1}'.format(component.prefix, component.name)] = python_utils.dictionizeAttrs(children, constants.POSITION_SAVE_ATTRS)
        self.bindPositionData = position_dict
        self.saveJSON(positions_path, position_dict)

    def saveControlData(self, control_data_path):
        curves_dict = {}
        keys_dict = {}
        attrs_dict = {}
        for component in self.components:
            controls_group = component.baseGroups['controls_group']
            children = cmds.listRelatives(controls_group, allDescendents=True, type='transform')
            for child in children:
                if len(child.split('_')) <= 1:
                    continue
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(child)
                if node_type == 'CRV' and node_purpose == 'CTL':
                    if '{0}_{1}'.format(component.prefix, component.name) not in curves_dict:
                        curves_dict['{0}_{1}'.format(component.prefix, component.name)] = {}
                    curves_dict['{0}_{1}'.format(component.prefix, component.name)][child] = python_utils.getCurveData(child)
                if node_purpose == 'KEY' or node_purpose == 'CTL':
                    if '{0}_{1}'.format(component.prefix, component.name) not in keys_dict:
                        keys_dict['{0}_{1}'.format(component.prefix, component.name)] = {}
                    keys = python_utils.getDrivenKeys(child)
                    if keys:
                        keys_dict['{0}_{1}'.format(component.prefix, component.name)][child] = keys
                if cmds.attributeQuery(constants.SAVE_ATTR_LIST_ATTR, node=child, exists=True):
                    # If there are attributes to save, we save them out.
                    attribute_string = cmds.getAttr('{0}.{1}'.format(child, constants.SAVE_ATTR_LIST_ATTR))
                    attribute_list = attribute_string.split(',')
                    dictionized_attrs = python_utils.dictionizeAttrs([child], attribute_list, type=True)
                    if '{0}_{1}'.format(component.prefix, component.name) not in attrs_dict:
                        attrs_dict['{0}_{1}'.format(component.prefix, component.name)] = {}
                    attrs_dict['{0}_{1}'.format(component.prefix, component.name)][child] = dictionized_attrs[child]
                    # Save out the list of saved attributes.
                    attrs_dict['{0}_{1}'.format(component.prefix, component.name)][child][constants.SAVE_ATTR_LIST_ATTR] = {}
                    attrs_dict['{0}_{1}'.format(component.prefix, component.name)][child][constants.SAVE_ATTR_LIST_ATTR]['data'] = attribute_string
                    attrs_dict['{0}_{1}'.format(component.prefix, component.name)][child][constants.SAVE_ATTR_LIST_ATTR]['type'] = 'string'
        self.controlsData[constants.CONTROL_DATA_KEYS.curves] = curves_dict
        self.controlsData[constants.CONTROL_DATA_KEYS.drivenKeys] = keys_dict
        self.controlsData[constants.CONTROL_DATA_KEYS.attributes] = attrs_dict
        self.saveJSON(control_data_path, self.controlsData)

    def saveBindSkinData(self, bind_path):
        geo_transforms = python_utils.getRigGeo()
        everything_in_the_rig = cmds.listRelatives(constants.DEFAULT_GROUPS.rig, allDescendents=True, type='transform')
        for thing in everything_in_the_rig:
            if cmds.attributeQuery(constants.BOUND_GEO_ATTR, node=thing, exists=True):
                    geo_transforms.append(thing)

        bindDict = {}
        for transform in geo_transforms:
            shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
            skinClusters = [x for x in cmds.listHistory(shape) if cmds.nodeType(x) == "skinCluster" ]
            if skinClusters:
                bindDict[shape] = self.getVertexWeights(shape, skinClusters[0])

        self.bindSkinPath = bind_path
        self.saveJSON(bind_path, bindDict)
        return

    def connectModuleToChildren(self, module):
        for child in module.children:
                # First we connect up all the attributes.
                self.connectModuleAttrs(child, module)

    def updateControlCurves(self):
        for component, component_data in self.controlsData['curves'].items():
            for name in component_data:
                if cmds.ls(name):
                    curve = om2.MFnNurbsCurve(python_utils.getDagPath(name))
                    curve.setCVPositions(component_data[name]['points'])
                    curve.setKnots(component_data[name]['knots'], 0 , len(component_data[name]['knots']) - 1)
                    curve.updateCurve()

    def createDrivenKeys(self):
        components = self.controlsData[constants.CONTROL_DATA_KEYS.drivenKeys]
        for component, nodes in components.items():
            for node, attrs in nodes.items():
                if cmds.ls(node):
                    for attr, dict in attrs.items():
                        if 'driver' in dict:
                            for i in range(0, len(dict['keyframes']), 2):
                                cmds.setDrivenKeyframe(attr, currentDriver=dict['driver'], driverValue=dict['keyframes'][i], value=dict['keyframes'][i + 1])
                            index_num = 0
                            for i in range(0, len(dict['keytangents']), 4):
                                cmds.keyTangent(attr, absolute=True, inAngle=dict['keytangents'][i], outAngle=dict['keytangents'][i+1], inTangentType=dict['keytangents'][i+2], outTangentType=dict['keytangents'][i+3], index=(index_num, index_num))
                                index_num += 1
                            cmds.setInfinity(attr, preInfinite=dict['infinites'][0], postInfinite=dict['infinites'][1])
                        else:
                            for driver, keyData in dict.items():
                                for i in range(0, len(keyData['keyframes']), 2):
                                    cmds.setDrivenKeyframe(attr, currentDriver=driver, driverValue=keyData['keyframes'][i], value=keyData['keyframes'][i + 1])
                                index_num = 0
                                for i in range(0, len(keyData['keytangents']), 4):
                                    cmds.keyTangent(attr, absolute=True, inAngle=keyData['keytangents'][i], outAngle=keyData['keytangents'][i+1], inTangentType=keyData['keytangents'][i+2], outTangentType=keyData['keytangents'][i+3], index=(index_num, index_num))
                                    index_num += 1
                                cmds.setInfinity(attr, preInfinite=keyData['infinites'][0].lower(), postInfinite=keyData['infinites'][1].lower())

    def setSavedAttrs(self):
        components = self.controlsData[constants.CONTROL_DATA_KEYS.attributes]
        for component, nodes in components.items():
            for node, attrs in nodes.items():
                if cmds.ls(node):
                    for name, value in attrs.items():
                        if not cmds.attributeQuery(name, node=node, exists=True):
                            try:
                                if value['type'] == 'string':
                                    cmds.addAttr(node, longName=name, dataType=value['type'])
                                else:
                                    cmds.addAttr(node, longName=name, attributeType=value['type'])
                            except:
                                constants.RIGGER_LOG.warning('WARNING: Could not add attribute {0} of type {1} to {2}'.format(name, value['type'], node))

                        try:
                            cmds.setAttr('{0}.{1}'.format(node, name), value['data'], type=value['type'])
                        except:
                            # This is probably bad form but I'm not making a list of all the maya data types that require the "type" flag vs all the types that don't
                            try:
                                cmds.setAttr('{0}.{1}'.format(node, name), value['data'])
                            except:
                                constants.RIGGER_LOG.warning('WARNING: Could not set attribute "{0}.{1} to {2}'.format(node, name, value['data']))

    def connectParentLogic(self, child, childModule, parentModule):
        if 'connectionType' not in child:
            constants.RIGGER_LOG.info('{0} connection to child {1} not defined, skipping connection.'.format(parentModule.getFullName(), child['childName']))
            return
        
        # I'm not actually cleaning the inputs but I don't want nothing to work because I capitalized something.
        connection_type = child['connectionType'].lower()

        if connection_type == constants.CONNECTION_TYPES.parent:
            # The default case is covered by "connectModuleAttrs()"
            return
        elif connection_type == constants.CONNECTION_TYPES.translateConstraint:
            out_world = '{0}_output_GRP.{1}'.format(parentModule.getFullName(), constants.DEFAULT_ATTRS.outWorld)
            in_world = '{0}_input_GRP.{1}'.format(child['childName'], constants.DEFAULT_ATTRS.inWorld)
            out_inv_world = '{0}_output_GRP.{1}'.format(parentModule.getFullName(), constants.DEFAULT_ATTRS.outInverseWorld)
            in_inv_world = '{0}_input_GRP.{1}'.format(child['childName'], constants.DEFAULT_ATTRS.inInverseWorld)
            try:
                cmds.disconnectAttr(out_world, in_world)
            except:
                constants.RIGGER_LOG.error('{0} and {1} could not be disconnected. This is weird and shouldn\'t happen here.(connectParentLogic)'.format(out_world, in_world))
            python_utils.decomposeAndRecompose(out_world, in_world, ['translate'])
            try:
                cmds.disconnectAttr(out_inv_world, in_inv_world)
            except:
                constants.RIGGER_LOG.error('{0} and {1} could not be disconnected. This is weird and shouldn\'t happen here.(connectParentLogic)'.format(out_world, in_world))
            python_utils.decomposeAndRecompose(out_inv_world, in_inv_world, ['translate'])
        elif connection_type == constants.CONNECTION_TYPES.spaceSwitch:
            self.handleSpaceSwitch(child, childModule, parentModule)
        else:
            constants.RIGGER_LOG.info('{0} connection to child {1} not defined, skipping connection.'.format(parentModule.getFullName(), child['childName']))
        
        return

    def handleSpaceSwitch(self, child, childModule, parentModule):
        out_world = '{0}_output_GRP.{1}'.format(parentModule.getFullName(), constants.DEFAULT_ATTRS.outWorld)
        in_world = '{0}_input_GRP.{1}'.format(childModule.getFullName(), constants.DEFAULT_ATTRS.inWorld)
        out_inv_world = '{0}_output_GRP.{1}'.format(parentModule.getFullName(), constants.DEFAULT_ATTRS.outInverseWorld)
        in_inv_world = '{0}_input_GRP.{1}'.format(childModule.getFullName(), constants.DEFAULT_ATTRS.inInverseWorld)
        in_switch_enum = '{0}_input_GRP.{1}'.format(childModule.getFullName(), constants.DEFAULT_ATTRS.spaceSwitch)
        input_group = '{0}_input_GRP'.format(childModule.getFullName())

        blend_matrix_name = '{0}_SPC_SWTCHM'.format(childModule.getFullName())
        child_in_connections = cmds.listConnections(in_world, source=True, destination=False, plugs=True)
        if not child_in_connections or not (blend_matrix_name in child_in_connections[0]):
            # create matrix switch
            blend_matrix = cmds.createNode('blendMatrix', name=blend_matrix_name)
            # the in_world can only have one input and we don't want it to be whatever it was before.
            cmds.connectAttr('{0}.outputMatrix'.format(blend_matrix_name), in_world, force=True)

        # Add parent to matrix switch.
        # find the next-available target slot
        free_index = python_utils.findNextAvailableMultiIndex('{0}.target'.format(blend_matrix_name), 0, 'targetMatrix')

        # Find the 'main' parent by following the source of the in_inv_world plug and grab the world space
        # the spaceswitch won't work if this isn't connected by one of the parents
        main_parent_inv_world_attr = cmds.connectionInfo(in_inv_world, sourceFromDestination=True)
        main_parent = main_parent_inv_world_attr.split('.')[0]
        main_parent_world_attr = '{0}.{1}'.format(main_parent, constants.DEFAULT_ATTRS.outWorld)
        # Create parent mult-matrix
        mult_matrix = python_utils.createParentSwitchMult(out_world, out_inv_world, main_parent_world_attr, '{0}_{1}'.format(childModule.getFullName(), free_index))
        # Create new enum value
        # First check if any values have already been created
        input_depend_node = python_utils.getDependNode(input_group)
        dependNodeFn = om2.MFnDependencyNode(input_depend_node)
        attrFn = om2.MFnEnumAttribute(dependNodeFn.attribute(constants.DEFAULT_ATTRS.spaceSwitch))
        max = attrFn.getMax()
        min = attrFn.getMin()
        # If the minimum is higher than the max, no enum values have been defined for the attr yet, this would pose a problem if I
        # was doing anything else with the attr, but the default max value for an undefined enum attr is -1, so it all works out.
        # Because you can define an enum's value to whatever you want, it's possible for the next available enum value to actually be
        # between the min and the max, which means we'd have to loop through all the values until we threw an exception to find the
        # lowest free slot.  But that's work, so we'll just add the new value as "max + 1"
        next_value = max + 1
        attrFn.addField(child['spaceName'], next_value)

        # We also have to update whatever proxies are downstream of the switch enum because that doesn't happen automatically, which is dumb.
        downstream_connections = cmds.connectionInfo(in_switch_enum, destinationFromSource=True)
        for connection in downstream_connections:
            connection_node = connection.split('.')[0]
            connection_attr = connection.split('.')[1]
            connection_depend_node = python_utils.getDependNode(connection_node)
            dependNodeFn = om2.MFnDependencyNode(connection_depend_node)
            attrObj = dependNodeFn.attribute(connection_attr)
            # Basically we assume if it's connected to a downstream enum attribute, we want to update that enum as well.
            if attrObj.hasFn(om2.MFn.kEnumAttribute):
                attrFn = om2.MFnEnumAttribute(dependNodeFn.attribute(connection_attr))
                attrFn.addField(child['spaceName'], next_value)

        # Next we create the conditional that will switch on the space matrix if the enum on the control is set to it.
        switch_condition = cmds.createNode('condition', name='{0}_{1}_SWTCH_CND'.format(childModule.getFullName(), free_index))
        cmds.setAttr('{0}.colorIfTrueR'.format(switch_condition), 1)
        cmds.setAttr('{0}.colorIfFalseR'.format(switch_condition), 0)
        cmds.connectAttr(in_switch_enum, '{0}.firstTerm'.format(switch_condition))
        cmds.setAttr('{0}.secondTerm'.format(switch_condition), next_value)

        # Connect everything up to the matrix blend
        cmds.connectAttr('{0}.matrixSum'.format(mult_matrix), '{0}.target[{1}].targetMatrix'.format(blend_matrix_name, free_index))
        cmds.connectAttr('{0}.outColorR'.format(switch_condition), '{0}.target[{1}].useMatrix'.format(blend_matrix_name, free_index))

    def handleInternalSpaceSwitch(self, parentMatrix, enum_name, childTransform, switch_attr_name):
        offsetParentMatrix = '{0}.offsetParentMatrix'.format(childTransform)
        DG_parent = cmds.listRelatives(childTransform, parent=True)[0]

        # Because of the way I've got the internal attributes set up, the internal space switch attribute will have been
        # initialized to the wrong attr type, so we check the attribute to see if it's an enum, and if not, we replace
        # the attribute.
        if cmds.getAttr('{0}.{1}'.format(childTransform, switch_attr_name), type=True) != 'enum':
            cmds.deleteAttr('{0}.{1}'.format(childTransform, switch_attr_name))
            cmds.addAttr(childTransform, longName=switch_attr_name, attributeType='enum', keyable=True, hidden=False)
        
        # Then, we check to see if the offsetParentMatrix is connected to anything, and if so, what.
        oPMIncomingConnection = cmds.connectionInfo(offsetParentMatrix, sourceFromDestination=True)
        
        # If it isn't connected to anything, or if what it's connected to isn't the expected space switch, then we create the space switch.
        make_new_switch = True
        space_switch_name = '{0}_SPC_SWTCHM'.format(childTransform)
        if oPMIncomingConnection:
            incoming_node, incoming_attr = oPMIncomingConnection.split('.')
            if incoming_node == space_switch_name:
                make_new_switch = False
        
        if make_new_switch:
            matrix_switch = cmds.createNode('blendMatrix', name=space_switch_name)
            # We make the default/initial value of the space switch either the identity matrix, or whatever
            # the pre-existing connection to the offsetParentMatrix was.
            if oPMIncomingConnection:
                default_parent_matrix = oPMIncomingConnection
            else:
                identity_mat_mult = cmds.createNode('multMatrix', name='{0}_0_IDNT_MMULT'.format(childTransform))
                default_parent_matrix = '{0}.matrixSum'.format(identity_mat_mult)
            cmds.connectAttr('{0}.outputMatrix'.format(matrix_switch), offsetParentMatrix, force=True)
            python_utils.addParentToSpaceSwitch(
                '{0}.{1}'.format(childTransform, switch_attr_name),
                'off',
                default_parent_matrix,
                '{0}.worldMatrix'.format(DG_parent),
                '{0}.worldInverseMatrix'.format(DG_parent),
                childTransform,
                matrix_switch
            )
            cmds.connectAttr(default_parent_matrix, '{0}.target[0].targetMatrix'.format(matrix_switch), force=True)
        else:
            incoming_node, incoming_attr = oPMIncomingConnection.split('.')
            matrix_switch = incoming_node

        python_utils.addParentToSpaceSwitch(
            '{0}.{1}'.format(childTransform, switch_attr_name),
            enum_name,
            parentMatrix,
            '{0}.worldMatrix'.format(DG_parent),
            '{0}.worldInverseMatrix'.format(DG_parent),
            childTransform,
            matrix_switch
        )


    def connectModuleAttrs(self, child, module):
        for ccomponent in self.components:
            if self.isComponent(child['childName'], child['childPrefix'], ccomponent):
                for i in range(len(child['parentAttrs'])):
                    pOutput = '{0}_output_GRP.{1}'.format(module.getFullName(), child['parentAttrs'][i])
                    cInput = '{0}_input_GRP.{1}'.format(ccomponent.getFullName(), child['childAttrs'][i])
                    try:
                        cmds.connectAttr(pOutput, cInput)
                    except:
                        # If there's multiple incoming connections we let "connectParentLogic()" sort it out.
                        constants.RIGGER_LOG.warning('{0} and {1} are already connected! (This could be fine)'.format(pOutput, cInput))
                        continue
                if 'parentUpAttrs' in child:
                    for i in range(len(child['parentUpAttrs'])):
                        pInput = '{0}_input_GRP.{1}'.format(module.getFullName(), child['parentUpAttrs'][i])
                        cOutput = '{0}_output_GRP.{1}'.format(ccomponent.getFullName(), child['childUpAttrs'][i])
                        try:
                            cmds.connectAttr(cOutput, pInput)
                        except:
                            # If there's multiple incoming connections we let "connectParentLogic()" sort it out.
                            constants.RIGGER_LOG.warning('{0} and {1} are already connected! (This could be fine)'.format(cOutput, pInput))
                            continue

    
    def activateParentAttrs(self):
        for component in self.components:
            parent_group = component.baseGroups['input_group']
            for attr in component.inputAttrs:
                if 'attrConnection' in attr:
                    lower_connection_type = attr['attrConnection'].lower()
                    if lower_connection_type == constants.ATTR_CONNECTION_TYPES.parent:
                        new_attr = '{0}.{1}'.format(parent_group, attr['attrName'])
                        final_attr_path = '{0}_{1}_{2}'.format(component.prefix, component.name, attr['internalAttr'])
                        python_utils.constrainByMatrix(new_attr, final_attr_path, True, False)
                    if lower_connection_type == constants.ATTR_CONNECTION_TYPES.parentOffset:
                        new_attr = '{0}.{1}'.format(parent_group, attr['attrName'])
                        final_attr_path = '{0}_{1}_{2}'.format(component.prefix, component.name, attr['internalAttr'])
                        python_utils.constrainByMatrix(new_attr, final_attr_path, True, False)
                    if lower_connection_type == constants.ATTR_CONNECTION_TYPES.parentOffsetTranslate:
                        new_attr = '{0}.{1}'.format(parent_group, attr['attrName'])
                        final_attr_path = '{0}_{1}_{2}'.format(component.prefix, component.name, attr['internalAttr'])
                        python_utils.constrainByMatrix(new_attr, final_attr_path, True, False, ['translate'])
                    if lower_connection_type == constants.ATTR_CONNECTION_TYPES.spaceSwitch:
                        new_attr = '{0}.{1}'.format(parent_group, attr['attrName'])
                        final_attr_path = '{0}_{1}_{2}'.format(component.prefix, component.name, attr['internalAttr'])
                        # Check to see if the user has defined an attribute for the space switch
                        split_list = final_attr_path.split('.')
                        space_switch_attr = constants.DEFAULT_SPACE_SWITCH_ATTR
                        if len(split_list) > 1:
                            space_switch_attr = split_list[-1]
                            final_attr_path = split_list[0]
                        
                        # Check to see if the user has defined a name for the enum
                        enum_name = attr['attrName']
                        if 'enumName' in attr:
                            enum_name = attr['enumName']

                        self.handleInternalSpaceSwitch(new_attr, enum_name, final_attr_path, space_switch_attr)


    def propagateLimits(self):
        for component in self.components:
            for child in component.children:
                for ccomponent in self.components:
                    if self.isComponent(child['childName'], child['childPrefix'], ccomponent):
                        for i in range(len(child['parentAttrs'])):
                            # Get the parent/child connections between components, and the internal connections between the input/output groups and their
                            # internal nodes.
                            pOutput = '{0}_output_GRP.{1}'.format(component.getFullName(), child['parentAttrs'][i])
                            pInternal = [ x['internalAttr'] for x in component.outputAttrs if x['attrName'] == child['parentAttrs'][i] ][0]
                            pInternal = '{0}_{1}_{2}'.format(component.prefix, component.name, pInternal)
                            cInput = '{0}_input_GRP.{1}'.format(ccomponent.getFullName(), child['childAttrs'][i])
                            cInternal = [ x['internalAttr'] for x in ccomponent.inputAttrs if x['attrName'] == child['childAttrs'][i] ][0]
                            cInternal = '{0}_{1}_{2}'.format(ccomponent.prefix, ccomponent.name, cInternal)

                            # If the 'internalAttr' isn't actually an attr and just a node we skip it.  My fudges are catching up to me.
                            if len(cInternal.split('.')) < 2 or len(pInternal.split('.')) < 2:
                                continue
                            try:
                                # Now propagate the limits of the internal attributes to the input/output groups
                                self.copyLimits(pInternal, pOutput)
                                self.copyLimits(cInput, cInternal)
                                # Now propagate between the input/output groups (the parent output group takes precedent)
                                self.copyLimits(pOutput, cInput)
                                # Now we propagate the limits of the input/ouput groups to the internal attributes again.
                                self.copyLimits(pInternal, pOutput)
                                self.copyLimits(cInput, cInternal)
                            except:
                                    # I don't want the program crashing every time it tries to set a limit on a deleted node
                                    constants.RIGGER_LOG.warning('Could not set limits on {0}, {1}, and {2}, {3}! Maybe check that out or something.'.format(pInternal, pInput, cInternal, cOutput))
                                    continue
                        if 'parentUpAttrs' in child:
                            for i in range(len(child['parentUpAttrs'])):
                                # Now we do everything but in reverse for the child->parent attrs
                                pInput = '{0}_input_GRP.{1}'.format(component.getFullName(), child['parentUpAttrs'][i])
                                pInternal = [ x['internalAttr'] for x in component.inputAttrs if x['attrName'] == child['parentUpAttrs'][i] ][0]
                                pInternal = '{0}_{1}_{2}'.format(component.prefix, component.name, pInternal)
                                cOutput = '{0}_output_GRP.{1}'.format(ccomponent.getFullName(), child['childUpAttrs'][i])
                                cInternal = [ x['internalAttr'] for x in ccomponent.outputAttrs if x['attrName'] == child['childUpAttrs'][i] ][0]
                                cInternal = '{0}_{1}_{2}'.format(ccomponent.prefix, ccomponent.name, cInternal)

                                # If the 'internalAttr' isn't actually an attr and just a node we skip it.  My fudges are catching up to me.
                                if len(cInternal.split('.')) < 2 or len(pInternal.split('.')) < 2:
                                    continue

                                try:
                                    # Now propagate the limits of the internal attributes to the input/output groups
                                    self.copyLimits(pInternal, pInput)
                                    self.copyLimits(cInternal, cOutput)
                                    # Now propagate between the input/output groups (the child output group takes precedent)
                                    self.copyLimits(cOutput, pInput)
                                    # Now we propagate the limits of the input/ouput groups to the internal attributes again.
                                    self.copyLimits(pInput, pInternal)
                                    self.copyLimits(cInternal, cOutput)
                                except:
                                    # I don't want the program crashing every time it tries to set a limit on a deleted node
                                    constants.RIGGER_LOG.warning('Could not set limits on {0}, {1}, and {2}, {3}! Maybe check that out or something.'.format(pInternal, pInput, cInternal, cOutput))
                                    continue


    def copyLimits(self, parentAttr, childAttr):
        pnode, pattr = parentAttr.split('.')
        cnode, cattr = childAttr.split('.')
        if cmds.attributeQuery(pattr, node=pnode, maxExists=True):
            # We only set the limits for dynamic attrs.
            if childAttr in cmds.listAttr(cnode, userDefined=True):
                max = cmds.attributeQuery(pattr, node=pnode, maximum=True)[0]
                cmds.addAttr(childAttr, edit=True, maxValue=max)
        elif cmds.attributeQuery(cattr, node=cnode, maxExists=True):
            # We only set the limits for dynamic attrs.
            if parentAttr in cmds.listAttr(pnode, userDefined=True):
                max = cmds.attributeQuery(cattr, node=cnode, maximum=True)[0]
                cmds.addAttr(parentAttr, edit=True, maxValue=max)

        if cmds.attributeQuery(pattr, node=pnode, minExists=True):
            # We only set the limits for dynamic attrs.
            if childAttr in cmds.listAttr(cnode, userDefined=True):
                min = cmds.attributeQuery(pattr, node=pnode, minimum=True)[0]
                cmds.addAttr(childAttr, edit=True, minValue=min)
        elif cmds.attributeQuery(cattr, node=cnode, minExists=True):
            # We only set the limits for dynamic attrs.
            if parentAttr in cmds.listAttr(pnode, userDefined=True):
                min = cmds.attributeQuery(cattr, node=cnode, minimum=True)[0]
                cmds.addAttr(parentAttr, edit=True, minValue=min)


    def getVertexWeights(self, shape, skinCluster, ignoreThreshold=0.001):
        if cmds.objectType(shape) == 'mesh':
            vertices = cmds.ls('{0}.vtx[*]'.format(shape), flatten=True)
        else:
            vertices = cmds.ls('{0}.cv[*]'.format(shape), flatten=True)
        weightDict = {}
        for vertex in vertices:
            influenceNames = cmds.skinPercent(skinCluster, vertex, query=True, transform=None, ignoreBelow=ignoreThreshold)
            influenceValues = cmds.skinPercent(skinCluster, vertex, query=True, value=True, ignoreBelow=ignoreThreshold)
            if influenceNames and influenceValues:
                weightDict[vertex] = list(zip(influenceNames, influenceValues))
        return weightDict
