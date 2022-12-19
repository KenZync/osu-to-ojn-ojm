import os
import subprocess
from pydub import AudioSegment
import shutil
from PIL import Image
import struct

ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'

input_id = str(input("Enter the ID : ") or "1000")
input_level_raw = int(input("Enter the Level : ") or "0")
input_level = int(input_level_raw)

def is_image(filename):
    try:
        img = Image.open(filename)
        img.verify()
        return True
    except (IOError, SyntaxError) as e:
        return False

folder_path=os.getcwd()
found_image = False
for filename in os.listdir(os.getcwd()):
    file_path = os.path.join(folder_path, filename)
    lib_path = os.path.join(folder_path, 'lib')
    file_lib_path = os.path.join(lib_path, filename)
    if is_image(file_path):
        image = Image.open(file_path)
        image = image.resize((800, 600))
        cover_file_path = f'{file_lib_path}_800x600.jpg'
        image.save(cover_file_path, format='JPEG')
        image = image.resize((80, 80))
        bmp_file_path = f'{file_lib_path}_80x80.bmp'
        image.save(bmp_file_path, format='BMP')
        found_image = True

    if filename=="HX.osu":
        continue
    if filename.endswith('.osu'):
        music_file = ''
        with open(os.path.join(os.getcwd(), filename), 'r',encoding = 'utf-8') as f:
            lines = f.readlines()
            timing_points_index = lines.index('[TimingPoints]\n')
            timing_points_newline_index = lines.index('\n', timing_points_index)
            timing_points_last_line = lines[timing_points_newline_index - 1]
            timing_points_text_before_newline = timing_points_last_line.split('\n')[0]

            count = 0
            found = False
            largest = 0
            audio_is_mp3 = False
            for i,line in enumerate(lines):
                if line.startswith('TitleUnicode:'):
                    words = line.split(":")
                    title_unicode = words[1].strip().encode("cp949")
                if line.startswith('ArtistUnicode:'):
                    words = line.split(":")
                    artist_unicode = words[1].strip().encode("cp949")
                if line.startswith('Creator:'):
                    words = line.split(":")
                    creator = words[1].strip().encode("cp949")
                if line.startswith('AudioFilename:'):
                    words = line.split()
                    filename = words[1]
                    if filename.endswith('.mp3'):
                        music_file = filename
                        filename = filename[:-4] + '.ogg'
                        lines[i] = f"AudioFilename: {filename}\n"
                        audio_is_mp3 = True
                count += 1
                text = line.strip()

                if(text == '[HitObjects]'):
                    found = True
                    continue
                if found:
                    values = line.strip().split(',')
                    third_column = int(values[2])
                    last_column = int(values[-1].split(':')[0])
                    largest = max(largest, third_column, last_column)

            text_split = timing_points_text_before_newline.split(',')
            text_split[0] = str(max(int(text_split[0]),largest) + 2000)
            text_split[-1] = text_split[-1] + '\n'
            text_joined = ','.join(text_split)

            lines.insert(timing_points_newline_index, text_joined)
            with open('HX.osu', 'w', encoding='UTF-8') as f:
                f.writelines(lines)
            shutil.move("HX.osu", "lib/HX.osu")
        if(audio_is_mp3):
            target_file = music_file.replace(".mp3",".ogg")
            AudioSegment.from_mp3(music_file).export(target_file, format='ogg', bitrate="192k")
            shutil.move(target_file, "lib/" + target_file)
        else:
            shutil.move(music_file, "lib/" + music_file)
        subprocess.run('osu2bms HX.osu HX.bms --key-map-o2mania',shell=True, cwd="lib")
        subprocess.run('enojn2 '+input_id+' HX.bms',shell=True, cwd="lib")
        shutil.move("lib/o2ma"+input_id+".ojn", "o2ma"+input_id+".ojn")
        shutil.move("lib/o2ma"+input_id+".ojm", "o2ma"+input_id+".ojm")
        os.remove("lib/"+ target_file)
        wav_file = music_file.replace(".mp3",".wav")
        os.remove("lib/"+ wav_file)

with open('o2ma'+input_id+'.ojn', 'r+b') as f:
    data = f.read()
    songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, timet_nx, time_hx, note_ex, note_nx, note_hx, cover_offset = struct.unpack(
        ojn_struct, data[:300])

    title = title_unicode
    artist = artist_unicode
    noter = creator
    level_ex = input_level
    level_nx = input_level
    level_hx = input_level
    f.seek(0)
    if found_image:
        with open(cover_file_path, 'rb') as cover_file:
            cover_file_data = cover_file.read()
            cover_file_size = len(cover_file_data)
        with open(bmp_file_path, 'rb') as bmp_file:
            bmp_file_data = bmp_file.read()
            bmp_file_size = len(bmp_file_data)
        cover_size = cover_file_size
        bmp_size = bmp_file_size
        
        new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, timet_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
        f.write(new_header_data)

        
        f.seek(cover_offset)
        f.write(cover_file_data + bmp_file_data)
        os.remove(cover_file_path)
        os.remove(bmp_file_path)
    else:
        new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, timet_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
        f.write(new_header_data)
print("Done Converting Osu to O2Jam")