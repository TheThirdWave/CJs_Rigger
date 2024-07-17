from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class JointCloudModule(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.joint_dict = {}
        self.joint_dict['baseJoint'] = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        if 'numJoints' in self.componentVars:
            num_joints = self.componentVars['numJoints']
        else:
            num_joints = 3

        if 'numKeyLayers' in self.componentVars:
            self.key_layers = self.componentVars['numKeyLayers']
        else:
            self.key_layers = 0
        
        self.joint_dict['cloudJoints'] = []
        for i in range(num_joints):
            joint_chain = []
            end_joint = cmds.joint(self.joint_dict['baseJoint'], name='{0}_{1}_{2}_BND_JNT'.format(self.prefix, self.name, i), position=(0, 0, 0))
            for j in range(self.key_layers):
                key_joint = cmds.duplicate(end_joint, name=end_joint.replace('BND_JNT', '{0}_PLC_JNT'.format(j)))
                cmds.parent(end_joint, key_joint)
                joint_chain.append(key_joint)
            joint_chain.append(end_joint)
            self.joint_dict['cloudJoints'].append(joint_chain)

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        joint_list = []
        for joint_chain in self.joint_dict['cloudJoints']:
            # reparent the end joint to be below the base joint
            cmds.parent(joint_chain[-1], self.joint_dict['baseJoint'])
            end_joint = joint_chain[-1]
            # Create the stuff that goes under the "controls_GRP", which is pretty much all of the logic and user interface curves.
            base_control = python_utils.makeSquareControl(end_joint.replace('BND_JNT', 'CTL_CRV'), 2)
            base_placement = cmds.group(name=end_joint.replace('BND_JNT', 'PLC_GRP'), parent=self.baseGroups['placement_group'], empty=True)
            cmds.matchTransform(base_placement, base_control)
            cmds.parent(base_control, base_placement)
            cmds.matchTransform(base_placement, end_joint)
            joint_chain.remove(end_joint)
            if joint_chain:
                cmds.parent(joint_chain[0], base_placement)
                parent = base_placement
                for key_joint in joint_chain:
                    cmds.parent(key_joint, parent)
                    cmds.rename(key_joint.replace('PLC_JNT', 'KEY_JNT'))
                    key_joint = key_joint.replace('PLC_JNT', 'KEY_JNT')
                cmds.parent(base_control, joint_chain[-1])
            joint_list.append( { 'control': base_control, 'placement': base_placement, 'keyJoints': joint_chain, 'bindJoint': end_joint } )
            # Connect control to bind joint.
            mult_matrix, matrix_decompose = python_utils.constrainTransformByMatrix(base_control, end_joint)


        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return