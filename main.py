import concurrent.futures
import glob
import imghdr
import os
import shutil
from multiprocessing import freeze_support

from config import read_config
from ojn_merger import merge_ojn
from osu2ojnojm import convert_to_o2jam
from utils import yes_or_no


def main():
    print("Osu to O2jam Converter")

    config = read_config()
    config_input = config['Path']['input']
    config_inprogress = config['Path']['inprogress']
    config_output = config['Path']['output']

    config_o2maID = int(config['Default']['o2maID'])
    config_level = int(config['Default']['level'])
    config_multiplybpm = float(config['Default']['multiplybpm'])
    config_offset = int(config['Default']['offset'])
    config_usetitle = config.getboolean('Default', 'usetitle')
    config_lnMode = config['Default']['lnMode']
    config_lengthGap = config['Default']['lengthGap']

    config_auto_ID = config.getboolean('Automation', 'autoID')
    config_auto_remove_input = config.getboolean(
        'Automation', 'autoremoveinput')
    config_auto_remove_inprogress = config.getboolean(
        'Automation', 'autoremoveinprogress')

    input_folder = config_input
    inprogress_folder = config_inprogress
    output_folder = config_output

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
    print(".osu count :", osu_count)

    input_ojn_files = glob.glob(os.path.join(
        input_folder, "**/o2ma*.ojn"), recursive=True)
    input_ojn_count = len(input_ojn_files)

    output_ojn_files = glob.glob(os.path.join(
        output_folder, "o2ma*.ojn"), recursive=True)
    output_ojn_count = len(output_ojn_files)

    if not osu_files:
        print("Osu Beatmap Not Found in 'Input' Folder")
    if input_ojn_files and not osu_files:
        print("Changing to OJN Merger Mode")
        print("Input Folder Music Count : ", input_ojn_count)
        print("Output Folder Music Count : ", output_ojn_count)
        merge_ojn(input_ojn_files, output_folder)

    # Use glob to get a list of all the o2ma*.ojn files in the current directory
    ojn_files = glob.glob(os.path.join(output_folder, 'o2ma*.ojn'))

    # Extract the IDs from the file names and store them in a list
    ids = set([int(file.split('o2ma')[1].split('.')[0]) for file in ojn_files])

    # Initialize a list to store the generated IDs
    generated_ids = []

    # Use a loop to generate the desired number of IDs
    for i in range(osu_count):
        # Increment the current ID until it does not overlap with any of the IDs in the o2ma*.ojn files
        current_id = config_o2maID
        while current_id in ids:
            current_id += 1
        # Add the current ID to the list of generated IDs
        generated_ids.append(current_id)
        # Increment the starting ID for the next iteration
        config_o2maID = current_id + 1

    if config_auto_ID:
        use_title = config_usetitle
        input_level = config_level
        input_multiply_bpm = config_multiplybpm
        input_offset = config_offset
        ln_mode = int(config_lnMode)
        length_gap = int(config_lengthGap)
    else:
        if (osu_count > 1):
            print("Multiple .osu file detected")
            use_title = yes_or_no(
                "Would you like to use Title (Y) / Difficulty (N) as a Song name in o2jam?")
        else:
            use_title = True
        input_id = int(
            input(f"Enter the ID Default ({config_o2maID}) : ") or config_o2maID)
        input_level = int(
            input(f"Enter the Level Default ({config_level}): ") or config_level)
        input_multiply_bpm = float(
            input(f"Multiply BPM (Ex. 0.5 ,0.75) Default ({config_multiplybpm}) : ") or config_multiplybpm)
        input_offset = int(input(
            f"Enter the Offset (Music Come Faster by X millisecs) Default ({config_offset}) : ") or config_offset)
        ln_mode = int(input(f"Enter the LN Mode (0/1/2) (Normal/Short/Full) Default ({config_lnMode}) : ") or config_lnMode)
        if(ln_mode != 0):
            length_gap = int(input(f"Enter the LN Length/Gap (4/8/16) Default ({config_lengthGap}) : ") or config_lengthGap)
        else:
            length_gap = 0

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for index, osu in enumerate(osu_files):
            if config_auto_ID:
                input_id = generated_ids[index]
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

            result = executor.submit(convert_to_o2jam, index, input_id, input_level,
                                     input_multiply_bpm, use_title, osu, parent, inprogress_osu_folder, output_folder, input_offset, config_auto_ID, ln_mode, length_gap)

    if config_auto_remove_inprogress:
        print("Deleting Folder : ", inprogress_folder)
        shutil.rmtree(inprogress_folder)

    if config_auto_remove_input:
        print("Deleting Folder : ", input_folder)
        shutil.rmtree(input_folder)
        os.makedirs(input_folder)


if __name__ == '__main__':
    freeze_support()
    main()
    print("ALL DONE!")
