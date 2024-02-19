import maya.cmds as cmds
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


    def callControlRigAndConnect(self, component):
        component.createControlRig()
        self.connectModuleToChildren(component)



    # Loads skin data from the bind_skin .json file and binds it to the bind joints
    def bindSkin(self, skin_data_path):
        bind_joints = cmds.ls('*_BND_JNT', type='joint')
        bind_data = self.loadJSON(skin_data_path)
        for shape, data in bind_data.items():
            skinCluster = cmds.skinCluster(bind_joints, shape, maximumInfluences=5, dropoffRate=7)[0]
            for vertex, touple in data.items():
                cmds.skinPercent(skinCluster, vertex, transformValue=touple)
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
        for component in self.components:
            controls_group = component.baseGroups['controls_group']
            children = cmds.listRelatives(controls_group, allDescendents=True, type='transform')
            for child in children:
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
        self.controlsData[constants.CONTROL_DATA_KEYS.curves] = curves_dict
        self.controlsData[constants.CONTROL_DATA_KEYS.drivenKeys] = keys_dict
        self.saveJSON(control_data_path, self.controlsData)

    def saveBindSkinData(self, bind_path):
        geo_transforms = python_utils.getRigGeo()
        bindDict = {}
        for transform in geo_transforms:
            shape = cmds.listRelatives(transform, shapes=True)[0]
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
                # Then we immediately change the IN_WORLD/END_OUT_WORLD connections because I've decided they're special and how I'm going
                # to deal with component parent/child transformation stuff.
                self.connectParentLogic(child, module)

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
                        for i in range(0, len(dict['keyframes']), 2):
                            cmds.setDrivenKeyframe(attr, currentDriver=dict['driver'], driverValue=dict['keyframes'][i], value=dict['keyframes'][i + 1])
                        index_num = 0
                        for i in range(0, len(dict['keytangents']), 4):
                            cmds.keyTangent(attr, absolute=True, inAngle=dict['keytangents'][i], outAngle=dict['keytangents'][i+1], inTangentType=dict['keytangents'][i+2], outTangentType=dict['keytangents'][i+3], index=(index_num, index_num))
                            index_num += 1
                        cmds.setInfinity(attr, preInfinite=dict['infinites'][0], postInfinite=dict['infinites'][1])

    def connectParentLogic(self, child, module):
        if 'connectionType' not in child:
            constants.RIGGER_LOG.info('{0} connection to child {1} not defined, skipping connection.'.format(module.getFullName(), child['childName']))
            return
        
        # I'm not actually cleaning the inputs but I don't want nothing to work because I capitalized something.
        connection_type = child['connectionType'].lower()

        if connection_type == constants.CONNECTION_TYPES.parent:
            # The default case is covered by "connectModuleAttrs()"
            return
        elif connection_type == constants.CONNECTION_TYPES.translateConstraint:
            out_world = '{0}_output_GRP.{1}'.format(module.getFullName(), constants.DEFAULT_ATTRS.outWorld)
            in_world = '{0}_input_GRP.{1}'.format(child['childName'], constants.DEFAULT_ATTRS.inWorld)
            out_inv_world = '{0}_output_GRP.{1}'.format(module.getFullName(), constants.DEFAULT_ATTRS.outInverseWorld)
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
        else:
            constants.RIGGER_LOG.info('{0} connection to child {1} not defined, skipping connection.'.format(module.getFullName(), child['childName']))
        
        return


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

                            # Now propagate the limits of the internal attributes to the input/output groups
                            self.copyLimits(pInternal, pOutput)
                            self.copyLimits(cInput, cInternal)
                            # Now propagate between the input/output groups (the parent output group takes precedent)
                            self.copyLimits(pOutput, cInput)
                            # Now we propagate the limits of the input/ouput groups to the internal attributes again.
                            self.copyLimits(pInternal, pOutput)
                            self.copyLimits(cInput, cInternal)
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

                                # Now propagate the limits of the internal attributes to the input/output groups
                                self.copyLimits(pInternal, pInput)
                                self.copyLimits(cInternal, cOutput)
                                # Now propagate between the input/output groups (the child output group takes precedent)
                                self.copyLimits(cOutput, pInput)
                                # Now we propagate the limits of the input/ouput groups to the internal attributes again.
                                self.copyLimits(pInput, pInternal)
                                self.copyLimits(cInternal, cOutput)


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
        vertices = cmds.ls('{0}.vtx[*]'.format(shape), flatten=True)
        weightDict = {}
        for vertex in vertices:
            influenceNames = cmds.skinPercent(skinCluster, vertex, query=True, transform=None, ignoreBelow=ignoreThreshold)
            influenceValues = cmds.skinPercent(skinCluster, vertex, query=True, value=True, ignoreBelow=ignoreThreshold)
            weightDict[vertex] = list(zip(influenceNames, influenceValues))
        return weightDict
