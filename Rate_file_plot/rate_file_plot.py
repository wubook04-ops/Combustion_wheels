import matplotlib.pyplot as plt
import pandas as pd
from find_column import FindColumn

class RateFilePlot:
    def __init__(self, filepath, column_names):
        self.filename = filepath
        self.ext = None
        self.data = None
        self.column_name = column_names
        self.X = []
        self.Y = []
        self.x_label = None
        self.y_label = None
        self.x_column = None
        self.y_column = None

    def identify_the_file_extension(self):
        self.ext = self.filename.split('.')[-1].lower()
        if self.ext == 'csv':
            self.csv_format_file()
        elif self.ext == 'xlsx':
            self.xlsx_format_file()
        else:
            print('Please input the rate file in CSV/XLSX format: ')
            return False
        self.plot_x_y()
        return True

    def csv_format_file(self):
        try:
            print(f'Reading CSV format file: {self.filename}')
            #Read the CSV file, trying multiple encodings.
            encodings = ['utf-8', 'gbk', ]
            for encoding in encodings:
                try:
                    self.data = pd.read_csv(self.filename, encoding = encoding)
                    print(f'Successfully read the file. Encoding: {encoding}')
                    break
                except UnicodeDecodeError:
                    continue

            if self.data is None:
                print('Unable to decode the file. Please check the file encoding.')
                return False

            #Display basic information about the data.
            print(f'\nData shape: {self.data.shape}')
            print(f'Column names: {list(self.data.columns)}')
            print('\nFirst 5 rows preview: ')
            print(self.data.head())
            #Extract the needing columns.
            find_columns = FindColumn(column__names=self.column_name, data=self.data)
            column_names = find_columns.find_columns()
            self.x_column = column_names[0]
            self.y_column = column_names[1]
            self.X = self.data[self.x_column]
            self.Y = self.data[self.y_column]
            return True

        except FileNotFoundError:
            print(f'File not found: {self.filename}')
            return False
        except pd.errors.EmptyDataError:
            print('File is empty.')
            return False
        except Exception as e:
            print(f'Error reading CSV file: {e}')
            return False

    def xlsx_format_file(self):
        try:
            print(f'Reading XLSX format file: {self.filename}')
            # Read the Excel file
            try:
                self.data = pd.read_excel(self.filename)
                print('Successfully read the file.')
            except Exception as e:
                print(f'Error reading Excel file: {e}')
                return False

            print(f'\nData shape: {self.data.shape}') # type: ignore
            print(f'Column names: {list(self.data.columns)}') # type: ignore
            print('\nFirst 5 rows preview:')
            print(self.data.head()) # type: ignore
            # Extract the needed columns.
            find_columns = FindColumn(column__names=self.column_name, data=self.data)
            column_names = find_columns.find_columns()
            self.x_column = column_names[0]
            self.y_column = column_names[1]
            self.X = self.data[self.x_column]
            self.Y = self.data[self.y_column]
            return True

        except FileNotFoundError:
            print(f'File not found: {self.filename}')
            return False
        except Exception as e:
            print(f'Error reading XLSX file: {e}')
            return False

    def load_and_process_file(self):
        self.ext = self.filename.split('.')[-1].lower()
        try:
            #Choose the reading method based on the file extension.
            if self.ext == 'csv':
                print(f'Reading CSV format file: {self.filename}')
                encodings = ['utf-8', 'gbk']
                for encoding in encodings:
                    try:
                        self.data = pd.read_csv(self.filename, encoding=encoding)
                        print(f'Successfully read the file. Encoding: {encoding}')
                        break
                    except UnicodeDecodeError:
                        continue
                if self.data is None:
                    print('Unable to decode the file. Please check the file encoding.')
                    return False
            elif self.ext == 'xlsx':
                print(f'Reading XLSX format file: {self.filename}')
                try:
                    self.data = pd.read_excel(self.filename)
                    print('Successfully read the file.')
                except Exception as e:
                    print(f'Error reading Excel file: {e}')
                    return False

            else:
                print('Please input the rate file in CSV/XLSX format.')
                return False

            #Check if the data is empty.
            if self.data is None or self.data.empty: # type: ignore
                print('The file is empty or could not be read.')
                return False
            # Display basic information about the data.
            print(f'\nData shape: {self.data.shape}') # type: ignore
            print(f'Column names: {list(self.data.columns)}') # type: ignore
            print('\nFirst 5 rows preview: ')
            print(self.data.head()) # type: ignore

            #Extract the required columns.
            find_columns = FindColumn(column__names=self.column_name, data=self.data)
            column_names = find_columns.find_columns()
            #Store the column names and data.
            self.x_column = column_names[0]
            self.y_column = column_names[1]
            self.X = self.data[self.x_column]
            self.Y = self.data[self.y_column]
            self.plot_x_y()
            return True
        except FileNotFoundError:
            print(f'File not found: {self.filename}')
            return False
        except Exception as e:
            print(f'Error reading file: {e}')
            return False


    def plot_x_y(self):
        plt.figure()
        plt.plot(self.X, self.Y)
        plt.xlabel(self.x_column, fontdict={'fontsize':20, })
        plt.ylabel(self.y_column, fontdict={'fontsize':20, })
        plt.title(f'{self.x_column} vs {self.y_column}', fontsize=24)
        plt.show()