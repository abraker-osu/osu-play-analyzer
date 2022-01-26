import sqlite3
import glob
import os
import time

from app.osu_db_reader.osu_db_reader import OsuDbReader
from app.file_managers.config_mgr import AppConfig


class _MapsDB():

    # For resolving replays to maps
    db = sqlite3.connect("data/maps.db")
    osu_path = AppConfig.cfg['osu_dir']

    @staticmethod
    def __check_maps_table():
        reply = _MapsDB.db.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='maps'").fetchone()[0]
        if reply == 0:
            _MapsDB.db.execute("CREATE TABLE maps(md5 TEXT, md5h TEXT, path TEXT)")

            columns = ', '.join([ 'md5', 'md5h', 'path' ])
            placeholders = ':' + ', :'.join([ 'md5', 'md5h', 'path' ])

            data = OsuDbReader.get_beatmap_md5_paths(f'{_MapsDB.osu_path}/osu!.db')
            for entry in data:
                _MapsDB.db.execute(f'INSERT INTO maps ({columns}) VALUES ({placeholders});', tuple(entry[k] for k in entry.keys()))

            print('Map table did not exist - created it')
            _MapsDB.db.commit()
            return True

        return False


    @staticmethod
    def __check_meta_table():
        reply = _MapsDB.db.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()[0]
        if reply == 0:
            _MapsDB.db.execute("CREATE TABLE meta(num_maps INT, last_modified REAL)")

            num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{_MapsDB.osu_path}/osu!.db')
            last_modified_read = os.stat(f'{_MapsDB.osu_path}/osu!.db').st_mtime

            columns = ', '.join([ 'num_maps', 'last_modified' ])
            placeholders = ':' + ', :'.join([ 'num_maps', 'last_modified' ])

            _MapsDB.db.execute(f'INSERT INTO meta ({columns}) VALUES ({placeholders});', (num_beatmaps_read, last_modified_read))

            print('Meta table did not exist - created it')
            _MapsDB.db.commit()
            return True

        return False


    def check_db(self):
        maps_table_built = _MapsDB.__check_maps_table()
        meta_table_built = _MapsDB.__check_meta_table()

        if maps_table_built and meta_table_built:
            print('Map db did not exist - created it')
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
                user_input = input('osu!.db was modified. If you modified a map for testing, it will not be found until you update db. Update db? (y/n)')
                if not 'y' in user_input.lower(): return

            MapsDB.update_maps_db()

            if num_beatmaps_save != None:
                print(f'Added {num_beatmaps_read - num_beatmaps_save} new maps')
            else:
                print(f'Added {num_beatmaps_read} new maps')


    def update_maps_db(self):
        osu_path = AppConfig.cfg["osu_dir"]

        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{osu_path}/osu!.db')
        last_modified_read = os.stat(f'{osu_path}/osu!.db').st_mtime

        data = OsuDbReader.get_beatmap_md5_paths(f'{_MapsDB.osu_path}/osu!.db')

        # Insert missing entries
        columns = ', '.join([ 'md5', 'md5h', 'path' ])
        placeholders = ':' + ', :'.join([ 'md5', 'md5h', 'path' ])
        
        for entry in data:
            reply = _MapsDB.db.execute(f'SELECT md5 FROM maps WHERE md5="{entry["md5"]}"').fetchone()
            if reply == None:
                _MapsDB.db.execute(f'INSERT INTO maps ({columns}) VALUES ({placeholders});', tuple(entry[k] for k in entry.keys()))

        _MapsDB.db.execute(f'UPDATE meta SET num_maps = {num_beatmaps_read};')
        _MapsDB.db.execute(f'UPDATE meta SET last_modified = {last_modified_read};')


    def get_map_file_name(self, map_md5, md5h=False, reprocess_if_missing=False):
        field = "md5h" if md5h else "md5"
        reply = _MapsDB.db.execute(f'SELECT path FROM maps WHERE {field}="{map_md5}"').fetchone()
        
        if reply != None:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/{reply[0]}'
            return map_file_name

        # Try to find the map file by hash
        if md5h == False:
            # See if it's a generated map, it has its md5 hash in the name
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/{map_md5}.osu'
            if not os.path.isfile(map_file_name):
                return

            return map_file_name
        else:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/osu_play_analyzer/*{map_md5}*.osu'
            matches = glob.glob(map_file_name, recursive=False)

            if len(matches) > 0:
                return matches[0]

        # Find by hash failed, reprocess the db and try if enabled
        if not reprocess_if_missing:
            print('Associated beatmap not found. If you modified or added a new map since starting osu!, close osu! and rebuild db. Then try again.')
            return ''

        print('Associated beatmap not found, updating maps database...')
        MapsDB.update_maps_db()
        reply = _MapsDB.db.execute(f'SELECT path FROM maps WHERE {field}="{map_md5}"').fetchone()

        if reply != None:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/{reply[0]}'
            return map_file_name

        print('Associated beatmap not found. Do you have it?')
        return ''


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
