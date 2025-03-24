from . import maya_base_module
from ..utilities import python_utils
from ... import constants
import maya.cmds as cmds

class JointCloud(maya_base_module.MayaBaseModule):

    def createBindJoints(self):
        # Create the bind joints that the stuff in the "controls_GRP" will drive.  These should not have any actual puppetry logic in them, they should be driven by puppet joints.
        cmds.select(self.baseGroups['deform_group'])
        self.joint_dict = {}
        self.joint_dict['baseJoint'] = cmds.joint(self.baseGroups['deform_group'], name='{0}_{1}_base_BND_JNT'.format(self.prefix, self.name), position=(0, 0, 0))

        if 'numChains' in self.componentVars:
            num_chains = self.componentVars['numChains']
        else:
            num_chains = 1

        if 'chainLength' in self.componentVars:
            self.chain_length = self.componentVars['chainLength']
        else:
            self.chain_length = 1

        if 'numKeyLayers' in self.componentVars:
            self.key_layers = self.componentVars['numKeyLayers']
        else:
            self.key_layers = 0

        if 'numChainKeyLayers' in self.componentVars:
            self.chain_key_layers = self.componentVars['numChainKeyLayers']
        else:
            self.chain_key_layers = 0
        
        self.joint_dict['cloudJoints'] = []
        for i in range(num_chains):
            joint_chain = []
            last_joint = self.joint_dict['baseJoint']
            for j in range(self.chain_length):
                current_joint = cmds.joint(last_joint, name='{0}_{1}_{2}_{3}_BND_JNT'.format(self.prefix, self.name, i, j), position=(0, 0, 0))
                joint_chain.append(current_joint)
                last_joint = current_joint
            self.joint_dict['cloudJoints'].append(joint_chain)

    def createControlRig(self):
        if not self.baseGroups:
            constants.RIGGER_LOG.warning('Base groups for component {0} not found, run "Generate Bind Joints" first.')
            return

        base_dupe_joint = cmds.duplicate(self.joint_dict['baseJoint'], name=self.joint_dict['baseJoint'].replace('BND', 'CTL'), parentOnly=True)[0]
        cmds.parent(base_dupe_joint, self.baseGroups['placement_group'])
        python_utils.constrainTransformByMatrix(base_dupe_joint, self.joint_dict['baseJoint'])

        for joint_chain in self.joint_dict['cloudJoints']:
            par_joint = base_dupe_joint
            dupe_chain = []
            for j in range(len(joint_chain)):
                base_and_keys = []
                new_joint = cmds.joint(par_joint, name=joint_chain[j].replace('BND', 'CTL'), relative=True, scaleCompensate=False)
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(new_joint)
                base_and_keys.append(new_joint)
                par_joint = new_joint
                for i in range(self.chain_key_layers):
                    new_joint = cmds.joint(par_joint, name=joint_chain[j].replace('BND', '{0}_KEY'.format(i)), relative=True, scaleCompensate=False)
                    base_and_keys.append(new_joint)
                    par_joint = new_joint
                if j < (len(joint_chain) - 1):
                    control_stuff = python_utils.makeControl('{0}_{1}_{2}_chain_CTL_CRV'.format(prefix, component_name, joint_name), 2, "circle")
                    control_pos_group = control_stuff[0]
                    cmds.parent(control_stuff[0], par_joint)
                    python_utils.zeroOutLocal(control_pos_group)
                    par_joint = control_stuff[1]
                    base_and_keys.append(control_stuff[1])
                dupe_chain.append(base_and_keys)
            for j in range(len(joint_chain)):
                cmds.matchTransform(dupe_chain[j][0], joint_chain[j])
                current_joint = dupe_chain[j][-1]
                prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(current_joint)
                if node_type == 'CRV':
                    prefix, component_name, joint_name, node_purpose, node_type = python_utils.getNodeNameParts(dupe_chain[j][-2])
                par_joint = current_joint
                key_joints = [current_joint]
                cur_key_joint = current_joint
                for i in range(self.key_layers):
                    new_joint = cmds.joint(cur_key_joint, name='{0}_{1}_{2}_{3}_KEY_JNT'.format(prefix, component_name, joint_name, i), relative=True, scaleCompensate=False)
                    key_joints.append(new_joint)
                    cur_key_joint = new_joint
                cmds.setAttr('{0}.segmentScaleCompensate'.format(joint_chain[j]), False)
                control_stuff = python_utils.makeConstraintControl('{0}_{1}_{2}_CTL_CRV'.format(prefix, component_name, joint_name), key_joints[-1], joint_chain[j], 1.0, "circle", maintainOffset=False, useParentOffset=False)
                control_pos_group = control_stuff[0]
                python_utils.zeroOutLocal(control_pos_group)

        self.connectInputandOutputAttrs(self.baseGroups['output_group'], self.baseGroups['input_group'])

        return