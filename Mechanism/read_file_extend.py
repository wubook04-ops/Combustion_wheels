import pandas as pd

class ReadFileExtend:
    def __init__(self,file_path):
        self.file_path = file_path
        self.extend = None
        self.df = None
        self.data = None

    def load_and_process_file(self):
        # 判断 file_path 是否为列表
        if isinstance(self.file_path, list):
            return self._load_multiple_files()
        else:
            return self._load_single_file()

    def _load_single_file(self):
        """读取单个文件（原逻辑）"""
        self.extend = self.file_path.split('.')[-1].lower()
        try:
            #Choose the reading method based on the file extension.
            if self.extend == 'csv':
                print(f'Reading CSV format file: {self.file_path}')
                encodings = ['utf-8', 'gbk']
                for encoding in encodings:
                    try:
                        self.data = pd.read_csv(self.file_path, encoding=encoding)
                        print(f'Successfully read the file. Encoding: {encoding}')
                        break
                    except UnicodeDecodeError:
                        continue
                if self.data is None:
                    print('Unable to decode the file. Please check the file encoding.')
                    return False
            elif self.extend == 'xlsx':
                print(f'Reading XLSX format file: {self.file_path}')
                try:
                    self.data = pd.read_excel(self.file_path, engine="openpyxl")
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
            return True
        except FileNotFoundError:
            print(f'File not found: {self.file_path}')
            return False
        except Exception as e:
            print(f'Error reading file: {e}')
            return False

    def _load_multiple_files(self):
        """批量读取多个文件并纵向拼接"""
        dfs = []
        for fp in self.file_path:
            # 复用单文件读取逻辑，但不覆盖 self.data
            single_reader = ReadFileExtend(fp)
            success = single_reader._load_single_file()
            if not success:
                print(f'Skipping failed file: {fp}')
                continue
            dfs.append(single_reader.data)

        if not dfs:
            print('No valid files were read.')
            return False

            # 纵向拼接（假设所有文件列结构一致）
        self.data = pd.concat(dfs, ignore_index=True)
        print(f'\nMerged data shape: {self.data.shape}')
        print(f'Total files merged: {len(dfs)}')
        print(f'Columns: {list(self.data.columns)}')
        print('\nFirst 5 rows of merged data:')
        print(self.data.head())
        return True