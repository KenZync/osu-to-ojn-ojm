import os
import re
import subprocess
from pydub import AudioSegment
import shutil
from PIL import Image
import struct
from decimal import Decimal
from math import isclose

ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'

input_id = str(input("Enter the ID : ") or "1000")
input_level_raw = int(input("Enter the Level : ") or "0")
input_level = int(input_level_raw)

# input_id = "1000"
# input_level = 1

# Check is a file an image


def is_image(filename):
    try:
        img = Image.open(filename)
        img.verify()
        return True
    except (IOError, SyntaxError) as e:
        return False

# Float, String compatibility


def remove_trailing_zeros(number):
    float_number = float(number)
    if isclose(float_number, int(float_number), rel_tol=1e-9):
        return int(float_number)
    else:
        return "{:f}".format(float_number)


folder_path = os.getcwd()
found_image = False
for filename in os.listdir(os.getcwd()):
    file_path = os.path.join(folder_path, filename)
    lib_path = os.path.join(folder_path, 'lib')
    file_lib_path = os.path.join(lib_path, filename)

    if is_image(file_path):
        print("Found Image: ", filename)
        image = Image.open(file_path)
        image = image.convert("RGB")
        image = image.resize((800, 600))
        cover_file_path = f'{file_lib_path}_800x600.jpg'
        image.save(cover_file_path, format='JPEG')
        image = image.resize((80, 80))
        bmp_file_path = f'{file_lib_path}_80x80.bmp'
        image.save(bmp_file_path, format='BMP')
        found_image = True

    if filename == "HX.osu":
        continue

    if filename.endswith('.osu'):
        print("Found Map: ", filename)
        music_file = ''
        with open(os.path.join(os.getcwd(), filename), 'r', encoding='utf-8') as f:
            lines = f.readlines()

            timing_points_index = lines.index('[TimingPoints]\n')
            hit_objects_index = lines.index('[HitObjects]\n')

            try:
                epilepsy_warning = lines.index('EpilepsyWarning: 1\n')
                lines[epilepsy_warning] = '\n'
            except:
                print("EpilepsyWarning Not Found")

            found = False
            largest = 0
            audio_is_mp3 = False

            timing_lines = []
            object_lines = []
            events_lines = []

            timing_line = 0
            object_line = 0
            section_reg = re.compile('^\[([a-zA-Z0-9]+)\]$')
            osu_section = None
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                match = section_reg.match(line)
                if match:
                    osu_section = match.group(1).lower()
                    continue
                if osu_section == 'timingpoints':
                    timing_lines.append(line)
                elif osu_section == 'hitobjects':
                    object_lines.append(line)
                    events_lines.append(line)

                if line.startswith('Title:'):
                    words = line[6:].strip()
                    title_non_unicode = words.encode("cp949")
                if line.startswith('TitleUnicode:'):
                    words = line[13:].strip()
                    try:
                        title_unicode = words.encode("cp949")
                    except:
                        title_unicode = title_non_unicode
                        print("TitleUnicode Error, used Title")
                    print("Title : ", title_unicode)
                if line.startswith('Artist:'):
                    words = line[7:].strip()
                    artist_non_unicode = words.encode("cp949")
                    print("Artist : ", artist_non_unicode)
                if line.startswith('ArtistUnicode:'):
                    words = line[14:].strip()
                    try:
                        artist_unicode = words.encode("cp949")
                    except:
                        artist_unicode = artist_non_unicode
                        print("ArtistUnicode Error, used Artist")
                    print("Artist : ", artist_unicode)
                if line.startswith('Creator:'):
                    words = line[8:].strip()
                    try:
                        creator = words.encode("cp949")
                    except:
                        creator = words.encode()
                    print("Creator : ", creator)
                if line.startswith('AudioFilename:'):
                    filename = line[15:].strip()
                    print("Audio File : ", filename)
                    if filename.endswith('.mp3'):
                        music_file = filename
                        filename = filename[:-4] + '.ogg'
                        lines[i] = f"AudioFilename: {filename}\n"
                        audio_is_mp3 = True

            # Check for last note offset
            for object in object_lines:
                note = object.split(',')
                third_column = remove_trailing_zeros(note[2])
                last_column = remove_trailing_zeros(note[-1].split(':')[0])
                try:
                    last_offset
                except NameError:
                    last_offset = third_column
                last_offset = max(last_offset, third_column, last_column)

            bpm_list = []
            # Get BPM List
            for i, timing in enumerate(timing_lines):
                point = timing.split(',')
                timing_offset = float(point[0])
                timing_bpm = float(point[1])

                if (timing_bpm > 0):
                    bpm_list.append(timing)

            # Find Main BPM
            bpm_duration = {}
            for i, each_time in enumerate(bpm_list):
                time = each_time.split(',')

                try:
                    start = float(time[0])
                    end = float(bpm_list[i+1].split(',')[0])
                except:
                    end = last_offset
                duration = end - start
                bpm_now = round(float(time[1]), 10)
                if bpm_now in bpm_duration:
                    bpm_duration[bpm_now] += duration
                else:
                    bpm_duration[bpm_now] = duration

                try:
                    first_offset
                except NameError:
                    first_offset = start
                if (bpm_now > 0 and start <= first_offset):
                    first_offset = remove_trailing_zeros(start)

            longest_duration_bpm = max(bpm_duration, key=bpm_duration.get)
            print(
                f'The bpm with the longest duration is {60000/float(longest_duration_bpm)}')

            print(time)
            time[0]= last_offset + 2000
            time[1]= longest_duration_bpm
            new_timing_last_line=time
            print(new_timing_last_line)
            timing_lines.append(','.join(map(str, new_timing_last_line)))

            print("First Offset")
            print(first_offset)

            print("Last Offset")
            print(last_offset)

            append_offset_util = round(float(longest_duration_bpm)*4)
            print("Append Offset Utility")
            print(append_offset_util)

            if (first_offset < append_offset_util):
                print("True")
                append_offset = append_offset_util - first_offset
            else:
                room = first_offset//append_offset_util
                offset_need = append_offset_util*(room+1)
                append_offset = offset_need - first_offset
            while (append_offset + first_offset < 2000):
                print("Offset is < 2000")
                append_offset = append_offset + append_offset_util
            print("APPEND OFFSET")
            print(append_offset)
            print("NEW FIRST BPM OFFSET")
            print(append_offset + first_offset)

            # Delete ALL Hit Objects
            del lines[hit_objects_index+1:]

            # Rewrite Notes to Move to aligned first room
            for i, object in enumerate(object_lines):
                note = object.split(',')
                third_column = remove_trailing_zeros(note[2])
                last_column = note[-1].split(':')
                note[2] = third_column + append_offset
                if (last_column[0] != "0"):
                    last_column[0] = remove_trailing_zeros(
                        last_column[0]) + append_offset
                    note[-1] = ':'.join(map(str, last_column))
                object_lines[i] = ','.join(map(str, note))
                lines.insert(hit_objects_index+i+1, object_lines[i]+'\n')


            # Delete ALL Offsets
            del lines[timing_points_index+1:hit_objects_index-2]

            # Add Offset at 0 to fix Bug
            first_timing = timing_lines[0].split(',')
            if (float(first_timing[0]) > 0):
                first_timing[0] = 0
                first_timing[2] = 4
                first_timing[3] = 2
                first_timing[1] = longest_duration_bpm
                first_timing = ','.join(map(str, first_timing))
                lines.insert(timing_points_index+1, first_timing+'\n')

            # Rewrite BPM Lines (BETA)
            for i, timing in enumerate(timing_lines):
                point = timing.split(',')
                point[2] = 4
                point[3] = 2
                point[0] = remove_trailing_zeros(point[0]) + append_offset
                timing_lines[i] = ','.join(map(str, point))
                lines.insert(timing_points_index+i+2, timing_lines[i]+'\n')

            print("Writing a new HX.osu File")
            with open('HX.osu', 'w', encoding='UTF-8') as f:
                f.writelines(lines)
            shutil.move("HX.osu", "lib/HX.osu")
        if (audio_is_mp3):
            print("Converting MP3 to OGG")
            target_file = music_file.replace(".mp3", ".ogg")

            silent_segment = AudioSegment.silent(duration=append_offset)
            the_song = AudioSegment.from_mp3(music_file)
            final_song = silent_segment + the_song
            final_song.export(
                target_file, format='ogg', bitrate="192k")
            shutil.move(target_file, "lib/" + target_file)
        else:
            shutil.move(music_file, "lib/" + music_file)
        print("Converting to BMS")
        subprocess.run('osu2bms HX.osu HX.bms --key-map-o2mania',
                       shell=True, cwd="lib")

        print("Converting to OJN")
        subprocess.run('enojn2 '+input_id+' HX.bms', shell=True, cwd="lib")
        shutil.move("lib/o2ma"+input_id+".ojn", "o2ma"+input_id+".ojn")
        shutil.move("lib/o2ma"+input_id+".ojm", "o2ma"+input_id+".ojm")
        os.remove("lib/" + target_file)
        wav_file = music_file.replace(".mp3", ".wav")
        os.remove("lib/" + wav_file)

print("Apply Metadata, Cover and BMP")
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

    if (measure_ex > 300):
        measure_ex = 300

    if (measure_nx > 300):
        measure_nx = 300

    if (measure_hx > 300):
        measure_hx = 300

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

        new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex,
                                      measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, timet_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
        f.write(new_header_data)
        f.seek(cover_offset)
        f.write(cover_file_data + bmp_file_data)
        os.remove(cover_file_path)
        os.remove(bmp_file_path)

    else:
        new_header_data = struct.pack(ojn_struct, songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex,
                                      measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, timet_nx, time_hx, note_ex, note_nx, note_hx, cover_offset)
        f.write(new_header_data)
print("Done Converting Osu to O2Jam")
