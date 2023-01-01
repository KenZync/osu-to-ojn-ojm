import os
import struct
import sys
import logging
import glob
import re
import math
import shutil
import imghdr
import subprocess
from multiprocessing import freeze_support
from osu_writer import write_osu
from utils import yes_or_no
import concurrent.futures


def convert_to_o2jam(index, input_id, input_level, input_multiply_bpm, use_title, osu, parent, inprogress_osu_folder, input_offset):
    input_id = str(input_id + index)

    with open(osu, encoding="utf-8") as file:
        lines = file.readlines()

    general_lines = {}
    editor_lines = {}
    metadata_lines = {}
    difficulty_lines = {}
    timing_lines = []
    object_lines = []
    event_lines = []
    beatmap = {"timingPoints": [], "hitObjects": []}

    section_reg = re.compile('^\[([a-zA-Z0-9]+)\]$')
    key_val_reg = re.compile('^([a-zA-Z0-9]+)[ ]*:[ ]*(.+)$')
    osu_section = None

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        match_section = section_reg.match(line)
        if match_section:
            osu_section = match_section.group(1).lower()
            continue

        match_key_val = key_val_reg.match(line)
        if osu_section == 'general' and match_key_val:
            general_lines[match_key_val.group(1)] = match_key_val.group(2)
        if osu_section == 'editor' and match_key_val:
            editor_lines[match_key_val.group(1)] = match_key_val.group(2)
        if osu_section == 'metadata' and match_key_val:
            metadata_lines[match_key_val.group(1)] = match_key_val.group(2)
        if osu_section == 'difficulty' and match_key_val:
            difficulty_lines[match_key_val.group(1)] = match_key_val.group(2)
        if osu_section == 'events':
            event_lines.append(line)
        elif osu_section == 'timingpoints':
            timing_lines.append(line)
        elif osu_section == 'hitobjects':
            object_lines.append(line)

    first_timing = None
    last_timing = None
    first_note = None
    last_note = None
    bpm_list = []

    for line in timing_lines:
        points = line.split(',')
        offset = int(float(points[0]))
        if first_timing is None or offset < first_timing:
            first_timing = offset
        if last_timing is None or offset > last_timing:
            last_timing = offset
        timing_point = {"offset": offset,
                        "beatLength": float(points[1]),
                        "velocity": 1,
                        "timingSignature": 4,
                        "sampleSetId": 2,
                        "customSampleIndex": int(points[4]),
                        "sampleVolume": int(points[5]),
                        "timingChange": 1,
                        "kiaiTimeActive": points[7]}
        if not math.isnan(timing_point["beatLength"]) and timing_point["beatLength"] != 0:
            if timing_point["beatLength"] > 0:
                bpm = round(60000/timing_point["beatLength"], 3)
                timing_point["bpm"] = bpm*input_multiply_bpm
                bpm_list.append(timing_point)
            else:
                timing_point["velocity"] = round(
                    abs(100 / timing_point["beatLength"]), 10)
        beatmap["timingPoints"].append(timing_point)
    print("first timing:", first_timing)
    print("last timing:", last_timing)

    for obj in object_lines:
        objects = obj.split(',')
        note_offset = int(objects[2])
        last_column = objects[5].split(':')
        ln_offset = int(last_column[0])
        if first_note is None or note_offset < first_note:
            first_note = note_offset
        if last_note is None or note_offset > last_note:
            last_note = note_offset
        if ln_offset > last_note:
            last_note = ln_offset

        hit_object = {"x": objects[0],
                      "y": objects[1],
                      "offset": note_offset,
                      "objectType": objects[3],
                      "soundType": objects[4],
                      "offsetLongNote": ln_offset,
                      "rest": last_column[1:]}
        beatmap["hitObjects"].append(hit_object)

    print("first note:", first_note)
    print("last note:", last_note)

    bpm_now = None
    bpm_duration = {}
    start = min(0, first_note, first_timing)

    for i, each_time in enumerate(bpm_list):
        try:
            end = bpm_list[i+1]["offset"]
        except IndexError:
            end = last_note
        duration = end - start
        bpm_ack = each_time["bpm"]

        if bpm_now in bpm_duration:
            bpm_duration[bpm_ack] += duration
        else:
            bpm_duration[bpm_ack] = duration

    main_bpm = max(bpm_duration, key=bpm_duration.get)
    main_beatlength = round(60000/main_bpm, 12)
    main_one_measure_offset = main_beatlength*4

    print("main bpm", main_bpm)
    print("main beatlength:", main_beatlength)
    print("one measure offset", main_one_measure_offset)
    # to_delete = 0
    # for i,timing in enumerate(beatmap["timingPoints"]):
    # 	if timing["offset"] > last_note:
    # 			to_delete += 1
    # if(to_delete > 0):
    # 	del beatmap["timingPoints"][to_delete:]

    for i, timing in enumerate(beatmap["timingPoints"]):
        if "bpm" in timing:
            bpm_now = timing["bpm"]

        if "velocity" in timing:
            timing["bpm"] = bpm_now * timing["velocity"]

        if (i < len(beatmap["timingPoints"]) - 1):
            if (beatmap["timingPoints"][i+1]["offset"] == timing["offset"]):
                beatmap["timingPoints"][i+1]["bpm"] = bpm_now * \
                    beatmap["timingPoints"][i+1]["velocity"]
                del beatmap["timingPoints"][i]

    real_offset_index = 0
    indices_to_delete = []
    for i, timing in enumerate(beatmap["timingPoints"]):
        if (timing["offset"] <= first_note):
            real_offset_index = i
        if timing["offset"] > last_note:
            indices_to_delete.append(i)
    indices_to_keep = [i for i in range(
        len(beatmap["timingPoints"])) if i not in indices_to_delete]
    beatmap["timingPoints"] = [beatmap["timingPoints"][i]
                               for i in indices_to_keep]
    beatmap["timingPoints"].append({'offset': last_note+2000, 'beatLength': main_beatlength, 'velocity': 1, 'timingSignature': 4,
                                    'sampleSetId': 2, 'customSampleIndex': 0, 'sampleVolume': 0, 'timingChange': '1', 'kiaiTimeActive': '0', 'bpm': main_bpm})

    if real_offset_index > 0:
        del beatmap["timingPoints"][:real_offset_index]

    first_timing = beatmap["timingPoints"][0]["offset"]
    print("first timing adjusted", first_timing)
    append_offset = (main_one_measure_offset*2) - first_timing

    while (first_note + append_offset <= 2000):
        append_offset = append_offset + main_one_measure_offset
    # while( append_offset + first_timing <= first_note-append_offset):
    # 	append_offset = append_offset + main_one_measure_offset

    append_offset = int(append_offset)
    print("append offset", append_offset)
    print("new offset", first_timing + append_offset)

    for i, timing in enumerate(beatmap["timingPoints"]):
        timing["offset"] = timing["offset"] + append_offset
        beatmap["timingPoints"][i] = timing
    beatmap["timingPoints"].insert(0, {'offset': 0, 'beatLength': main_beatlength, 'velocity': 1, 'timingSignature': 4,
                                       'sampleSetId': 2, 'customSampleIndex': 0, 'sampleVolume': 0, 'timingChange': '1', 'kiaiTimeActive': '0', 'bpm': main_bpm})

    for i, timing in enumerate(beatmap["hitObjects"]):
        timing["offset"] = timing["offset"] + append_offset
        if timing["objectType"] == '128':
            timing["offsetLongNote"] = timing["offsetLongNote"] + append_offset
            if timing["offset"] == timing["offsetLongNote"]:
                timing["objectType"] = 1
                timing["offsetLongNote"] = 0

        beatmap["hitObjects"][i] = timing

    music_file = general_lines["AudioFilename"]
    general_lines["AudioFilename"] = music_file[:-3] + "ogg"
    general_lines["AudioLeadIn"] = 0

    if "EpilepsyWarning" in general_lines:
        general_lines.pop("EpilepsyWarning")

    found_image = write_osu(parent, osu, music_file, append_offset, inprogress_osu_folder, general_lines,
                            editor_lines, metadata_lines, difficulty_lines, event_lines, beatmap, input_offset)

    cwd = os.getcwd()
    hx_osu_path = os.path.join(cwd, inprogress_osu_folder, "HX.osu")
    hx_bms_path = os.path.join(cwd, inprogress_osu_folder, "HX.bms")

    print("Converting to BMS")
    subprocess.run('osu2bms '+hx_osu_path+' '+hx_bms_path+' --key-map-o2mania',
                   shell=True, cwd="lib")

    print("Converting to OJN")
    subprocess.run('enojn2 '+input_id+' '+hx_bms_path, shell=True, cwd="lib")
    shutil.move("lib/o2ma"+input_id+".ojn", "Output/o2ma"+input_id+".ojn")
    shutil.move("lib/o2ma"+input_id+".ojm", "Output/o2ma"+input_id+".ojm")

    print("Apply Metadata, Cover and BMP")
    ojn_struct = '< i 4s f i f 4h 3i 3i 3i 3i h h 20s i i 64s 32s 32s 32s i 3i 3i i'
    with open(os.path.join("Output", 'o2ma'+input_id+'.ojn'), 'r+b') as f:
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
    print("Done :", osu)


