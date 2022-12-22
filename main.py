import os
import re
import subprocess
from pydub import AudioSegment
from pydub.utils import make_chunks
import shutil
from PIL import Image
import struct
from decimal import Decimal
from math import isclose
from time import sleep
import msvcrt

ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'

input_id = "1000"
input_level = 1

file_osu_inprogress = "HX_NOT_DONE.osu"
file_osu_done = "HX.osu"

input_id = str(input("Enter the ID Default (1000) : ") or "1000")
input_level_raw = int(input("Enter the Level Default (1): ") or "1")
input_level = int(input_level_raw)
input_multiply_bpm = float(input("Multiply BPM (Ex. 0.5 ,0.75) Default (1) : ") or "1")
input_multiply_bpm = 1/input_multiply_bpm
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

    if filename == "HX.osu" or filename == file_osu_inprogress:
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
                    if(i == 0):
                        first_try_offset = start
                        start = 0
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
                    first_offset = first_try_offset
                # try:
                #     first_offset
                # except NameError:
                #     first_offset = first_try_offset
                # if bpm_now > 0 and first_try_offset <= first_offset:
                #     if(i != 0):
                #         first_offset = start

            longest_duration_bpm = max(bpm_duration, key=bpm_duration.get)
            longest_duration_bpm = float(longest_duration_bpm)*input_multiply_bpm
            print(
                f'The bpm with the longest duration is {60000/(float(longest_duration_bpm))}')

            print("First Offset")
            print(first_offset)

            print("Last Offset")
            print(last_offset)

            append_offset_util = round(float(longest_duration_bpm)*4)
            print("Append Offset Utility")
            print(append_offset_util)

            new_timing_last_line = time

            time[1] = longest_duration_bpm
            time[0] = last_offset + append_offset_util
            timing_lines.append(','.join(map(str, new_timing_last_line)))

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
            del lines[timing_points_index+1:hit_objects_index-1]

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
                point[0] = remove_trailing_zeros(
                    float(point[0]) + append_offset)
                # timing_offset = float(point[0])
                timing_bpm = float(point[1])
                # print(timing_offset)
                # if(i!=len(timing_lines)-1):
                #     next = timing_lines[i+1].split(',')
                #     next_timing_offset = float(next[0]) + append_offset
                #     # print()
                #     # print(next_timing_offset)
                #     next_timing_bpm = float(next[1])
                #     # print("next_timing_offset")
                #     # print(next_timing_offset)
                #     # print(timing_offset,next_timing_offset)
                #     if(timing_offset == next_timing_offset  and next_timing_bpm < 0 and timing_bpm > 0):
                # #         print(timing_bpm,next_timing_bpm)
                #         new_bpm = timing_bpm*(1 + abs(next_timing_bpm)/100)
                #         point[1] = new_bpm
                #         # print(timing_bpm,new_bpm)
                # #         print(timing_bpm, new_bpm)
                #         del timing_lines[i+1]

                if (timing_bpm > 0):
                    point[1] = str(float(point[1]) * input_multiply_bpm)
                point[2] = 4
                point[3] = 2
                timing_lines[i] = ','.join(map(str, point))
                lines.insert(timing_points_index+i+2, timing_lines[i]+'\n')
            # for timing in timing_lines:
            #     print(timing)

            print("Writing a new HX.osu File")
            with open(file_osu_inprogress, 'w', encoding='UTF-8') as f:
                f.writelines(lines)
                f.close()
            # shutil.move("HX.osu", "lib/HX.osu")

        if (audio_is_mp3):
            print("Converting MP3 to OGG")
            target_file = music_file.replace(".mp3", ".ogg")

            music_size = os.path.getsize(music_file)
            silent_segment = AudioSegment.silent(duration=append_offset)
            the_song = AudioSegment.from_mp3(music_file)
            # duration_ms = len(the_song)
            # print(duration)
            # duration_seconds = duration_ms/60
            # print(duration_seconds)
            # song_max_offset = the_song.duration_seconds*1000
            final_song = silent_segment + the_song
            # if (music_size > 20000000):
            #     final_song.export(
            #         target_file, format='ogg', bitrate="64k")
            # else:
            #     final_song.export(
            #         target_file, format='ogg', bitrate="192k")

            # parts = 4

            # duration_ms = len(final_song)
            # duration_seconds = duration_ms/60
            # print(duration_ms)
            # duration_each_parts = duration_ms/parts
            # print(duration_each_parts)

            # Make chunks of one sec
            # chunks = make_chunks(final_song, duration_each_parts)
            chunks = final_song[::300000]

            # Export all of the individual chunks as wav files
            chunks_name = []
            chunk_length = []
            for i, chunk in enumerate(chunks):
                chunk_name = "song_part_{0}.ogg".format(i)
                chunks_name.append(chunk_name)
                print("Exporting", chunk_name)
                print("Length in ms")
                print(len(chunk))
                chunk_length.append(len(chunk))
                chunk.export(chunk_name, format="ogg")
                shutil.move(chunk_name, "lib/" + chunk_name)
                if (i == 0):
                    try:
                        os.rename("lib/" + chunk_name, "lib/" + target_file)
                    except:
                        os.remove("lib/" + target_file)
                        os.rename("lib/" + chunk_name, "lib/" + target_file)
                    chunks_name[0] = target_file
            # list_of_part = []
            # for part in range(parts):
            #     list_of_part.append(duration_each_parts*part)
            # # parts = song.split_on_time([part_length_ms, 2*part_length_ms, 3*part_length_ms])
            # parts_song = final_song.split_on_time(list_of_part)

            # final_song.export(
            #     target_file, format='ogg', bitrate="192k")
            # shutil.move(target_file, "lib/" + target_file)
        else:
            shutil.move(music_file, "lib/" + music_file)

        with open(file_osu_inprogress, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            sound_samples_index = lines.index('//Storyboard Sound Samples\n')
            sound_offset = 0
            for i, name in enumerate(chunks_name):
                if i != 0:
                    sound_offset = sound_offset + chunk_length[i-1] + 1
                    lines.insert(sound_samples_index + i, "Sample," +
                                 str(sound_offset)+',0,"'+name+'",100\n')

        with open('HX.osu', 'w', encoding='UTF-8') as f:
            f.writelines(lines)
            f.close()
        shutil.move(file_osu_inprogress, "lib/" + file_osu_inprogress)
        shutil.move("HX.osu", "lib/HX.osu")

        print("Converting to BMS")
        bms_converter = subprocess.run('osu2bms HX.osu HX.bms --key-map-o2mania',
                                       shell=True, cwd="lib")

        print("Adjust Last BPM to the Line")
        with open('lib/HX.bms', 'r', encoding='UTF-8') as bms:
            bms_lines = bms.readlines()
            # print(bms_lines)
            for bms_line in reversed(bms_lines):
                if bms_line.strip():
                    bms_last_line = list(bms_line)
                    # print(bms_lines[i-1])
                    # bms_lines[-i-1] = '\n'
                    # del bms_lines[i]
                    break
            bms_last_line[3] = int(bms_last_line[3])+1
            bms_last_line[4] = 0
            bms_last_line[5] = 3

            del bms_last_line[7:]
            bms_last_line.append(64)
            bms_last_line.append("\n")
            bms_last_line_final = ''.join(map(str, bms_last_line))
            # bms_lines.remove(delete_this)
            bms_lines.append(bms_last_line_final)

        with open('lib/O2JAM.bms', 'w') as o2jam:
            o2jam.writelines(bms_lines)
            o2jam.close()

        print("Converting to OJN")
        subprocess.run('enojn2 '+input_id+' O2JAM.bms', shell=True, cwd="lib")
        shutil.move("lib/o2ma"+input_id+".ojn", "o2ma"+input_id+".ojn")
        shutil.move("lib/o2ma"+input_id+".ojm", "o2ma"+input_id+".ojm")
        # os.remove("lib/" + target_file)
        # wav_file = music_file.replace(".mp3", ".wav")
        # os.remove("lib/" + wav_file)

        for i, chunk in enumerate(chunks_name):
            chunk_wav_file = chunk.replace(".ogg", ".wav")
            os.remove("lib/" + chunk)
            os.remove("lib/" + chunk_wav_file)


print("Apply Metadata, Cover and BMP")
with open('o2ma'+input_id+'.ojn', 'r+b') as f:
    data = f.read()
    songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, time_nx, time_hx, note_ex, note_nx, note_hx, cover_offset = struct.unpack(
        ojn_struct, data[:300])

    title = title_unicode
    artist = artist_unicode
    noter = creator
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
print("Done Converting Osu to O2Jam")
