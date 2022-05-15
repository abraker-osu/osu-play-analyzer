import os

os.makedirs('data', exist_ok=True)

from .config_mgr import AppConfig
from .db_mgr import MapsDB
from .npy_mgr import score_data_obj
