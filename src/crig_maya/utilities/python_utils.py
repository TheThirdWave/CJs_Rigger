import maya.cmds as cmds

def generate_component_base(component_name, component_prefix):
    component_group = cmds.group(name='{0}_{1}_GRP'.format(component_prefix, component_name), parent='rig_GRP', empty=True)
    output_group = cmds.group(name='output_GRP', parent=component_group, empty=True)
    input_group = cmds.group(name='input_GRP', parent=component_group, empty=True)
    controls_group = cmds.group(name='controls_GRP', parent=component_group, empty=True)
    deform_group = cmds.group(name='deform_GRP', parent=component_group, empty=True)
    return component_group, output_group, input_group, controls_group, deform_group
