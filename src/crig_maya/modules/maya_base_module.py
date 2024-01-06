from ... import base_module
from ... import constants
from ..utilities import python_utils
import maya.cmds as cmds

class MayaBaseModule(base_module.BaseModule):

    def __init__(self):
        self._name = None
        self._prefix = None
        self._parent = None
        self._children = []
        self._controls = {}
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

    def initializeInputandoutputAttrs(self, output_group, input_group):
        cmds.select(output_group)
        for attr in self.outputAttrs:
            cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'])
        cmds.select(input_group)
        for attr in self.inputAttrs:
            cmds.addAttr(longName=attr['attrName'], attributeType=attr['attrType'])

    def connectInputandOutputAttrs(self, output_group, input_group):
        cmds.select(output_group)
        for attr in self.outputAttrs:
            if not attr['internalAttr']:
                continue
            input_attr = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
            new_attr = '{0}.{1}'.format(output_group, attr['attrName'])
            self.connectAttributes(input_attr, new_attr, constants.ATTR_CONNECTION_TYPES.direct)
        cmds.select(input_group)
        for attr in self.inputAttrs:
            if not attr['internalAttr']:
                continue
            new_attr = '{0}.{1}'.format(input_group, attr['attrName'])
            output_attr = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])

            if 'attrConnection' in attr:
                self.connectAttributes(new_attr, output_attr, attr['attrConnection'])
            else:
                self.connectAttributes(new_attr, output_attr, constants.ATTR_CONNECTION_TYPES.direct)

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
        else:
            constants.RIGGER_LOG.warning('{0} connection with {1} has an undefined type!'.format(source_attr, dest_attr))





    def getFullName(self):
        return '{0}_{1}'.format(self.prefix, self.name)