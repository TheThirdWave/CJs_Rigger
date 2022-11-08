from ... import base_module
from ..utilities import python_utils
import maya.cmds as cmds

import logging

LOG = logging.getLogger(__name__)

class MayaBaseModule(base_module.BaseModule):

    def __init__(self):
        self._name = None
        self._prefix = None
        self._parent = None
        self._children = []
        self._controls = {}
        self._inputAttrs = []
        self._outputAttrs = []

    @classmethod
    def loadFromDict(cls, data):
        inst = cls()
        inst.name = data['name']
        inst.prefix = data['prefix']
        inst.children = data['children']
        inst.controls = data['controls']
        inst.inputAttrs = data['inputAttrs']
        inst.outputAttrs = data['outputAttrs']
        return inst

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

    def populateInputandOutputAttrs(self, output_group, input_group):
        cmds.select(output_group)
        for attr in self.outputAttrs:
            cmds.addAttr(longName=attr['longName'], attributeType=attr['type'])
        cmds.select(input_group)
        for attr in self.inputAttrs:
            cmds.addAttr(longName=attr['longName'], attributeType=attr['type'])