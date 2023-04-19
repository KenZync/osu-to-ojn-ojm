import math
import os
import re
import shutil
import subprocess
from bms_writer import increaseMeasureByOne

from ojn_writer import apply_metadata
from osu_writer import write_osu
from utils import calc_measures

from rosu_pp_py import Beatmap, Calculator

def convert_to_o2jam(index, input_id, input_level, input_multiply_bpm, use_title, osu, parent, inprogress_osu_folder, output_folder, input_offset, config_auto_ID):
    map = Beatmap(path = osu)
    calc = Calculator(mode = 3)
    max_perf = calc.performance(map)
    print("STARS:",max_perf.difficulty.stars)
    
    if config_auto_ID:
        input_id = str(input_id)
        input_level = int(round(max_perf.difficulty.stars*10))
    else:
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
        if i != 0:
            start = each_time["offset"]

        try:
            end = bpm_list[i+1]["offset"]
        except IndexError:
            end = last_note
            
        duration = end - start
        bpm_ack = each_time["bpm"]

        if bpm_ack in bpm_duration:
            bpm_duration[bpm_ack] += duration
        else:
            bpm_duration[bpm_ack] = duration

    main_bpm = max(bpm_duration, key=bpm_duration.get)
    main_beatlength = round(60000/main_bpm, 12)
    main_one_measure_offset = main_beatlength*4

    print("bpm duration", bpm_duration)
    print("main bpm", main_bpm)
    print("main beatlength:", main_beatlength)
    print("one measure offset", main_one_measure_offset)

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

    measure_count = calc_measures(beatmap["timingPoints"], last_note+2000 )
    print("Measure Count : ",measure_count)
    max_multiplier = 998/measure_count
    print("Multiplier to Maximize : ", max_multiplier)

    if(measure_count > 999):
        main_bpm = main_bpm * max_multiplier
        main_beatlength = round(60000/main_bpm, 12)
        main_one_measure_offset = main_beatlength*4
        for i, timing in enumerate(beatmap["timingPoints"]):
            timing["bpm"] = timing["bpm"] * max_multiplier
            beatmap["timingPoints"][i] = timing

    beatmap["timingPoints"].append({'offset': last_note+2000, 'beatLength': main_beatlength, 'velocity': 1, 'timingSignature': 4,
                                    'sampleSetId': 2, 'customSampleIndex': 0, 'sampleVolume': 0, 'timingChange': '1', 'kiaiTimeActive': '0', 'bpm': main_bpm})

    if real_offset_index > 0:
        del beatmap["timingPoints"][:real_offset_index]

    first_timing = beatmap["timingPoints"][0]["offset"]
    print("first timing adjusted", first_timing)
    append_offset = (main_one_measure_offset*1) - first_timing

    while (first_note + append_offset <= 1000):
        append_offset = append_offset + main_one_measure_offset

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

    if "StoryFireInFront" in general_lines:
        general_lines.pop("StoryFireInFront")

    found_image = write_osu(parent, osu, music_file, append_offset, inprogress_osu_folder, general_lines,
                            editor_lines, metadata_lines, difficulty_lines, event_lines, beatmap, input_offset)

    cwd = os.getcwd()
    hx_osu_path = os.path.join(cwd, inprogress_osu_folder, "HX.osu")
    hx_bms_path = os.path.join(cwd, inprogress_osu_folder, "HX.bms")

    print("Converting to BMS")
    subprocess.run('osu2bms '+hx_osu_path+' '+hx_bms_path+' --key-map-o2mania',
                   shell=True, cwd="lib", stdout=subprocess.DEVNULL)
    
    print("Increasing Measure By One")
    increaseMeasureByOne(hx_bms_path)

    print("Converting to OJN")
    subprocess.run('enojn2 '+input_id+' '+hx_bms_path,
                   shell=True, cwd="lib", stdout=subprocess.DEVNULL)
    shutil.move("lib/o2ma"+input_id+".ojn",
                os.path.join(output_folder, "o2ma"+input_id+".ojn"))
    shutil.move("lib/o2ma"+input_id+".ojm",
                os.path.join(output_folder, "o2ma"+input_id+".ojm"))

    print("Apply Metadata, Cover and BMP")
    apply_metadata(inprogress_osu_folder, output_folder, input_id, input_level, use_title, metadata_lines, found_image)

    print(f"Done ID {input_id}:", osu)
