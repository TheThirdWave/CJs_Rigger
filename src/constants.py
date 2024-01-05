import os
import logging

RIGGER_LOG = logging.getLogger('CJs_Rigger_LOG')

MAYA_CRIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'crig_maya'))
MAYA_MODULES_PATH = os.path.abspath(os.path.join(MAYA_CRIG_PATH, 'modules'))
TEMPLATES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'templates'))
POSITIONS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'positions'))
CURVES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'curves'))
DEFAULT_ATTRS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'defaults', 'default_attrs.yaml'))
PREV_RIG_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'previous_rig_paths.json'))

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