from ... import base_module
from ... import constants
from ..utilities import python_utils
import maya.cmds as cmds
import pyfrost as pf

class BifrostBaseModule(base_module.BaseModule):

    @property
    def bifTemplate(self):
        return self._bifTemplate

    @bifTemplate.setter
    def bifTemplate(self, bt):
        self._bifTemplate = bt

    @property
    def bifBoard(self):
        return self._bifBoard

    @bifBoard.setter
    def bifBoard(self, bb):
        self._bifBoard = bb

    @property
    def bifNode(self):
        return self._bifNode

    @bifNode.setter
    def bifNode(self, bg):
        self._bifNode = bg

    @classmethod
    def loadFromDict(cls, name, data, default_attrs, bifTemplate_name):
        instance_ret = super().loadFromDict(name, data, default_attrs)
        instance_ret.bifTemplate = bifTemplate_name
        instance_ret.bifBoard = None
        instance_ret.bifNode = None
        return instance_ret

    def createBindJoints(self):
        self.bifNode = self.bifBoard.create_node(self.bifTemplate, name='{0}_{1}'.format(self.prefix, self.name))
        self.bifNode.rename(self.getFullName())
        self.bifNode['name'].value = self.getFullName()
        self.bifNode.is_editable = True

    def initializeInputandoutputAttrs(self):
        for attr in self.inputAttrs:
            self.bifNode[attr['attrName']].add('input', attr['attrType'])
            self.handleInputConnections(attr)
        for attr in self.outputAttrs:
            self.bifNode[attr['attrName']].add('output', attr['attrType'])
            self.handleOutputConnections(attr)


    def handleInputConnections(self, attr):
        if not attr['internalAttr']:
            return

        if 'attrConnection' in attr:
            match attr['attrConnection']:
                case 'parent':
                    user_setup = self.bifNode['/user_setup']
                    self.bifNode[attr['attrName']] >> user_setup[attr['attrName']]
                    handle_parents = user_setup['/handle_parents']
                    handle_parents.exists()
                    if not handle_parents.exists():
                        handle_parents = user_setup.create_node('compound', 'handle_parents')
                    user_setup['/value25.output.parents'] >> handle_parents['parents']
                    user_setup[attr['attrName']] >> handle_parents[attr['attrName']]
                    find_parent = handle_parents.create_node('Rigging::Module::Setup::find_parent')
                    handle_parents['parents'] >> find_parent['parents']
                    handle_parents[attr['attrName']] >> find_parent['find']
                    parent_path, node_name, node_purpose, node_type = python_utils.getNodeNameParts(attr['internalAttr'])
                    if node_type == 'CRV':
                        find_parent['kind'].value = 0
                        node_attr_name = 'parent_control'
                    elif node_type == 'JNT':
                        find_parent['kind'].value = 1
                        node_attr_name = 'parent_joint'
                    handle_parents['{}_OUT'.format(attr['attrName'])].add("output", datatype=find_parent['parent_definition'].type)
                    find_parent['parent_definition'] >> handle_parents['{}_OUT'.format(attr['attrName'])]
                    handle_parents['{}_OUT'.format(attr['attrName'])] >> self.bifNode['{}.{}'.format(attr['internalAttr'], node_attr_name)]
                case _:
                    python_utils.attrConnectDown(self.bifNode[attr['attrName']], self.bifNode[attr['internalAttr']])
        else:
            python_utils.attrConnectDown(self.bifNode[attr['attrName']], self.bifNode[attr['internalAttr']])


    def handleOutputConnections(self, attr):
        if not attr['internalAttr']:
            return

        if 'attrConnection' in attr:
            match attr['attrConnection']:
                case _:
                    python_utils.attrConnectUp(self.bifNode[attr['internalAttr']], self.bifNode[attr['attrName']])
        else:
            python_utils.attrConnectUp(self.bifNode[attr['internalAttr']], self.bifNode[attr['attrName']])


    def getFullName(self):
        return '{0}_{1}'.format(self.prefix, self.name)