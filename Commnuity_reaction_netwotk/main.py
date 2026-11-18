from generate_markov_chain_transition_matrix_q import GenerateQ
from read_file_extend import ReadFileExtend
from convert_matrix_q_kt import ConvertMatrixQKT

file_path = r'data.xlsx'
dt = 0.000001
start_step = 75
end_step = 76

#提取需要的数据
Reader = ReadFileExtend(file_path)
Reader.load_and_process_file()
ori_data = Reader.data

#分为时间列和浓度列
times_col = ori_data.iloc[:, 0]
concentration_cols = ori_data.iloc[:, 1:]
n_species = concentration_cols.shape[1]

a = GenerateQ(n_species, dt, start_step, end_step, concentration_cols)
a.main()

b = ConvertMatrixQKT(start_step, end_step)
b.main()
