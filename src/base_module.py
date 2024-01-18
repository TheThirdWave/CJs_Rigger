from abc import ABC, abstractmethod

class BaseModule(ABC):

    @property
    @abstractmethod
    def name(self):
        return None

    @name.setter
    @abstractmethod
    def name(self, n):
        pass

    @property
    @abstractmethod
    def children(self):
        return []

    @children.setter
    @abstractmethod
    def children(self, c):
        pass

    @property
    @abstractmethod
    def parent(self):
        return None

    @parent.setter
    @abstractmethod
    def parent(self, p):
        pass

    @property
    @abstractmethod
    def controls(self):
        return {}

    @controls.setter
    @abstractmethod
    def controls(self, c):
        pass

    @property
    @abstractmethod
    def prefix(self):
        return None

    @prefix.setter
    @abstractmethod
    def prefix(self, p):
        pass

    @property
    @abstractmethod
    def inputAttrs(self):
        return []

    @inputAttrs.setter
    @abstractmethod
    def inputAttrs(self, i):
        pass

    @property
    @abstractmethod
    def outputAttrs(self):
        return []

    @outputAttrs.setter
    @abstractmethod
    def outputAttrs(self, o):
        pass

    @classmethod
    def loadFromDict(cls, name, data, default_attrs):
        inst = cls(name, data['prefix'])
        inst.children = data['children']
        inst.controls = data['controls']
        inst.inputAttrs = data['inputAttrs']

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
            for default in default_attrs['inputAttrs']:
                if default['attrName'] not in child['childAttrs']:
                    child['childAttrs'].append(default['attrName'])
            for default in default_attrs['outputAttrs']:
                if default['attrName'] not in child['parentAttrs']:
                    child['parentAttrs'].append(default['attrName'])

        return inst
    
    @abstractmethod
    def createBindJoints(self):
        pass

    @abstractmethod
    def createControlRig(self):
        pass

