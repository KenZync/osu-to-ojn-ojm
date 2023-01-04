# from math import isclose
from PIL import Image
# Check is a file an image


def is_image(filename):
    try:
        img = Image.open(filename)
        img.verify()
        return True
    except (IOError, SyntaxError) as e:
        return False

# # Float, String compatibility
# def remove_trailing_zeros(number):
#     float_number = float(number)
#     if isclose(float_number, int(float_number), rel_tol=1e-9):
#         return int(float_number)
#     else:
#         return "{:f}".format(float_number)


def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[0] == 'y':
            return True
        if reply[0] == 'n':
            return False
            
def calc_measures(bpm_list, last_offset):
  # Initialize measure count to 0
  measure_count = 0
  
  # Iterate through the list of BPM changes
  for i in range(len(bpm_list)):
    # print(bpm_list[i]['offset'],bpm_list[i]['bpm'])
    # Get the current BPM and offset
    offset = bpm_list[i]['offset']
    bpm = bpm_list[i]['bpm']
    
    # Calculate the length of one measure at this BPM
    measure_length = (60000 / bpm)*4  # multiply by 1000 to convert from seconds to milliseconds
    
    # If this is the first BPM change, use the offset as the time elapsed
    if i == 0:
      time_elapsed = 0
    # Otherwise, use the difference between the current and previous offsets as the time elapsed
    else:
      time_elapsed = offset - bpm_list[i-1]['offset']
  
    measure_count += time_elapsed / measure_length

  # Return the total number of measures
  time_elapsed =  last_offset - offset
  measure_count += time_elapsed / measure_length
  return measure_count