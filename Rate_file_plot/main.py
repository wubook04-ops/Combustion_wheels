import os
from rate_file_plot import RateFilePlot
max_attempts = 3
attempt_count = 0
while attempt_count < max_attempts:
    file_path = input('Please input the path of rate file:')
    column__name = input('Please input the column name(s) to plot (e.g., TIME, TEMP, PRESSURE): ')
    # Strip leading and trailing whitespace
    file_path = file_path.strip()
    if not os.path.exists(file_path):
        print('File does not exist!')
        attempt_count += 1
        continue

    start = RateFilePlot(filepath=file_path, column_names=column__name)
#   success = start.identify_the_file_extension()
    success = start.load_and_process_file()

    if success:
        print('File format is correct, starting processing...')
        break
    else:
        attempt_count += 1
        remaining = max_attempts - attempt_count
        if remaining > 0:
            print(f'You have {remaining} attempt(s) remaining.\n')
        else:
            print('Maximum number of attempts reached. Exiting program.')