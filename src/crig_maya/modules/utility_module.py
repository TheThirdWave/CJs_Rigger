from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class UtilityModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create a placeholder joint that we use for positioning
        cmds.select(self.baseGroups['deform_group'])
        self.place_joint = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_control_PLC_JNT'.format(self.prefix, self.name), position=(0, 0, 0))
        return

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = python_utils.makeCircleControl('{0}_{1}_base_CTL_CRV'.format(self.prefix, self.name), 2)
        base_placement = cmds.group(name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=self.baseGroups['placement_group'], empty=True)
        cmds.matchTransform(base_placement, base_control)
        cmds.parent(base_control, base_placement)

        # Match the control to the place joint then delete the joint.
        cmds.matchTransform(base_placement, self.place_joint)
        cmds.delete(self.place_joint)

        for attr in self.outputAttrs:
            if attr['internalAttr']:
                node = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
                try:
                    node, nodeAttr = node.split('.')
                except:
                    # If it ain't actually an attr we ignore it (yes this is silly)
                    continue
                if nodeAttr not in cmds.listAttr(base_control):
                    cmds.addAttr(base_control, longName=nodeAttr, attributeType=attr['attrType'], keyable=True)

        for attr in self.inputAttrs:
            if attr['internalAttr']:
                node = '{0}_{1}_{2}'.format(self.prefix, self.name, attr['internalAttr'])
                try:
                    node, nodeAttr = node.split('.')
                except:
                    # If it ain't actually an attr we ignore it (yes this is silly)
                    continue
                if nodeAttr not in cmds.listAttr(base_control):
                    cmds.addAttr(base_control, longName=nodeAttr, attributeType=attr['attrType'], keyable=True)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return