
import os
import struct


def apply_metadata(inprogress_osu_folder, output_folder, input_id, input_level, use_title, metadata_lines, found_image):
    ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'
    with open(os.path.join(output_folder, 'o2ma'+input_id+'.ojn'), 'r+b') as f:
        data = f.read()
        songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, time_nx, time_hx, note_ex, note_nx, note_hx, cover_offset = struct.unpack(
            ojn_struct, data[:300])

        if (use_title):
            try:
                title = metadata_lines["TitleUnicode"].encode("cp949")
            except:
                title = metadata_lines["Title"].encode("cp949")
        else:
            title = metadata_lines["Version"].encode("cp949")

        try:
            artist = metadata_lines["ArtistUnicode"].encode("cp949")
        except:
            artist = metadata_lines["Artist"].encode("cp949")
        noter = metadata_lines["Creator"].encode("cp949")
        level_ex = input_level
        level_nx = input_level
        level_hx = input_level

        new_cover_offset = note_nx
        cover_offset = int(new_cover_offset)
        f.seek(note_nx)

        note_nx = 300
        note_hx = 300
        f.truncate()

        if (measure_ex > 300):
            measure_ex = 300

        if (measure_nx > 300):
            measure_nx = 300

        if (measure_hx > 300):
            measure_hx = 300

        if (notecount_ex > 65535):
            notecount_ex = 65535

        if (notecount_nx > 65535):
            notecount_nx = 65535

        if (notecount_hx > 65535):
            notecount_hx = 65535

        f.seek(0)
        if found_image:
            cover_file_path = os.path.join(
                inprogress_osu_folder, '800x600.jpg')
            bmp_file_path = os.path.join(inprogress_osu_folder, '80x80.bmp')
            cover_file_data = open(cover_file_path, 'rb').read()
            cover_size = len(cover_file_data)
            bmp_file_data = open(bmp_file_path, 'rb').read()
            bmp_size = len(bmp_file_data)

            new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex,
                                            measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, time_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
            f.write(new_header_data)
            f.seek(new_cover_offset)
            f.write(cover_file_data + bmp_file_data)
            os.remove(cover_file_path)
            os.remove(bmp_file_path)

        else:
            new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex,
                                            measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, time_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
            f.write(new_header_data)
