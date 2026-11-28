import numpy as np

class DRG:
    def __init__(self, species, reactions, drg_data_file_path=None, edge_weight=None):
        self.species = species
        self.reactions = reactions
        self.drg_data_file_path = drg_data_file_path
        self.edge_weight = edge_weight

    def cal_drg_matrix(self):
        size = len(self.species)
        matrix = np.zeros((size, size), dtype=int)

        species_copy = self.species.copy()
        for species_name in self.species:
            species_copy[species_name]['flux_sum'] = 0

        id = 0
        for species_name in self.species:
            if species_copy[species_name]['flux_sum'] != 0:
                for j in range(len(self.species)):
                    if matrix[i][j] != 0:
                        id += 1
                        matrix[i][j] = matrix[i][j] / (species_copy[i].flux_sum + species_copy[j].flux_sum - matrix[i][j])
                        self.edge_weight.append((i, j, matrix[i][j]))


if __name__ == "__main__":
    from mechanism_workflow import MechanismWorkflow

    Mechanism_file_path = "DataFile/grimech30.dat"
    Therm_file_path = "DataFile/thermo30.dat"
    Chemkin_output_file = ['DataFile/CKSoln_solution_no_1_1.csv','DataFile/CKSoln_solution_no_1_2.csv','DataFile/CKSoln_solution_no_1_3.csv',
                           'DataFile/CKSoln_solution_no_1_4.csv','DataFile/CKSoln_solution_no_1_5.csv','DataFile/CKSoln_solution_no_1_6.csv']
    Output_file_path = "mechanism_preprocessing"
    main = MechanismWorkflow(mechanism_file_path=Mechanism_file_path, therm_file_path=Therm_file_path,
                      chemkin_output_file_path=Chemkin_output_file, output_file_path=Output_file_path).main()
    DRG(species=main[0],reactions=main[1]).cal_drg_matrix()