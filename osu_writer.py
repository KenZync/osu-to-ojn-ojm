import os
import shutil
from PIL import Image
from utils import is_image
from pydub import AudioSegment
import concurrent.futures


def write_osu(parent, osu, music_file, append_offset, inprogress_osu_folder, general_lines, editor_lines, metadata_lines, difficulty_lines, event_lines, beatmap, input_offset):
    with open(os.path.join(inprogress_osu_folder, "HX.osu"), 'w', encoding="utf-8") as hx_osu:
        hx_osu.write("osu file format v14\n\n")
        hx_osu.write("[General]\n")
        for key, value in general_lines.items():
            hx_osu.write(f'{key}: {value}\n')

        hx_osu.write("\n[Editor]\n")
        for key, value in editor_lines.items():
            hx_osu.write(f'{key}: {value}\n')

        hx_osu.write("\n[Metadata]\n")
        for key, value in metadata_lines.items():
            hx_osu.write(f'{key}:{value}\n')

        hx_osu.write("\n[Difficulty]\n")
        for key, value in difficulty_lines.items():
            hx_osu.write(f'{key}:{value}\n')

        print(music_file)
        print("Converting MP3 to OGG")
        music_file_path = os.path.join(inprogress_osu_folder, music_file)
        music_exist = os.path.exists(music_file_path)
        if not music_exist:
            raise Exception("Music Not Found, Stopping process")
        try:
            the_song = AudioSegment.from_mp3(
                os.path.join(music_file_path))
            target_file = music_file.replace(".mp3", ".ogg")
        except:
            the_song = AudioSegment.from_ogg(
                os.path.join(music_file_path))
            target_file = music_file

        append_offset = append_offset + input_offset
        if (append_offset >= 0):
            silent_segment = AudioSegment.silent(duration=append_offset)
            final_song = silent_segment + the_song
        else:
            final_song = the_song[abs(append_offset):]
        chunks = final_song[::300000]

        # Export all of the individual chunks as wav files
        chunks_name = []
        chunk_length = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i, chunk in enumerate(chunks):
                chunk_name = "osu2ojnojm_song_part_{0}.ogg".format(i)
                chunks_name.append(chunk_name)
                print("Exporting", len(chunk), "ms" , chunk_name)
                chunk_length.append(len(chunk))
                executor.submit(chunk.export,os.path.join(
                    inprogress_osu_folder, chunk_name), format="ogg")
        print(inprogress_osu_folder, chunks_name[0])
        print(inprogress_osu_folder, target_file)
        if os.path.exists(os.path.join(inprogress_osu_folder, target_file)):
            os.rename(os.path.join(inprogress_osu_folder, target_file), os.path.join(
                    inprogress_osu_folder, "_Backup"+target_file))
        else:
            os.rename(os.path.join(inprogress_osu_folder, chunks_name[0]), os.path.join(
                                inprogress_osu_folder, target_file))
        image_file = None

        hx_osu.write("\n[Events]\n")
        found_image = False
        for i, event in enumerate(event_lines):
            if "," in event:
                member = event.split(",")
                image = member[2].strip('\"')
                if is_image(os.path.join(os.path.dirname(osu), image)):
                    image_file = image
                    shutil.copy(os.path.join(parent, image_file),
                                inprogress_osu_folder)

                    image = Image.open(os.path.join(
                        inprogress_osu_folder, image_file))
                    image = image.convert("RGB")
                    image = image.resize((800, 600))
                    cover_file_path = os.path.join(
                        inprogress_osu_folder, '800x600.jpg')
                    image.save(cover_file_path, format='JPEG')
                    image = image.resize((80, 80))
                    bmp_file_path = os.path.join(
                        inprogress_osu_folder, '80x80.bmp')
                    image.save(bmp_file_path, format='BMP')
                    found_image = True
                if (member[0] == "Video"):
                    continue
                hx_osu.write(event + "\n")
            else:
                hx_osu.write(event + "\n")

        sound_offset = 0
        for i, name in enumerate(chunks_name):
            if i != 0:
                sound_offset = sound_offset + chunk_length[i-1] + 1
                hx_osu.write("Sample," +
                             str(sound_offset)+',0,"'+name+'",100\n')

        hx_osu.write("\n[TimingPoints]\n")

        for timing in beatmap["timingPoints"]:
            beat_length = round(60000/timing["bpm"], 12)
            hx_osu.write('{},{},{},{},{},{},{},{}\n'.format(timing["offset"], beat_length, timing["timingSignature"], timing["sampleSetId"],
                         timing["customSampleIndex"], timing["sampleVolume"], timing["timingChange"], timing["kiaiTimeActive"]))

        hx_osu.write("\n[HitObjects]\n")

        for object in beatmap["hitObjects"]:
            rest = ":".join(object["rest"])
            hx_osu.write('{},{},{},{},{},{}:{}\n'.format(
                object["x"], object["y"], object["offset"], object["objectType"], object["soundType"], object["offsetLongNote"], rest))
    return found_image
