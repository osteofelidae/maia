"""
Base config class
"""

# INTERNAL DEPENDENCIES
from src.utils.path_utils import *

# DEPENDENCIES
import json

# FUNCTIONS
def init_config(config_path: str = None):

    # If config path provided
    if config_path:
        config_path = Path(config_path)

    # If config path not provided
    else:

        # Set system config
        config_path = Path("~/.config/maia/config.json")

    # If config path invalid
    if not config_path.exists():

        # Set default config
        config_path = path("config/config.json")

    # Set config
    global config
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    return config

# GET CONFIG
config = init_config()