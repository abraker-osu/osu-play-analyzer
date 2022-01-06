import tinydb
import os

from app.osu_db_reader.osu_db_reader import OsuDbReader
from app.file_managers.config_mgr import AppConfig


class _MapsDB():

    # For resolving replays to maps
    db = tinydb.TinyDB('data/maps.json')
    maps_table = db.table('maps')
    meta_table = db.table('meta')

    @staticmethod
    def check_maps_db():
        osu_path = AppConfig.cfg['osu_dir']

        if len(_MapsDB.maps_table) == 0:
            data = OsuDbReader.get_beatmap_md5_paths(f'{osu_path}/osu!.db')
            _MapsDB.maps_table.insert_multiple(data)
            
            num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{osu_path}/osu!.db')
            _MapsDB.meta_table.upsert({ 'num_maps' : num_beatmaps_read }, tinydb.where('num_maps').exists())

            last_modified_read = os.stat(f'{osu_path}/osu!.db').st_mtime
            _MapsDB.meta_table.upsert({ 'last_modified' : last_modified_read }, tinydb.where('last_modified').exists())

            print('Map table did not exist - created it')
            return

        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{osu_path}/osu!.db')
        num_beatmaps_save = _MapsDB.meta_table.get(tinydb.where('num_maps').exists())
        if num_beatmaps_save != None:
            num_beatmaps_save = num_beatmaps_save['num_maps']

        last_modified_read = os.stat(f'{osu_path}/osu!.db').st_mtime
        last_modified_save = _MapsDB.meta_table.get(tinydb.where('last_modified').exists())
        if last_modified_save != None:
            last_modified_save = last_modified_save['last_modified']

        num_maps_changed = num_beatmaps_read != num_beatmaps_save
        osu_db_modified = last_modified_read != last_modified_save

        if num_maps_changed or osu_db_modified:
            if osu_db_modified:
                user_input = input('osu!.db was modified. If you modified a map for testing, it will not be found until you rebuild db. Rebuild db? (y/n)')
                if not 'y' in user_input.lower(): return

            data = OsuDbReader.get_beatmap_md5_paths(f'{osu_path}/osu!.db')
            _MapsDB.db.drop_table('maps')
            _MapsDB.maps_table = _MapsDB.db.table('maps')
            _MapsDB.maps_table.insert_multiple(data)

            _MapsDB.meta_table.upsert({ 'num_maps' : num_beatmaps_read }, tinydb.where('num_maps').exists())
            _MapsDB.meta_table.upsert({ 'last_modified' : last_modified_read }, tinydb.where('last_modified').exists())

        print(num_beatmaps_read, num_beatmaps_save)
        print(last_modified_read, last_modified_save)


    def rebuild_maps_db(self):
        osu_path = AppConfig.cfg["osu_dir"]

        num_beatmaps_read = OsuDbReader.get_num_beatmaps(f'{osu_path}/osu!.db')
        last_modified_read = os.stat(f'{osu_path}/osu!.db').st_mtime

        data = OsuDbReader.get_beatmap_md5_paths(f'{osu_path}/osu!.db')
        self.db.drop_table('maps')
        self.maps_table = self.db.table('maps')
        self.maps_table.insert_multiple(data)

        self.meta_table.upsert({ 'num_maps' : num_beatmaps_read }, tinydb.where('num_maps').exists())
        self.meta_table.upsert({ 'last_modified' : last_modified_read }, tinydb.where('last_modified').exists())


    def get_map_file_name(self, map_md5, md5h=False, reprocess_if_missing=False):
        maps = MapsDB.maps_table.search(tinydb.where('md5h' if md5h else 'md5') == map_md5)

        if len(maps) != 0:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/{maps[0]["path"]}'
            return map_file_name

        if not reprocess_if_missing:
            print('Associated beatmap not found. Do you have it?')
            return ''

        print('Associated beatmap not found, rebuilding maps database...')
        MapsDB.rebuild_maps_db()
        maps = MapsDB.maps_table.search(tinydb.where('md5') == map_md5)

        if len(maps) != 0:
            map_file_name = f'{AppConfig.cfg["osu_dir"]}/Songs/{maps[0]["path"]}'
            return map_file_name

        print('Associated beatmap not found. Do you have it?')
        return ''



MapsDB = _MapsDB()
MapsDB.check_maps_db()