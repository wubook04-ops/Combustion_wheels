class FindColumn:
    def __init__(self, column__names, data, temp_column=None, time_column=None):
        self.temp_column = temp_column
        self.time_column = time_column
        self.data = data
        self.column_names = column__names
        self.keywords= {'time': ['time_s', 'Time_(sec)', 'time', 'Time', '时间', 't',
                         'second'],
                    'temp': ['Temperature_(K)', 'T', 'temp', '温度'],
                    'volume': ['Volume_(cm3)', ' Volume_(dm3)', ' Volume_(m3)',],
                    'pressure': ['Pressure_(atm)', 'Pressure_(pa)','Pressure_(kpa)'],}

    def preprocess_column_name(self):
        self.column_names = [name.strip().lower() for name in self.column_names.replace(' ', '').split(',')]
        if len(self.column_names) != 2:
            self.column_names = input(f'Please enter two variables (e.g., T, TEMP) for plotting: ')

    def find_time_column(self):
        print('Searching for time column...')
        time_keywords = ['time_s', 'Time_(sec)', 'time', 'Time', '时间', 'TIME', 'timestamp', 'Timestamp', 't',
                         'second']
        found_columns = []
        for col in self.data.columns:
            col_str = str(col).strip()
            if col_str in time_keywords:
                found_columns.append(col)
        if len(found_columns) == 1:
            self.time_column = found_columns[0]
            print(f'Automatically identify the time column: {self.time_column.lower()}')
        elif len(found_columns) > 1:
            print(f'Found multiple potential time columns: {found_columns}')
            choice_time_columns = input('Please select the time column (enter column name): ')
            while choice_time_columns not in found_columns:
                choice_time_columns = input(f'Invalid selection. Please choose from {found_columns}: ')
            self.time_column = choice_time_columns
        else:
            print('No time column auto-detected. Please specify manually.')
            print(f'Available columns: {list(self.data.columns)}')
            self.time_column = input('Please input the name of time column: ')
            while self.time_column not in self.data.columns:
                self.time_column = input(f'Column {self.time_column} does not exist. Please re-enter: ')
        print(f'Time columns confirmed as: {self.time_column}')

    def find_columns(self):
        self.preprocess_column_name()
        column_names = []
        for i in self.column_names:
            print(f'Searching for {i} column...')
            found_column = []
            dynamic_value = i + '_column'
            #Dynamically create an attribute on the instance, using a name derived from loop variable i.
            setattr(self,dynamic_value,None)
            for col in self.data.columns:
                col_str = str(col).strip()
                if col_str in self.keywords[i]:
                    found_column.append(col)
            if len(found_column) == 1:
                print(f'Automatically identify the {i.upper()} column: {found_column}')
                setattr(self,dynamic_value,found_column[0])
            elif len(found_column) > 1:
                print(f'Found multiple potential {i.upper()} columns: {found_column}')
                choice_column = input(f'Please select the {i} column (enter column name): ')
                while choice_column not in found_column:
                    choice_column = input(f'Invalid selection. Please choose from {found_column}: ')
                setattr(self,dynamic_value,choice_column)
            else:
                print(f'No {i} column auto-detected. Please specify manually.')
                print(f'Available columns: {list(self.data.columns)}')
                manual_input = input(f'Please input the name of {i} column: ')
                manual_input = manual_input.strip().lower()
                while manual_input not in self.data.columns:
                    manual_input = input(f'Column {manual_input} does not exist. Please re-enter: ')
                setattr(self, dynamic_value, manual_input)
            print(f'{i.title()} column confirmed as: {getattr(self, dynamic_value)}')
            column_names.append(getattr(self, dynamic_value))
        return column_names