def main():
    print("Osu to O2jam Converter")
    input_folder = "Input"
    inprogress_folder = "Inprogress"
    output_folder = "Output"

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    if os.path.exists(inprogress_folder):
        shutil.rmtree(inprogress_folder)
    os.mkdir(inprogress_folder)

    # file_handler = logging.FileHandler(filename='tmp.txt')
    # stdout_handler = logging.StreamHandler(stream=sys.stdout)
    # handlers = [file_handler, stdout_handler]

    # logging.basicConfig(
    #    level=logging.DEBUG,
    #    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    #    handlers=handlers
    # )

    # logger = logging.getLogger('LOGGER_NAME')
    #
    # logger.debug('The debug message is displaying')
    # logger.info('The info message is displaying')
    # logger.warning('The warning message is displaying')
    # logger.error('The error message is displaying')
    # logger.critical('The critical message is displaying')

    osu_files = glob.glob(os.path.join(
        input_folder, "**/*.osu"), recursive=True)
    osu_count = len(osu_files)

    # input_id = "1000"
    # input_level = 1
    # use_title = True
    # input_multiply_bpm = 1

    print(".osu count :", osu_count)
    if (osu_count > 1):
        print("Multiple .osu file detected")
        use_title = yes_or_no(
            "Would you like to use Title (Y) / Difficulty (N) as a Song name in o2jam?")
    else:
        use_title = True
    input_id = int(input("Enter the ID Default (1000) : ") or "1000")
    input_level_raw = int(input("Enter the Level Default (1): ") or "1")
    input_level = int(input_level_raw)
    input_multiply_bpm = float(
        input("Multiply BPM (Ex. 0.5 ,0.75) Default (1) : ") or "1")
    input_offset = int(input(
        "Enter the Offset (Music Come Faster by X millisecs) Default (0) : ") or "0")
    # input_multiply_bpm = 1/input_multiply_bpm

    if not osu_files:
        print("Please put Osu Beatmap in 'Input' Folder")
        input("Press Enter to exit...")
        os._exit()

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for index, osu in enumerate(osu_files):
            parent = os.path.dirname(osu)
            parent_name = os.path.basename(parent)
            files = os.listdir(parent)

            inprogress_osu_folder = os.path.join(
                inprogress_folder, f'{index}_{parent_name.replace(" ", "_")}')
            os.mkdir(inprogress_osu_folder)
            for file in files:

                source_path = os.path.join(parent, file)

                if not imghdr.what(source_path) and not file.endswith('.osu'):
                    shutil.copy(source_path, inprogress_osu_folder)

            result = executor.submit(convert_to_o2jam,index, input_id, input_level,
                                                      input_multiply_bpm, use_title, osu, parent, inprogress_osu_folder, input_offset)
            print(result)
    # shutil.rmtree(inprogress_folder)


if __name__ == '__main__':
    freeze_support()
    main()
    print("ALL DONE!")
