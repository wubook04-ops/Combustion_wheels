import pandas as pd
from pathlib import Path
from chemkin_mechanism import ChemkinStandardizer, Species, ReactionThermoKinetics
from read_file_extend import ReadFileExtend


class MechanismPreprocessing:
    def __init__(self, t, pressure, mechanism_file_path, therm_file_path,):
        self.T = t
        self.P = pressure
        self.mechanism_file_path = mechanism_file_path
        self.therm_file_path = therm_file_path
        self.species = None
        self.reactions = None


    def main(self):
        a = ChemkinStandardizer(mech_file_path=self.mechanism_file_path, therm_file_path=self.therm_file_path)
        #a.convert_to_standard() #标准处理，按需选用
        a.load_mechanism()
        a.load_therm()
        self.species = a.species.copy()
        self.reactions = a.reactions.copy()

        for specie in self.species.values():
            b = Species(temp=self.T, temp_low=specie['T_l'], temp_high=specie['T_h']
                        , temp_mid=specie['T_m'], a_l=specie['a_L'], a_h=specie['a_H'])
            b.cal_s_h_cp()
            specie['T'] = self.T
            specie['S'] = b.S
            specie['H'] = b.H
            specie['Cp'] = b.Cp

        for i in range(len(self.reactions)):
            reaction = self.reactions[i]
            c = ReactionThermoKinetics(temp=self.T, reactions=reaction, species=self.species, third_type=reaction['rate_model'],
                                       a=reaction['arrhenius']['A'], n=reaction['arrhenius']['N'], e=reaction['arrhenius']['E'])
            c.cal_s_h()
            c.cal_k_p()
            c.cal_k_c()
            c.cal_k_f()
            c.cal_k_r()
            evaluation = {
                "temperature_K": self.T,
                "pressure_Pa": self.P,

                "delta_S_J_per_mol_K": c.delt_S,
                "delta_H_J_per_mol": c.delt_H,

                "Kp_dimensionless": c.kp,
                "Kc": c.kc,
                "Kc_unit": None,  # 根据 Δn 和浓度单位确定

                "kf": c.kf,
                "kf_unit": None,  # 速率级数及浓度单位确定后填写
                "kr": c.kr,
                "kr_unit": None,
            }
            reaction["evaluations"].append(evaluation)
        return self.species

class MechanismPostprocessing:
    def __init__(self, file_path, reactions):
        self.file_path = file_path
        self.reactions = reactions

    def load_net_rate_series(self):
        """Read an Excel workbook containing reaction rate data sheets.

        Sheet naming convention (Cantera / Chemkin post-processing output):
            "*soln_no*"  → net rate sheets (one per solution point / condition)
            "*rop_for_soln_no*" → rate-of-production sheets (currently collected only)

        For each net-rate sheet:
            - Column "Time_(sec)" is treated as the time axis.
            - Columns containing "Net" are parsed for reaction-specific net rates.
            - Reaction ID is extracted from the column name via the pattern 'n#DD'.
            - Rates are stored in self.reactions[reaction_id]["rate_net"] as a dict
              with keys: time_s (list), values (list), unit (str).
        """

        # Load the entire Excel workbook as a dict of DataFrames (one per sheet)
        if self.file_path is None:
            raise ValueError('Rate file has not been loaded: file_path is None')

        if isinstance(self.file_path, pd.DataFrame):
            # ReadFileExtend: when reading a CSV or a single Excel sheet, the return type is a DataFrame.
            rate_sheets = [self.file_path]
        elif isinstance(self.file_path, dict):
            # pd.read_excel(..., sheet_name=None) returns a dict mapping sheet names to DataFrames.
            rate_sheets = [
                df for sheet_name, df in self.file_path.items()
                if "soln_no" in sheet_name.lower()
                   and "rop_for_soln_no" not in sheet_name.lower()
            ]
        else:
            raise TypeError(
                f"Unsupported rate data type: {type(self.file_path).__name__}"
            )

        for df in rate_sheets:
            # Locate the time column by matching the substring "Time_(sec)"
            time_col = next((col for col in df.columns if "Time_(sec)" in str(col)),None,)

            if time_col is None:
                raise ValueError("Time column 'Time_(sec)' not found in worksheet")
            time_values = df[time_col].tolist()

            # Select columns that contain net-rate data
            net_cols = [col for col in df.columns if 'Net' in str(col)]
            for col in net_cols:
                import re
                match = re.search(r'n#(\d+)', str(col))
                if match is None:
                    continue

                # Convert to 0-based index (external IDs are 1-based)
                reaction_id = int(match.group(1)) - 1
                if not 0 <= reaction_id < len(self.reactions):
                    raise IndexError(f"Reaction index out of range: {reaction_id}")

                net_r_values = df[col].tolist()
                if len(time_values) != len(net_r_values):
                    raise ValueError(
                        f"Time/rate length mismatch for reaction {reaction_id}"
                    )

                # Append the parsed time-series net rate to the reaction dict
                rate_record = {
                    "time_s": time_values.copy(),
                    "values": net_r_values,
                    "unit": "mol/cm3/s",
                }
                self.reactions[reaction_id]["rate_net"].append(rate_record)
        print(f'Loading the reaction rate file: {self.file_path}')
        return self.reactions

