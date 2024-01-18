from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class UtilityModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the common groups that all components share if they don't exist already.
        if not self.baseGroups:
            self.baseGroups = python_utils.generate_component_base(self.name, self.prefix)

        # We have to initialize the components input/output custom attrs so they can be connected later, even if the component rig hasn't been created yet.
        self.initializeInputandoutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = python_utils.makeCircleControl('{0}_{1}_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.matchTransform(base_placement, base_control)
        cmds.parent(base_control, base_placement)
        cmds.matchTransform(base_placement, self.baseGroups['placement_group'])

        for attr in self.outputAttrs:
            if attr['internalAttr']:
                node = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
                try:
                    node, nodeAttr = node.split('.')
                except:
                    # If it ain't actually an attr we ignore it (yes this is silly)
                    continue
                cmds.addAttr(base_control, longName=nodeAttr, attributeType=attr['attrType'], keyable=True)

        for attr in self.inputAttrs:
            if attr['internalAttr']:
                node = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
                try:
                    node, nodeAttr = node.split('.')
                except:
                    # If it ain't actually an attr we ignore it (yes this is silly)
                    continue
                cmds.addAttr(base_control, longName=nodeAttr, attributeType=attr['attrType'], keyable=True)

        # Connect constrain parent group to parent space matrix.
        python_utils.constrainByMatrix('{0}.parentspace'.format(base_control), self.baseGroups['parent_group'], False)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        # Copy inv world space to placement_GRP to keep the offset around.
        python_utils.copyOverMatrix('{0}.parentinvspace'.format(base_control), self.baseGroups['placement_group'])

        return