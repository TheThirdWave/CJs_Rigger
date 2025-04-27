from abc import ABC, abstractmethod

class UtilsController(ABC):

    # Connect the first selected object by the second selected object using a matrix constraint.
    @abstractmethod
    def constrainByMatrix(self):
        pass

    @abstractmethod
    def makeRLMatch(self):
        pass

    @abstractmethod
    def selectBindJoints(self):
        pass

    @abstractmethod
    def mirrorDrivenKeys(self):
        pass

    @abstractmethod
    def generateVertexJoints(self, component_name, joint_side):
        pass

    @abstractmethod
    def appendSoftModDeformer(self):
        pass