class Process:
    def __init__(self, species, reactions,
                 process_file_path="./Mechanism_preprocessing/species.csv"):
        self.species = species
        self.reactions = reactions
        self.output_file_path_species = './' + str(process_file_path) + '/species.csv'
        self.output_file_path_reactions = './' + str(process_file_path) + '/reactions.csv'

    def save_csv(self):
        reactions_df = pd.DataFrame(self.reactions)
        species_df = pd.DataFrame(self.species)
        reactions_df.index.name = "reaction_index"
        species_df.index.name = "species_name"

        output_path_reactions = Path(self.output_file_path_reactions)
        output_path_species = Path(self.output_file_path_species)
        output_path_reactions.parent.mkdir(parents=True, exist_ok=True)
        output_path_species.parent.mkdir(parents=True, exist_ok=True)

        reactions_df.to_csv(output_path_reactions, encoding="utf-8-sig")
        species_df.to_csv(output_path_species, encoding="utf-8-sig")

class MechanismWorkflow:
    def __init__(self, mechanism_file_path, therm_file_path, chemkin_output_file_path,output_file_path='mechanism_preprocessing'):
        self.mechanism_file_path = mechanism_file_path
        self.therm_file_path = therm_file_path
        self.chemkin_output_file_path = chemkin_output_file_path
        self.output_file_path = output_file_path

    def main(self):
        temp_input = input('Please enter the temperature in Kelvin (default 1200): ')
        temp = float(temp_input) if temp_input.strip() else 1200.0
        pressure_input = input('Please enter the pressure in Pa (default 101325): ')
        pressure = float(pressure_input) if pressure_input.strip() else 101325.0

        a = MechanismPreprocessing(t=temp, pressure=pressure, mechanism_file_path=self.mechanism_file_path
                                   , therm_file_path=self.therm_file_path)
        a.main()
        b = ReadFileExtend(file_path=self.chemkin_output_file_path)
        b.load_and_process_file()
        b = MechanismPostprocessing(file_path=b.data, reactions=a.reactions)
        b.load_net_rate_series()
        Process(species=a.species, reactions=b.reactions, process_file_path=self.output_file_path).save_csv()
        return a.species, b.reactions


if __name__ == "__main__":
    Mechanism_file_path = "DataFile/grimech30.dat"
    Therm_file_path = "DataFile/thermo30.dat"
    Chemkin_output_file = ['DataFile/CKSoln_solution_no_1_1.csv','DataFile/CKSoln_solution_no_1_2.csv','DataFile/CKSoln_solution_no_1_3.csv',
                           'DataFile/CKSoln_solution_no_1_4.csv','DataFile/CKSoln_solution_no_1_5.csv','DataFile/CKSoln_solution_no_1_6.csv']
    Output_file_path = "mechanism_preprocessing"

    MechanismWorkflow(mechanism_file_path=Mechanism_file_path, therm_file_path=Therm_file_path,
                      chemkin_output_file_path=Chemkin_output_file, output_file_path=Output_file_path).main()
