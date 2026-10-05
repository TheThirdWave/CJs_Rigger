from abc import ABC, abstractmethod
from . import constants

class BaseModule(ABC):

    def __init__(self, name, prefix):
        self._componentType = None
        self._name = name
        self._prefix = prefix
        self._parent = None
        self._children = []
        self._controls = {}
        self._componentVars = {}
        self._inputAttrs = []
        self._outputAttrs = []
        self._bindGeometry = []
        self._baseGroups = {}
        self._bindPositionData = {}
        self._dirty = True

    @property
    def componentType(self):
        return self._componentType

    @componentType.setter
    def componentType(self, ct):
        self._componentType = ct

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
        return self._inputAttrs

    @inputAttrs.setter
    def inputAttrs(self, i):
        self._inputAttrs = i

    @property
    def outputAttrs(self):
        return self._outputAttrs

    @outputAttrs.setter
    def outputAttrs(self, o):
        self._outputAttrs = o

    @property
    def bindGeometry(self):
        return self._bindGeometry

    @bindGeometry.setter
    def bindGeometry(self, gd):
        self._bindGeometry = gd

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, d):
        self._dirty = d

    @classmethod
    def loadFromDict(cls, name, data, default_attrs):
        inst = cls(name, data['prefix'])
        inst.children = data['children']
        inst.controls = data['controls']
        inst.componentVars = data['componentVars']
        inst.inputAttrs = data['inputAttrs']
        inst.bindGeometry = data['bindGeometry']
        inst.componentType = data['componentType']

        # Add default attributes if they haven't been overridden.
        for default in default_attrs['inputAttrs']:
            found = False
            for attr in inst.inputAttrs:
                if attr['attrName'] == default['attrName']:
                    found = True
                    break
            if not found:
                inst.inputAttrs.append(default)
        inst.outputAttrs = data['outputAttrs']
        for default in default_attrs['outputAttrs']:
            found = False
            for attr in inst.outputAttrs:
                if attr['attrName'] == default['attrName']:
                    found = True
                    break
            if not found:
                inst.outputAttrs.append(default)

        # Add default attrs to child data if they're not there.
        for child in inst.children:
            if child['connectionType'] == constants.CONNECTION_TYPES.parent:
                for i in range(len(default_attrs['outputAttrs'])):
                    if default_attrs['inputAttrs'][i]['attrName'] not in child['childAttrs'] and default_attrs['outputAttrs'][i]['attrName'] not in child['parentAttrs']:
                        child['childAttrs'].append(default_attrs['inputAttrs'][i]['attrName'])
                        child['parentAttrs'].append(default_attrs['outputAttrs'][i]['attrName'])

        return inst
    
    def createBindJoints(self):
        pass

    def createControlRig(self):
        pass

    def destroy(self):
        pass

