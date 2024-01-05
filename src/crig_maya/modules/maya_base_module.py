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
            cmds.connectAttr(input_attr, new_attr)
        cmds.select(input_group)
        for attr in self.inputAttrs:
            if not attr['internalAttr']:
                continue
            new_attr = '{0}.{1}'.format(input_group, attr['attrName'])
            output_attr = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
            cmds.connectAttr(new_attr, output_attr)

    def getFullName(self):
        return '{0}_{1}'.format(self.prefix, self.name)