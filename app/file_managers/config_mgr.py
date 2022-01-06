import json
import random


class _AppConfig():

    cfg = {}

    @staticmethod
    def load_config_file():
        try:
            with open('config.json') as f:
                _AppConfig.cfg = json.load(f)
        except FileNotFoundError:
            _AppConfig.cfg = { 
                'id'      : random.randint(100, 1000000),
                'osu_dir' : '' 
            }

            with open('config.json', 'w') as f:
                json.dump(_AppConfig.cfg, f, indent=4)

            with open('config.json') as f:
                _AppConfig.cfg = json.load(f)


    @staticmethod
    def update_value(key, value):
        _AppConfig.cfg[key] = value

        with open('config.json', 'w') as f:
            json.dump(_AppConfig.cfg, f, indent=4)


AppConfig = _AppConfig()
AppConfig.load_config_file()