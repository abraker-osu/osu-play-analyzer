import sqlite3
import os

from app.misc.Logger import Logger
from app.osu_db_reader.osu_db_reader import OsuDbReader
from app.file_managers.config_mgr import AppConfig


class _MapsDB():

    logger = Logger.get_logger(__name__)

    # For resolving replays to maps
    db = sqlite3.connect('data/maps.db')
    osu_path = AppConfig.cfg['osu_dir']

    @staticmethod
    def __check_maps_table():
        _MapsDB.logger.info('Checking maps table')

        reply = _MapsDB.db.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='maps'").fetchone()[0]
        if reply > 0:
            _MapsDB.logger.info('Map table ok')
            return False

        _MapsDB.logger.info('Map table does not exist - creating')

        _MapsDB.db.execute("CREATE TABLE maps(md5 TEXT, path TEXT)")

        columns = ', '.join([ 'md5', 'path' ])
        placeholders = ':' + ', :'.join([ 'md5', 'path' ])

        data = OsuDbReader.get_beatmap_md5_paths(f'{_MapsDB.osu_path}/osu!.db')
        for entry in data:
            _MapsDB.db.execute(f'INSERT INTO maps ({columns}) VALUES ({placeholders});', tuple(entry[k] for k in entry.keys()))
        _MapsDB.db.commit()

        _MapsDB.logger.info('Map table created')
        return True


    @staticmethod
    def __check_meta_table():
        _MapsDB.logger.info('Checking meta table')

        reply = _MapsDB.db.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()[0]
        if reply > 0:
            _MapsDB.logger.info('Meta table ok')
            return False

        _MapsDB.logger.info('Meta table does not exist - creating')

        _MapsDB.db.execute("CREATE TABLE meta(num_maps INT, last_modified REAL)")

        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{_MapsDB.osu_path}/osu!.db')
        last_modified_read = os.stat(f'{_MapsDB.osu_path}/osu!.db').st_mtime

        columns = ', '.join([ 'num_maps', 'last_modified' ])
        placeholders = ':' + ', :'.join([ 'num_maps', 'last_modified' ])

        _MapsDB.db.execute(f'INSERT INTO meta ({columns}) VALUES ({placeholders});', (num_beatmaps_read, last_modified_read))
        _MapsDB.db.commit()

        _MapsDB.logger.info('Meta table created')
        return True


    def check_db(self):
        if not os.path.isdir(AppConfig.cfg['osu_dir']):
            return

        maps_table_built = _MapsDB.__check_maps_table()
        meta_table_built = _MapsDB.__check_meta_table()

        if maps_table_built and meta_table_built:
            return
        
        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{_MapsDB.osu_path}/osu!.db')
        num_beatmaps_save = _MapsDB.db.execute('SELECT num_maps FROM meta').fetchone()
        if num_beatmaps_save != None:
            num_beatmaps_save = num_beatmaps_save[0]

        last_modified_read = os.stat(f'{_MapsDB.osu_path}/osu!.db').st_mtime
        last_modified_save = _MapsDB.db.execute('SELECT last_modified FROM meta').fetchone()
        if last_modified_save != None:
            last_modified_save = last_modified_save[0]

        num_maps_changed = num_beatmaps_read != num_beatmaps_save
        osu_db_modified = last_modified_read != last_modified_save

        if num_maps_changed or osu_db_modified:
            if osu_db_modified:
                # TODO: This needs a GUI interface
                #user_input = input('osu!.db was modified. If you modified a map for testing, it will not be found until you update db. Update db? (y/n)')
                #if not 'y' in user_input.lower(): return
                _MapsDB.logger.info(f'osu!.db was modified. If you modified or added maps, they will not be found until you update db')
                return

            MapsDB.update_maps_db()

            if num_beatmaps_save != None:
                _MapsDB.logger.info(f'Added {num_beatmaps_read - num_beatmaps_save} new maps')
            else:
                _MapsDB.logger.info(f'Added {num_beatmaps_read} new maps')


    def update_maps_db(self):
        osu_path = AppConfig.cfg['osu_dir']

        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{osu_path}/osu!.db')
        last_modified_read = os.stat(f'{osu_path}/osu!.db').st_mtime

        data = OsuDbReader.get_beatmap_md5_paths(f'{_MapsDB.osu_path}/osu!.db')

        # Insert missing entries
        columns = ', '.join([ 'md5', 'path' ])
        placeholders = ':' + ', :'.join([ 'md5', 'path' ])
        
        # Drop maps table
        _MapsDB.db.execute('DROP TABLE maps')
        _MapsDB.db.commit()

        _MapsDB.db.execute("CREATE TABLE meta(num_maps INT, last_modified REAL)")

        # Add maps into table
        for entry in data:
            _MapsDB.db.execute(f'INSERT INTO maps ({columns}) VALUES ({placeholders});', tuple(entry[k] for k in entry.keys()))

        _MapsDB.db.execute(f'UPDATE meta SET num_maps = {num_beatmaps_read};')
        _MapsDB.db.execute(f'UPDATE meta SET last_modified = {last_modified_read};')

        _MapsDB.db.commit()


    def get_map_file_name(self, map_md5, filename=True):
        reply = _MapsDB.db.execute(f'SELECT path FROM maps WHERE md5 = "{map_md5}"').fetchone()
        
        if reply != None:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/{reply[0]}' if filename else reply[0]
            return map_file_name, False
        
        # See if it's a generated map, it has its md5 hash in the name
        map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/{map_md5}.osu' if filename else map_md5
        if not os.path.isfile(map_file_name):
            return None, False

        return map_file_name, True


    def md5h_to_md5h_str_func(self, md5h):
        # Since map_md5h is the integer representation of a portion of the lower 
        # half of the md5 hash, there might be zeros in most significant digits of
        # the resultant uin64 encoded value. It's possible to detect that by 
        # checking size of the resulting hash string in hex form 
        # (it must be 12 characters). From there, fill the front with zeros to 
        # make it complete
        map_md5h_str = hex(md5h)[2:-4]
        if len(map_md5h_str) < 12:
            map_md5h_str = '0'*(12 - len(map_md5h_str)) + map_md5h_str

        return map_md5h_str


MapsDB = _MapsDB()
MapsDB.check_db()
