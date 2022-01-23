# from https://github.com/jaasonw/osu-db-tools/blob/master/osu_to_sqlite.py

from app.osu_db_reader.buffer import ReadBuffer


class OsuDbReader():

    def get_beatmap_md5_paths(filename):
        data = []

        with open(filename, 'rb') as db:
            version = ReadBuffer.read_uint(db)
            folder_count = ReadBuffer.read_uint(db)
            account_unlocked = ReadBuffer.read_bool(db)
            # skip this datetime
            ReadBuffer.read_uint(db)
            ReadBuffer.read_uint(db)
            name = ReadBuffer.read_string(db)
            num_beatmaps = ReadBuffer.read_uint(db)

            for _ in range(num_beatmaps):
                artist = ReadBuffer.read_string(db)
                artist_unicode = ReadBuffer.read_string(db)
                song_title = ReadBuffer.read_string(db)
                song_title_unicode = ReadBuffer.read_string(db)
                mapper = ReadBuffer.read_string(db)
                difficulty = ReadBuffer.read_string(db)
                audio_file = ReadBuffer.read_string(db)
                md5_hash = ReadBuffer.read_string(db)
                map_file = ReadBuffer.read_string(db)
                ranked_status = ReadBuffer.read_ubyte(db)
                num_hitcircles = ReadBuffer.read_ushort(db)
                num_sliders = ReadBuffer.read_ushort(db)
                num_spinners = ReadBuffer.read_ushort(db)
                last_modified = ReadBuffer.read_ulong(db)
                approach_rate = ReadBuffer.read_float(db)
                circle_size = ReadBuffer.read_float(db)
                hp_drain = ReadBuffer.read_float(db)
                overall_difficulty = ReadBuffer.read_float(db)
                slider_velocity = ReadBuffer.read_double(db)
                
                i = ReadBuffer.read_uint(db)
                for _ in range(i):
                    ReadBuffer.read_int_double(db)

                i = ReadBuffer.read_uint(db)
                for _ in range(i):
                    ReadBuffer.read_int_double(db)

                i = ReadBuffer.read_uint(db)
                for _ in range(i):
                    ReadBuffer.read_int_double(db)

                i = ReadBuffer.read_uint(db)
                for _ in range(i):
                    ReadBuffer.read_int_double(db)

                drain_time = ReadBuffer.read_uint(db)
                total_time = ReadBuffer.read_uint(db)
                preview_time = ReadBuffer.read_uint(db)

                # skip timing points
                # i = ReadBuffer.read_uint(db)

                for _ in range(ReadBuffer.read_uint(db)):
                    ReadBuffer.read_timing_point(db)

                beatmap_id = ReadBuffer.read_uint(db)
                beatmap_set_id = ReadBuffer.read_uint(db)
                thread_id = ReadBuffer.read_uint(db)
                grade_standard = ReadBuffer.read_ubyte(db)
                grade_taiko = ReadBuffer.read_ubyte(db)
                grade_ctb = ReadBuffer.read_ubyte(db)
                grade_mania = ReadBuffer.read_ubyte(db)
                local_offset = ReadBuffer.read_ushort(db)
                stack_leniency = ReadBuffer.read_float(db)
                gameplay_mode = ReadBuffer.read_ubyte(db)
                song_source = ReadBuffer.read_string(db)
                song_tags = ReadBuffer.read_string(db)
                online_offset = ReadBuffer.read_ushort(db)
                title_font = ReadBuffer.read_string(db)
                is_unplayed = ReadBuffer.read_bool(db)
                last_played = ReadBuffer.read_ulong(db)
                is_osz2 = ReadBuffer.read_bool(db)
                folder_name = ReadBuffer.read_string(db)
                last_checked = ReadBuffer.read_ulong(db)
                ignore_sounds = ReadBuffer.read_bool(db)
                ignore_skin = ReadBuffer.read_bool(db)
                disable_storyboard = ReadBuffer.read_bool(db)
                disable_video = ReadBuffer.read_bool(db)
                visual_override = ReadBuffer.read_bool(db)
                last_modified2 = ReadBuffer.read_uint(db)
                scroll_speed = ReadBuffer.read_ubyte(db)

                data.append({ 
                    'md5'  : md5_hash,
                    'md5h' : md5_hash[-16:-4],
                    'path' : f'{folder_name.strip()}/{map_file.strip()}' 
                })
                print(data[-1])
            
        return data


    def get_num_beatmaps(filename):
        with open(filename, 'rb') as db:
            version = ReadBuffer.read_uint(db)
            folder_count = ReadBuffer.read_uint(db)
            account_unlocked = ReadBuffer.read_bool(db)
            # skip this datetime
            ReadBuffer.read_uint(db)
            ReadBuffer.read_uint(db)
            name = ReadBuffer.read_string(db)
            num_beatmaps = ReadBuffer.read_uint(db)

        return num_beatmaps
