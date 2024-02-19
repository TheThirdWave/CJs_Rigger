import os
import logging
from typing import NamedTuple

RIGGER_LOG = logging.getLogger('CJs_Rigger_LOG')

MAYA_CRIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'crig_maya'))
MAYA_MODULES_PATH = os.path.abspath(os.path.join(MAYA_CRIG_PATH, 'modules'))
TEMPLATES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'templates'))
BLUEPRINTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'blueprints'))
POSITIONS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'positions'))
CONTROLS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'controls'))
SKIN_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'skin'))
DEFAULT_ATTRS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'defaults', 'default_attrs.yaml'))
PREV_RIG_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'previous_rig_paths.json'))

# Is this overcomplicated for a single switch statement in "maya_controller.py"? Yes. But I miss C
# (Also it feels weird for the valid inputs for the "connectionType" field in the component dict to not be stated somewhere)
# (should I use typing more?)
class ConnectionTypes(NamedTuple):
    parent: str
    translateConstraint: str
CONNECTION_TYPES = ConnectionTypes('parent', 'translateconstraint')

class AttrConnectionTypes(NamedTuple):
    direct: str
    copy: str
    copyTransform: str
    proxy: str
    parent: str
ATTR_CONNECTION_TYPES = AttrConnectionTypes('direct', 'copy', 'copytransform', 'proxy', 'parent')

# Basic groups that the controller assumes exists in the maya scene.
class BaseRigGroups(NamedTuple):
    geometry: str
    rig: str
DEFAULT_GROUPS = BaseRigGroups('geometry_GRP', 'rig_GRP')

# MAYA SPECIFIC CONSTANTS
POSITION_SAVE_ATTRS = {
    'translateX',
    'translateY',
    'translateZ',
    'rotateX',
    'rotateY',
    'rotateZ',
    'scaleX',
    'scaleY',
    'scaleZ',
    'radius'
}

# This is duplicating info in the "default_attrs.yaml" file, and adds to overhead if updating it, but I think
# it's worth it for VS Code autocomplete purposes.  I might get rid of it if I start overloading on the default attrs.
class DefaultComponentAttributes(NamedTuple):
    inWorld: str
    inInverseWorld: str
    outWorld: str
    outInverseWorld: str
DEFAULT_ATTRS = DefaultComponentAttributes('IN_WORLD','IN_INV_WORLD','END_OUT_WORLD','END_OUT_INV_WORLD')

# I'm going to save anything to do with the logic or controls of the components in a big .json file.  The root
# dictionary keys are going to be the different types of data I'm saving out.  I'm keeping the expected keys
# here because it feels weird to just have them for all intents and purposes defined in maya_controller.py
class ControlDataKeys(NamedTuple):
    curves: str
    drivenKeys: str
CONTROL_DATA_KEYS = ControlDataKeys('curves', 'drivenKeys')