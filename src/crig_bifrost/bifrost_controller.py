import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om2
import pyfrost.main as pf
import os
import inspect
import sys
import importlib

from .. import base_controller, constants, graph_utils

class BifrostController(base_controller.BaseController):

    def __init__(self, uistate):
        super().__init__(uistate)
        self._modulePath = constants.BIFROST_MODULES_PATH
        self._dccPath = constants.BIFROST_CRIG_PATH
        self._displayComponents = []
        self._components = []
        self._loadedBlueprints = {}
        self._displayGraph = None
        self._componentGraph = None
        self._bindPositionData = {}
        self._controlsData = {}
        self.postScripts = {
            constants.POSTSCRIPT_TYPES.controlGeneration: [],
            constants.POSTSCRIPT_TYPES.skinBind: [],
            constants.POSTSCRIPT_TYPES.deletion: []
        }
        return

    @property
    def modulePath(self):
        return self._modulePath

    @modulePath.setter
    def modulePath(self, m):
        self._modulePath = m

    @property
    def dccPath(self):
        return self._dccPath

    @dccPath.setter
    def dccPath(self, dcc):
        self._dccPath = dcc

    @property
    def displayComponents(self):
        return self._displayComponents

    @displayComponents.setter
    def displayComponents(self, dc):
        self._displayComponents = dc

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self, c):
        self._components = c

    @property
    def loadedBlueprints(self):
        return self._loadedBlueprints

    @loadedBlueprints.setter
    def loadedBlueprints(self, lb):
        self._loadedBlueprints = lb

    @property
    def displayGraph(self):
        return self._displayGraph
    
    @displayGraph.setter
    def displayGraph(self, cg):
        self._displayGraph = cg

    @property
    def componentGraph(self):
        return self._componentGraph
    
    @componentGraph.setter
    def componentGraph(self, cg):
        self._componentGraph = cg

    @property
    def bindPositionData(self):
        return self._bindPositionData

    @bindPositionData.setter
    def bindPositionData(self, m):
        self._bindPositionData = m

    @property
    def controlsData(self):
        return self._controlsData
    
    @controlsData.setter
    def controlsData(self, c):
        self._controlsData = c

    @property
    def postScripts(self):
        return self._postScripts
    
    @postScripts.setter
    def postScripts(self, ps):
        self._postScripts = ps

    @property
    def utils(self):
        return self._utils
    
    @utils.setter
    def utils(self, u):
        self._utils = u

    @property
    def bifrostGraph(self):
        return self._bifrostGraph
    
    @bifrostGraph.setter
    def bifrostGraph(self, bfg):
        self._bifrostGraph = bfg

    def delete(self):
        check = cmds.ls(self.bifrostGraph.name)
        if check:
            transform = cmds.listRelatives(check, parent=True)
            cmds.delete(transform)
        self.bifrostGraph = None
        super().delete()

    def mirrorComponentGraph(self):
        self.bifrostGraph = pf.Graph('crig_graph_BIBD')
        parent = cmds.listRelatives(self.bifrostGraph.board, parent=True)
        if parent and parent[0] != constants.DEFAULT_GROUPS.rig:
            cmds.parent(self.bifrostGraph.board, constants.DEFAULT_GROUPS.rig)
        for component in self.components:
            component_name = '{0}_{1}'.format(component.prefix, component.name)
            component.bifBoard = self.bifrostGraph
            for node in self.bifrostGraph.nodes:
                if node.name == component_name:
                    component.bifNode = node
                    component.dirty = False
        return

    def generateLocs(self):
        #TODO: setup bifrost templates and pin locations.
        iter = graph_utils.ComponentGraphIterator()
        iter.breadthFirstIteration(self.componentGraph, self.callCreateBindJoints)
        return

    def generateJoints(self):
        iter = graph_utils.ComponentGraphIterator()
        iter.breadthFirstIteration(self.componentGraph, self.callConnectModules)
        
        self.connectInputs()
        self.connectOutputs()
        return

    def bindSkin(self):
        return

    def callCreateBindJoints(self, component):
        if component.dirty:
            if component.bifNode and self.bifrostGraph.get(component.bifNode.name):
                self.bifrostGraph.remove_node(component.bifNode.name)
            component.createBindJoints()
            component.initializeInputandoutputAttrs()        

    def callConnectModules(self, component):
        self.connectParents(component)


    def connectInputs(self):
        for component in self.components:
            input_node = self.bifrostGraph["/input"]
            input_node[component.getFullName() + "_IN"] >> component.bifNode["inputs"]

    def connectOutputs(self):
        for component in self.components:
            output_node = self.bifrostGraph["/output"]
            component.bifNode["outputs"] >> output_node[component.getFullName() + "_OUT"]

    def connectParents(self, component):
        for child in component.children:
            for ccomponent in self.components:
                if self.isComponent(child['childName'], child['childPrefix'], ccomponent):
                    component.bifNode['outputs'] >> ccomponent.bifNode['parents']
                    for i in range(len(child['parentAttrs'])):
                        component.bifNode[child['parentAttrs'][i]] >> ccomponent.bifNode[child['childAttrs'][i]]
                    if 'parentUpAttrs' in child:
                        for i in range(len(child['parentUpAttrs'])):
                            ccomponent.bifNode[child['childUpAttrs'][i]] >> component.bifNode[child['parentUpAttrs'][i]]

    def saveBindJointPositions(self, positions_path):
        return

    def saveControlData(self, control_data_path):
        return
    
    def saveBindSkinData(self, bind_path):
        return

    # I've decided to use the actual bifrost .json modules to handle the individual logic in order to
    # make it (hopefully!) as easy for users to publish modules to the autorigger as it is to publish
    # the bifrost modules normally.
    def importModules(self, template_path):
        self.components = []
        self.loadedBlueprints = {}
        module_files = os.listdir(self.modulePath)
        blueprint_files = os.listdir(constants.BLUEPRINTS_PATH)
        templates = self.loadYaml(template_path)
        self.unrollBlueprints(templates, blueprint_files)
        self.hookUpBlueprintComponents(templates)
        default_attrs = self.loadYaml(constants.BIFROST_DEFAULT_ATTRS_PATH)
        # The only python module we should need is the default module for the
        # bifrost autorigger.
        default_module = self.grabDefaultModule()
        for file in module_files:
            if os.path.splitext(file)[1] != '.json':
                continue
            bifrost_module_json = self.loadJSON(os.path.join(self.modulePath, file))

            for name, data in templates.items():
                if data['componentType'] == bifrost_module_json['compounds'][0]['name']:
                    self.components.append(default_module.loadFromDict(name, data, default_attrs, bifrost_module_json['compounds'][0]['name']))
                continue


    def grabDefaultModule(self):
        # First, import the file in the module path. I forget how we did it at brazen, so here I basically just
        # have to recreate the whole import chain (as in, I can't do any relative import stuff here.)
        # This is probably way overcomplicated.  Also it breaks importlib so if anyone knows how to avoid that lmk.
        src_module_name = __name__.rsplit('.', 2)[0]
        dcc_code_root = os.path.splitext(os.path.basename(self.dccPath))[0]
        module_code_root = os.path.splitext(os.path.basename(self.modulePath))[0]
        file_base_name = os.path.splitext(constants.BIFROST_DEFAULT_MODULE)[0]
        python_module_name = '{0}.{1}.{2}.{3}'.format(src_module_name, dcc_code_root, module_code_root, file_base_name)
        spec = importlib.util.spec_from_file_location(python_module_name, os.path.join(self.modulePath, constants.BIFROST_DEFAULT_MODULE))
        module = importlib.util.module_from_spec(spec)
        sys.modules[python_module_name] = module
        spec.loader.exec_module(module)

        # Then, find the class in that file
        members = inspect.getmembers(module)
        for name, obj in members:
            if inspect.isclass(obj):
                return obj
        return None