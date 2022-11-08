from abc import ABC, abstractmethod

class BaseController(ABC):

    @property
    @abstractmethod
    def modules(self):
        return []

    @modules.setter
    @abstractmethod
    def modules(self, m):
        pass

    @abstractmethod
    def generateLocs(self):
        pass

    @abstractmethod
    def generateJoints(self):
        pass

    @abstractmethod
    def generateControls(self):
        pass