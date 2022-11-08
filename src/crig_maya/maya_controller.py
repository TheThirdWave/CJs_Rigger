from .. import base_controller

class MayaController(base_controller.BaseController):

    def __init__(self):
        self._modules = []

    @property
    def modules(self):
        return self._modules

    @modules.setter
    def modules(self, m):
        self._modules = m

    def generateLocs(self):
        return

    def generateJoints(self):
        for module in self.modules:
            module.createControlRig()

    def generateControls(self):
        return