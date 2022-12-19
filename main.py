import os
import subprocess
from pydub import AudioSegment
import shutil
for filename in os.listdir(os.getcwd()):
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
        if(audio_is_mp3):
            target_file = music_file.replace(".mp3",".ogg")
            AudioSegment.from_mp3(music_file).export(target_file, format='ogg')
        shutil.move("HX.osu", "lib/HX.osu")
        subprocess.run('osu2bms HX.osu HX.bms --key-map-o2mania',shell=True, cwd="lib")
        subprocess.run('enojn2 1000 HX.bms',shell=True, cwd="lib")