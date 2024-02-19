from ... import base_module
from ... import constants
from ..utilities import python_utils
import maya.cmds as cmds

class MayaBaseModule(base_module.BaseModule):

    def __init__(self, name, prefix):
        self._name = name
        self._prefix = prefix
        self._parent = None
        self._children = []
        self._controls = {}
        self._componentVars = {}
        self._inputAttrs = []
        self._outputAttrs = []
        self._baseGroups = {}
        self._bindPositionData = {}

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, p):
        self._prefix = p

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, p):
        self._parent = p

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, c):
        self._children = c

    @property
    def controls(self):
        return self._controls

    @controls.setter
    def controls(self, c):
        self._controls = c

    @property
    def componentVars(self):
        return self._componentVars

    @componentVars.setter
    def componentVars(self, cv):
        self._componentVars = cv

    @property
    def inputAttrs(self):
        return self._inputNode

    @inputAttrs.setter
    def inputAttrs(self, i):
        self._inputNode = i

    @property
    def outputAttrs(self):
        return self._outputNode

    @outputAttrs.setter
    def outputAttrs(self, o):
        self._outputNode = o

    @property
    def baseGroups(self):
        return self._baseGroups

    @baseGroups.setter
    def baseGroups(self, bg):
        self._baseGroups = bg

    def generateComponentBase(self):
        if not self.baseGroups:
            groups = {}
            groups['component_group'] = cmds.group(name='{0}_{1}_GRP'.format(self.prefix, self.name), parent=constants.DEFAULT_GROUPS.rig, empty=True)
            groups['output_group'] = cmds.group(name='{0}_{1}_output_GRP'.format(self.prefix, self.name), parent=groups['component_group'], empty=True)
            groups['input_group'] = cmds.group(name='{0}_{1}_input_GRP'.format(self.prefix, self.name), parent=groups['component_group'], empty=True)
            groups['controls_group'] = cmds.group(name='{0}_{1}_controls_GRP'.format(self.prefix, self.name), parent=groups['component_group'], empty=True)
            groups['deform_group'] = cmds.group(name='{0}_{1}_deform_GRP'.format(self.prefix, self.name), parent=groups['component_group'], empty=True)
            # Create parent space group
            groups['parent_group'] = cmds.group(name='{0}_{1}_parentSpace_PAR_GRP'.format(self.prefix, self.name), parent=groups['controls_group'], empty=True)
            # Turn off transform inheritance because it's getting its parent transform from the input group.
            cmds.inheritTransform(groups['parent_group'], off=True)
            # Create placement group to hold the initial offset.
            groups['placement_group'] = cmds.group(name='{0}_{1}_placement_PLC_GRP'.format(self.prefix, self.name), parent=groups['parent_group'], empty=True)
            self.baseGroups = groups


    def initializeInputandoutputAttrs(self):
        output_group = self.baseGroups['output_group']
        input_group = self.baseGroups['input_group']
        cmds.select(output_group)
        for attr in self.outputAttrs:
            if 'proxy' in attr and attr['proxy']:
                cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'], usedAsProxy=True)
            else:
                cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'])
        cmds.select(input_group)
        for attr in self.inputAttrs:
            if 'proxy' in attr and attr['proxy']:
                cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'], usedAsProxy=True)
            else:
                cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'])

    def connectInputandOutputAttrs(self, output_group, input_group):
        cmds.select(output_group)
        for attr in self.outputAttrs:
            self.figureOutAttrConnections(attr, output_group, False)
        cmds.select(input_group)
        for attr in self.inputAttrs:
            self.figureOutAttrConnections(attr, input_group, True)

    def figureOutAttrConnections(self, attr, parent_group, input):
        if not attr['internalAttr']:
            return
        new_attr = '{0}.{1}'.format(parent_group, attr['attrName'])
        final_attr_path = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])

        if 'attrConnection' in attr:
            if len(final_attr_path.split('.')) > 1:
                # If the output attribute doesn't exist, we'll add it, along with any internal proxy attributes.
                self.setInternalAttrStuff(final_attr_path, attr)
            if input:
                self.connectAttributes(new_attr, final_attr_path, attr['attrConnection'])
            else:
                self.connectAttributes(final_attr_path, new_attr, attr['attrConnection'])
        else:
            # If the output attribute doesn't exist, we'll add it, along with any internal proxy attributes.
            self.setInternalAttrStuff(final_attr_path, attr)
            if input:
                self.connectAttributes(new_attr, final_attr_path, constants.ATTR_CONNECTION_TYPES.direct)
            else:
                self.connectAttributes(final_attr_path, new_attr, constants.ATTR_CONNECTION_TYPES.direct)

    def connectAttributes(self, source_attr, dest_attr, connection_type):
        
        lower_connection_type = connection_type.lower()

        if lower_connection_type == constants.ATTR_CONNECTION_TYPES.direct:
            cmds.connectAttr(source_attr, dest_attr)
        elif lower_connection_type == constants.ATTR_CONNECTION_TYPES.copy:
            source_node_name, source_attr_name = source_attr.split('.')
            dest_node_name, dest_attr_name = dest_attr.split('.')
            cmds.copyAttr(source_node_name, dest_node_name, values='True', attribute=[source_attr_name, dest_attr_name])
        elif lower_connection_type == constants.ATTR_CONNECTION_TYPES.copyTransform:
            python_utils.copyOverMatrix(source_attr, dest_attr)
        elif lower_connection_type == constants.ATTR_CONNECTION_TYPES.proxy:
            dest_node_name, dest_attr_name = dest_attr.split('.')
            dest_proxy = python_utils.getIsProxyAttr(dest_node_name, dest_attr_name)
            if not dest_proxy:
                python_utils.setIsProxyAttr(dest_node_name, dest_attr_name, True)
            cmds.connectAttr(source_attr, dest_attr)
        else:
            constants.RIGGER_LOG.warning('{0} connection with {1} has an undefined type!'.format(source_attr, dest_attr))


    def setInternalAttrStuff(self, internalAttr, attr_data):
        # If the attribute doesn't exist we add it
        if not cmds.attributeQuery(internalAttr.split('.')[1], node=internalAttr.split('.')[0], exists=True):
            node, attr = internalAttr.split('.')
            cmds.addAttr(node, longName=attr, attributeType=attr_data['attrType'])
        
        # Add attribute limits if specified.
        if 'min' in attr_data:
            cmds.addAttr(internalAttr, edit=True, minValue=attr_data['min'])
        if 'max' in attr_data:
            cmds.addAttr(internalAttr, edit=True, maxValue=attr_data['max'])
        
        # If there's a list of internal proxies, we go and create those
        if 'internalProxyNodes' in attr_data:
            self.createInternalProxyAttrs(internalAttr, attr_data['internalProxyNodes'])

    def createInternalProxyAttrs(self, internalAttr, proxy_list):
        parent_node, attribute = internalAttr.split('.')
        for proxy_node in proxy_list:
            proxy_node_full = '{0}_{1}_{2}'.format(self.prefix, self.name, proxy_node)
            cmds.addAttr(proxy_node_full, longName=attribute, proxy=internalAttr)


    def getFullName(self):
        return '{0}_{1}'.format(self.prefix, self.name)