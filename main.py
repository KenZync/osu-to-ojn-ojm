import os
import re
import subprocess
from pydub import AudioSegment
import shutil
from PIL import Image
import struct
import glob
from utils import *
import concurrent.futures

ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'


def convert_to_o2jam(input):
    index, input_id, osu_file, input_level, input_multiply_bpm, use_title = input

    input_id = str(int(input_id)+index)

    found_image = False

    file_osu_inprogress = str(index) + "_HX_NOT_DONE.osu"
    file_osu_done = str(index) + "_HX.osu"

    lib_path = os.path.join('', 'lib')
    file_lib_path = os.path.join(lib_path, osu_file)

    print("Found Map: ", osu_file)
    music_file = ''
    with open(os.path.join(os.getcwd(), osu_file), 'r', encoding='utf-8') as f:
        lines = f.readlines()

        timing_points_index = lines.index('[TimingPoints]\n')
        hit_objects_index = lines.index('[HitObjects]\n')

        try:
            epilepsy_warning = lines.index('EpilepsyWarning: 1\n')
            lines[epilepsy_warning] = '\n'
        except:
            print("EpilepsyWarning Not Found")

        audio_is_mp3 = False

        timing_lines = []
        object_lines = []
        events_lines = []

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
            elif osu_section == 'events':
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
            if line.startswith('AudioLeadIn:'):
                lines[i] = "AudioLeadIn:0\n"
            if line.startswith('Version:'):
                words = line[8:].strip()
                try:
                    difficulty_name = words.encode("cp949")
                except:
                    difficulty_name = title_unicode
        # Check for last note offset

        try:
            del last_offset
        except:
            print("no last offset")

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
        start = float(bpm_list[0].split(',')[0])
        first_offset = start
        for i, each_time in enumerate(bpm_list):
            time = each_time.split(',')

            start = float(time[0])
            if (i == 0):
                start = 0
            try:
                end = float(bpm_list[i+1].split(',')[0])
            except:
                end = last_offset
            duration = end - start
            bpm_now = round(float(time[1]), 10)
            if bpm_now in bpm_duration:
                bpm_duration[bpm_now] += duration
            else:
                bpm_duration[bpm_now] = duration

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
            timing_offset = float(point[0])
            timing_bpm = float(point[1])

            if i < len(timing_lines) - 1:
                next = timing_lines[i+1].split(',')
                next_timing_offset = float(next[0])
                next_timing_bpm = float(next[1])
                if (timing_offset == next_timing_offset and next_timing_bpm < 0 and timing_bpm > 0):
                    point[1] = timing_bpm*(abs(next_timing_bpm)/100)
                    next[1] = -100
                    timing_lines[i+1] = ','.join(map(str, next))

            point[0] = remove_trailing_zeros(
                float(point[0]) + append_offset)

            if (timing_bpm > 0):
                point[1] = str(float(point[1]) * input_multiply_bpm)
            point[2] = 4
            point[3] = 2

            timing_lines[i] = ','.join(map(str, point))
            lines.insert(timing_points_index+i+2, timing_lines[i]+'\n')

        print("Writing a new HX.osu File")
        with open("lib/"+file_osu_inprogress, 'w', encoding='UTF-8') as f:
            f.writelines(lines)
            f.close()

    image_file_name = events_lines[1].split(',')[2].strip('\"')
    print(image_file_name)
    if is_image(image_file_name):
        print("Found Image: ", image_file_name)
        image = Image.open(image_file_name)
        image = image.convert("RGB")
        image = image.resize((800, 600))
        cover_file_path = f'{file_lib_path}_800x600.jpg'
        image.save(cover_file_path, format='JPEG')
        image = image.resize((80, 80))
        bmp_file_path = f'{file_lib_path}_80x80.bmp'
        image.save(bmp_file_path, format='BMP')
        found_image = True
    if (audio_is_mp3):
        print("Converting MP3 to OGG")
        target_file = music_file.replace(".mp3", ".ogg")
        silent_segment = AudioSegment.silent(duration=append_offset)
        the_song = AudioSegment.from_mp3(music_file)
        final_song = silent_segment + the_song
        chunks = final_song[::300000]

        # Export all of the individual chunks as wav files
        chunks_name = []
        chunk_length = []
        for i, chunk in enumerate(chunks):
            chunk_name = str(index)+"_song_part_{0}.ogg".format(i)
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
    else:
        shutil.move(music_file, "lib/" + music_file)

    with open("lib/"+file_osu_inprogress, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sound_samples_index = lines.index('//Storyboard Sound Samples\n')
        sound_offset = 0
        for i, name in enumerate(chunks_name):
            if i != 0:
                sound_offset = sound_offset + chunk_length[i-1] + 1
                lines.insert(sound_samples_index + i, "Sample," +
                             str(sound_offset)+',0,"'+name+'",100\n')

    with open("lib/"+file_osu_done, 'w', encoding='UTF-8') as f:
        f.writelines(lines)
        f.close()

    print("Converting to BMS")
    bms_file = file_osu_done.replace(".osu", ".bms")
    subprocess.run('osu2bms '+file_osu_done+' '+bms_file+' --key-map-o2mania',
                   shell=True, cwd="lib")

    print("Adjust Last BPM to the Line")
    with open('lib/'+bms_file, 'r', encoding='UTF-8') as bms:
        bms_lines = bms.readlines()
        for bms_line in reversed(bms_lines):
            if bms_line.strip():
                bms_last_line = list(bms_line)
                break
        bms_last_line[3] = int(bms_last_line[3])+1
        bms_last_line[4] = 0
        bms_last_line[5] = 3

        del bms_last_line[7:]
        bms_last_line.append(64)
        bms_last_line.append("\n")
        bms_last_line_final = ''.join(map(str, bms_last_line))
        bms_lines.append(bms_last_line_final)
    o2jam_bms = "O2JAM_"+bms_file
    with open('lib/'+o2jam_bms, 'w', encoding='utf-8') as o2jam:
        o2jam.writelines(bms_lines)
        o2jam.close()

    print("Converting to OJN")
    subprocess.run('enojn2 '+input_id+' '+o2jam_bms, shell=True, cwd="lib")
    shutil.move("lib/o2ma"+input_id+".ojn", "o2ma"+input_id+".ojn")
    shutil.move("lib/o2ma"+input_id+".ojm", "o2ma"+input_id+".ojm")

    for i, chunk in enumerate(chunks_name):
        chunk_wav_file = chunk.replace(".ogg", ".wav")
        os.remove("lib/" + chunk)
        os.remove("lib/" + chunk_wav_file)

    print("Apply Metadata, Cover and BMP")
    with open('o2ma'+input_id+'.ojn', 'r+b') as f:
        data = f.read()
        songid, signature, encode_version, genre, bpm, level_ex, level_nx, level_hx, unknown, event_ex, event_nx, event_hx, notecount_ex, notecount_nx, notecount_hx, measure_ex, measure_nx, measure_hx, package_ex, package_nx, package_hx, old_1, old_2, old_3, bmp_size, old_4, title, artist, noter, ojm_file, cover_size, time_ex, time_nx, time_hx, note_ex, note_nx, note_hx, cover_offset = struct.unpack(
            ojn_struct, data[:300])
        if (use_title):
            title = title_unicode
        else:
            title = difficulty_name
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
    print("Done Converting Osu to O2Jam")


def main():
    print("Osu to O2jam Converter")
    folder_path = os.getcwd()
    osu_files = glob.glob(folder_path + '/*.osu')
    osu_count = len(osu_files)

    # input_id = "1000"
    # input_level = 1
    # use_title = True
    # input_multiply_bpm = 1

    print(".osu count :", osu_count)
    if(osu_count > 1):
        print("Multiple .osu file detected")
        use_title = yes_or_no("Would you like to use Title (Y) / Difficulty (N) as a Song name in o2jam?")
    else:
        use_title = True
    input_id = str(input("Enter the ID Default (1000) : ") or "1000")
    input_level_raw = int(input("Enter the Level Default (1): ") or "1")
    input_level = int(input_level_raw)
    input_multiply_bpm = float(input("Multiply BPM (Ex. 0.5 ,0.75) Default (1) : ") or "1")
    input_multiply_bpm = 1/input_multiply_bpm

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for index, osu_file in enumerate(osu_files):
            executor.submit(convert_to_o2jam, (index, input_id,
                            osu_file, input_level, input_multiply_bpm, use_title))
    print("ALL DONE!")

if __name__ == '__main__':
    main()
