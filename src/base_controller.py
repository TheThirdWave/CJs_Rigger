import os
import sys
import json
import yaml
import inspect
import importlib.util
from abc import ABC, abstractmethod

from . import constants
from . import graph_utils

class BaseController(ABC):

    @property
    @abstractmethod
    def modulePath(self):
        return []

    @modulePath.setter
    @abstractmethod
    def modulePath(self, m):
        pass

    @property
    @abstractmethod
    def dccPath(self):
        return []

    @dccPath.setter
    @abstractmethod
    def dccPath(self, dcc):
        pass

    @property
    @abstractmethod
    def components(self):
        return []

    @components.setter
    @abstractmethod
    def components(self, m):
        pass

    @property
    @abstractmethod
    def componentGraph(self):
        return None
    
    @componentGraph.setter
    @abstractmethod
    def components(self, m):
        pass

    @property
    @abstractmethod
    def bindPositionData(self):
        return {}

    @bindPositionData.setter
    @abstractmethod
    def bindPositionData(self, m):
        pass

    @property
    @abstractmethod
    def controlCurveData(self):
        return {}
    
    @controlCurveData.setter
    @abstractmethod
    def controlCurveData(self, c):
        pass

    @property
    @abstractmethod
    def utils(self):
        return None
    
    @utils.setter
    @abstractmethod
    def utils(self, u):
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

    def buildComponentGraph(self):
        self.componentGraph = graph_utils.ComponentGraph.buildFromList(self.components)

    def importModules(self, template_path):
        self.components = []
        module_files = os.listdir(self.modulePath)
        templates = self.loadYaml(template_path)
        default_attrs = self.loadYaml(constants.DEFAULT_ATTRS_PATH)
        for file in module_files:
            if os.path.splitext(file)[1] != '.py' or file == '__init__.py':
                continue
            # First, import the file in the module path. I forget how we did it at brazen, so here I basically just
            # have to recreate the whole import chain (as in, I can't do any relative import stuff here.)
            # This is probably way overcomplicated.
            src_module_name = __name__.rsplit('.', 1)[0]
            dcc_code_root = os.path.splitext(os.path.basename(self.dccPath))[0]
            module_code_root = os.path.splitext(os.path.basename(self.modulePath))[0]
            file_base_name = os.path.splitext(file)[0]
            python_module_name = '{0}.{1}.{2}.{3}'.format(src_module_name, dcc_code_root, module_code_root, file_base_name)
            spec = importlib.util.spec_from_file_location(python_module_name, os.path.join(self.modulePath, file))
            module = importlib.util.module_from_spec(spec)
            sys.modules[python_module_name] = module
            spec.loader.exec_module(module)

            # Then, find the class in that file
            members = inspect.getmembers(module)
            for name, obj in members:
                if inspect.isclass(obj):
                    for name, data in templates.items():
                        if data['componentType'] == obj.__name__:
                            self.components.append(obj.loadFromDict(name, data, default_attrs))

    def importBindJointPositions(self, positions_path):
        if not self.components:
            constants.RIGGER_LOG.warning('No modules loaded, please load a template first!')
        self.bindPositionData = self.loadJSON(positions_path)

    def importCurveData(self, curves_path):
        if not self.components:
            constants.RIGGER_LOG.warning('No modules loaded, please load a template first!')
        self.controlCurveData = self.loadJSON(curves_path)

    @abstractmethod
    def saveBindJointPositions(self, positions_path):
        return

    @abstractmethod
    def saveControlCurveData(self, curves_path):
        return

    def loadJSON(self, path):
        with open(path, 'r') as file:
            positions = json.load(file)
        return positions

    def saveJSON(self, path, data):
        with open(path, 'w') as file:
            json.dump(data, file, indent = 4)

    def loadYaml(self, path):
        templates = None
        with open(path, 'r') as file:
            templates = yaml.safe_load(file)
        return templates