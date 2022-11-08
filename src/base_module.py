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
    
    @abstractmethod
    def createControlRig(self):
        pass

