from . import maya_base_module
from ..utilities import python_utils
import maya.cmds as cmds

class RootModule(maya_base_module.MayaBaseModule):

    def __init__(self):
        super().__init__()

    def createControlRig(self):
        # Create the common groups that all components share.
        component_group, output_group, input_group, controls_group, deform_group = python_utils.generate_component_base(self.name, self.prefix)

        # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
        base_control = cmds.curve(name='{0}_{1}_base_CTL_CRV'.format(self.prefix, self.name), degree=1, point=[(2,0,2), (-2,0,2),(-2,0,2),(-2,0,-2),(-2,0,-2),(2,0,-2),(2,0,-2),(2,0,2)])
        base_placement = cmds.group(base_control, name='{0}_{1}_base_PLC_GRP'.format(self.prefix, self.name), parent=controls_group)
        middle_control = cmds.curve(name='{0}_{1}_middle_CTL_CRV'.format(self.prefix, self.name), degree=1, point=[(1.5,0,1.5), (-1.5,0,1.5),(-1.5,0,1.5),(-1.5,0,-1.5),(-1.5,0,-1.5),(1.5,0,-1.5),(1.5,0,-1.5),(1.5,0,1.5)])
        middle_placement = cmds.group(middle_control, name='{0}_{1}_middle_PLC_GRP'.format(self.prefix, self.name), parent=base_control)
        end_control = cmds.curve(name='{0}_{1}_end_CTL_CRV'.format(self.prefix, self.name), degree=1, point=[(1,0,1), (-1,0,1),(-1,0,1),(-1,0,-1),(-1,0,-1),(1,0,-1),(1,0,-1),(1,0,1)])
        end_placement = cmds.group(end_control, name='{0}_{1}_end_PLC_GRP'.format(self.prefix, self.name), parent=middle_control)

        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(deform_group)
        cmds.joint(deform_group, name='{0}_{1}_end_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        self.populateInputandOutputAttrs(output_group, input_group)
        return