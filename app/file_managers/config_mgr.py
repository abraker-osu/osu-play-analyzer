import json
import random


class _AppConfig():

    cfg = { 
        'id'         : random.randint(100, 1000000),
        'osu_dir'    : '',
        'delete_gen' : True,
    }

    @staticmethod
    def load_config_file():
        try:
            with open('config.json') as f:
                _AppConfig.cfg = json.load(f)
        except FileNotFoundError:
            # Write default
            with open('config.json', 'w') as f:
                json.dump(_AppConfig.cfg, f, indent=4)

            with open('config.json') as f:
                _AppConfig.cfg = json.load(f)


    @staticmethod
    def check_config_file():
        if not 'delete_gen' in _AppConfig.cfg:
            _AppConfig.update_value('delete_gen', False)


    @staticmethod
    def update_value(key, value):
        _AppConfig.cfg[key] = value

        with open('config.json', 'w') as f:
            json.dump(_AppConfig.cfg, f, indent=4)


AppConfig = _AppConfig()
AppConfig.load_config_file()
AppConfig.check_config_file()
