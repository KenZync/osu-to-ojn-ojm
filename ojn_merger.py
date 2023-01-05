import glob
import os
import shutil

from ojn_writer import change_id, check_md5


def merge_ojn(input_ojn_files, output_folder):
    i = 0
    for ojn in input_ojn_files:
        filename = os.path.basename(ojn)
        while os.path.exists(os.path.join(output_folder, filename)):
            i += 1
            filename = "o2ma" + str(i) + ".ojn"

        new_ojn_file_name = shutil.copy2(
            ojn, os.path.join(output_folder, filename))
        new_id = new_ojn_file_name.split('o2ma')[1].split('.')[0]
        change_id(new_ojn_file_name, new_id)
        ojm = ojn[:-1] + 'm'
        new_ojm_file_name = "o2ma" + new_id + ".ojm"
        shutil.copy2(ojm, os.path.join(output_folder, new_ojm_file_name))

    result_output_ojn_files = glob.glob(os.path.join(
        output_folder, "*.ojn"), recursive=True)
    md5_list = []
    print("Checking OJN/OJM Duplication")
    for result_ojn in result_output_ojn_files:
        md5 = check_md5(result_ojn)
        if md5 in md5_list:
            os.remove(result_ojn)
            result_ojm = result_ojn[:-1] + 'm'
            os.remove(result_ojm)
        else:
            md5_list.append(md5)
