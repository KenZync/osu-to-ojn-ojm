def increaseMeasureByOne(file):
    # Open the file in read mode
    with open(file, 'r', encoding="utf-8") as f:
        # Read the file contents
        content = f.read()

    # Split the file contents by line
    lines = content.split('\n')

    # Find the line index where MAINDATA FIELD starts
    maindata_start = lines.index('*********[MAINDATA FIELD]*********') + 1
    # Loop through the MAINDATA FIELD lines and increment the values
    for i in range(maindata_start, len(lines)):
        line = lines[i]
        if line.startswith('#'):
            # Get the current number value
            num = int(line[1:4])
            if num == 999:
                raise ValueError("Cannot increase number 999.")
            # Increment the number value and update the line
            new_num = str(num + 1).zfill(3)
            lines[i] = line.replace(line[1:4], new_num, 1)

    # Join the updated lines and write them back to the file
    content = '\n'.join(lines)
    with open(file, 'w', encoding="utf-8") as f:
        f.write(content)