import os
import sys
import json
import yaml
import inspect
import copy
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
    def loadedBlueprints(self):
        return {}

    @loadedBlueprints.setter
    @abstractmethod
    def loadedBlueprints(self, m):
        pass

    @property
    @abstractmethod
    def componentGraph(self):
        return None
    
    @componentGraph.setter
    @abstractmethod
    def componentGraph(self, m):
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
    def controlsData(self):
        return {}
    
    @controlsData.setter
    @abstractmethod
    def controlsData(self, c):
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
    def bindSkin(self):
        pass

    def buildComponentGraph(self):
        self.componentGraph = graph_utils.ComponentGraph.buildFromList(self.components)

    def importModules(self, template_path):
        self.components = []
        self.loadedBlueprints = {}
        module_files = os.listdir(self.modulePath)
        blueprint_files = os.listdir(constants.BLUEPRINTS_PATH)
        templates = self.loadYaml(template_path)
        self.unrollBlueprints(templates, blueprint_files)
        self.hookUpBlueprintComponents(templates)
        default_attrs = self.loadYaml(constants.DEFAULT_ATTRS_PATH)
        for file in module_files:
            if os.path.splitext(file)[1] != '.py' or file == '__init__.py':
                continue
            # First, import the file in the module path. I forget how we did it at brazen, so here I basically just
            # have to recreate the whole import chain (as in, I can't do any relative import stuff here.)
            # This is probably way overcomplicated.  Also it breaks importlib so if anyone knows how to avoid that lmk.
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
                            continue


    # If the component type of a component in the templates file matches a blueprint type, then we load the blueprint
    # and add its templates to the template list, giving them unique names by mashing them up with the name of the bluprint
    # component, as well as giving them it's prefix.
    def unrollBlueprints(self, templates, blueprint_files):
        new_components = {}
        for name, data in templates.items():
            # If template is a blueprint, we load that instead.
            for file in blueprint_files:
                blueprint_type = os.path.splitext(file)[0]
                if data['componentType'] == blueprint_type:
                    if blueprint_type not in self.loadedBlueprints:
                        self.loadedBlueprints[blueprint_type] = self.loadYaml(os.path.join(constants.BLUEPRINTS_PATH, file))
                        self.loadedBlueprints[blueprint_type]['blueprintAliases'] = []
                    self.loadedBlueprints[blueprint_type]['blueprintAliases'].append(name)
                    for blueprint_component_name, blueprint_component_data in self.loadedBlueprints[blueprint_type]['components'].items():
                        if not blueprint_component_data['prefix']:
                            blueprint_component_data['prefix'] = data['prefix']
                        for child in blueprint_component_data['children']:
                            child['childName'] = '{0}{1}'.format(name, child['childName'])
                            if not child['childPrefix']:
                                child['childPrefix'] = data['prefix']
                        new_components['{0}{1}'.format(name, blueprint_component_name)] = blueprint_component_data
        templates.update(new_components)



    # We check the children of each component.  If a child name matches a blueprint alias, we replace that child
    # with child elements that correspond to the blueprint's input components.
    def hookUpBlueprintComponents(self, templates):
        for name, data in templates.items():
            for i in range(len(data['children'])):
                for blueprint_type, blueprint_data in self.loadedBlueprints.items():
                    for alias in blueprint_data['blueprintAliases']:
                        if data['children'][i]['childName'] == alias:
                            for input_component_name in blueprint_data['variables']['inputComponents']:
                                new_child = copy.deepcopy(data['children'][i])
                                new_child['childName'] = '{0}{1}'.format(alias, input_component_name)
                                data['children'].append(new_child)
                            data['children'].pop(i)



    def duplicateLRComponents(self):
        for component in self.components:
            if component.prefix == 'LR' or component.prefix == 'RL':
                new_component = None
                if component.prefix == 'LR':
                    component.prefix = 'L'
                    new_component = copy.deepcopy(component)
                    new_component.prefix = 'R'
                    self.components.append(new_component)
                if component.prefix == 'RL':
                    component.prefix = 'R'
                    new_component = copy.deepcopy(component)
                    new_component.prefix = 'L'
                    self.components.append(new_component)
                for child in component.children:
                    if child['childPrefix'] == 'LR' or child['childPrefix'] == 'RL':
                        child['childPrefix'] = component.prefix
                for child in new_component.children:
                    if child['childPrefix'] == 'LR' or child['childPrefix'] == 'RL':
                        child['childPrefix'] = new_component.prefix


            

    def importBindJointPositions(self, positions_path):
        if not self.components:
            constants.RIGGER_LOG.warning('No modules loaded, please load a template first!')
        self.bindPositionData = self.loadJSON(positions_path)

    def importControlData(self, control_data_path):
        if not self.components:
            constants.RIGGER_LOG.warning('No modules loaded, please load a template first!')
        self.controlsData = self.loadJSON(control_data_path)

    @abstractmethod
    def saveBindJointPositions(self, positions_path):
        return

    @abstractmethod
    def saveControlData(self, control_data_path):
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
    
    def isComponent(self, cName, cPrefix, checkNodeData):
        if cName == checkNodeData.name and checkNodeData.prefix in cPrefix:
            return True
        return False