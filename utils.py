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
