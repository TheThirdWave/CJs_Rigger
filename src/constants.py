import os
import logging

RIGGER_LOG = logging.getLogger('CJs_Rigger_LOG')

MAYA_CRIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'crig_maya'))
MAYA_MODULES_PATH = os.path.abspath(os.path.join(MAYA_CRIG_PATH, 'modules'))
TEMPLATES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'templates'))
POSITIONS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'positions'))

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