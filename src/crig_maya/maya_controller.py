import maya.cmds as cmds

from .utilities import python_utils
from .. import base_controller, constants, graph_utils

class MayaController(base_controller.BaseController):

    def __init__(self):
        self._modulePath = constants.MAYA_MODULES_PATH
        self._dccPath = constants.MAYA_CRIG_PATH
        self._components = []
        self._componentGraph = None
        self._bindPositionData = {}
        self._controlCurveData = {}
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
    def controlCurveData(self):
        return self._controlCurveData
    
    @controlCurveData.setter
    def controlCurveData(self, c):
        self._controlCurveData = c

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
        component.createBindJoints()

    def generateJoints(self):
        #We generate and connect the control rigs from the root down to ensure that
        #Parents are always created before we connect them to their children.  Otherwise,
        #the data won't be there when the child components are created which will mess up
        #any intended offsets in the child components.
        #
        #The parent/child relationships are defined in the template.
        iter = graph_utils.ComponentGraphIterator()
        iter.breadthFirstIteration(self.componentGraph, self.callControlRigAndConnect)

        #Load in the saved out curve data for the controls (or I guess any curve under the controls )
        for component, component_data in self.controlCurveData.items():
            for name in component_data:
                cmds.curve(name, r=True, p=component_data[name])

    def callControlRigAndConnect(self, component):
        component.createControlRig()
        self.connectModuleToChildren(component)

    def generateControls(self):
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

    def saveControlCurveData(self, curves_path):
        curves_dict = {}
        for component in self.components:
            controls_group = component.baseGroups['controls_group']
            children = cmds.listRelatives(controls_group, allDescendents=True, type='transform')
            for child in children:
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(child)
                if node_type == 'CRV' and node_purpose == 'CTL':
                    if '{0}_{1}'.format(component.prefix, component.name) not in curves_dict:
                        curves_dict['{0}_{1}'.format(component.prefix, component.name)] = {}
                    curves_dict['{0}_{1}'.format(component.prefix, component.name)][child] = cmds.getAttr('{0}.{1}'.format(child, 'cv[*]'))
        self.controlCurveData = curves_dict
        self.saveJSON(curves_path, curves_dict)

    def connectModuleToChildren(self, module):
        for child in module.children:
                # First we connect up all the attributes.
                self.connectModuleAttrs(child, module)
                # Then we immediately change the IN_WORLD/END_OUT_WORLD connections because I've decided they're special and how I'm going
                # to deal with component parent/child transformation stuff.
                self.connectParentLogic(child, module)


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
            if child['childName'] == ccomponent.name:
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