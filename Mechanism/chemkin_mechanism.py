import math
from typing import Optional, Dict, Any

class Element:
    def __init__(self, species_name):  # 缺少对AR HE NE元素的处理
        self.species_name = species_name
        self.element_objects = []
        self.element_counts = []
        self.keep = False
        if self.species_name == "H":
            self.mass = 1.008
        elif self.species_name == "C":
            self.mass = 12.011
        elif self.species_name == "O":
            self.mass = 15.998
        elif self.species_name == "N":
            self.mass = 14.006
        elif self.species_name == "F":
            self.mass = 18.998
        elif self.species_name == "HE":
            self.mass = 4.003
        elif self.species_name == "NE":
            self.mass = 20.1797
        elif self.species_name == "AR":
            self.mass = 39.948

class Species:
    """NASA 7-coefficient thermodynamic species model.

    Stores two temperature-range polynomial coefficient sets (low: a_L, high: a_H)
    and evaluates Cp°, H°, S° at a given temperature T via NASA 7 polynomials.

    Attributes:
        T (float): Evaluation temperature in K.
        gas_constant (float): Universal gas constant, 8.314 J/(mol·K).
        T_l, T_m, T_h (float): Valid temperature range bounds (K); T_m splits low/high.
        a_L, a_H (list[float]): NASA 7 coefficients [a0–a4, a5(H-term), a6(S-term)].
        H, S, Cp (float | None): Last computed enthalpy (J/mol), entropy (J/(mol·K)),
                                 heat capacity (J/(mol·K)).
        H_list, S_list, Cp_list (list[float]): History of all computed values.

    Polynomial relations (R = gas_constant):
        Cp/R = a0 + a1·T + a2·T² + a3·T³ + a4·T⁴
        H/(R·T) = a0 + a1·T/2 + a2·T²/3 + a3·T³/4 + a4·T⁴/5 + a5/T
        S/R = a0·ln(T) + a1·T + a2·T²/2 + a3·T³/3 + a4·T⁴/4 + a6

    Call cal_s_h_cp() to evaluate at self.T; results are stored and appended to lists.

    Notes:
        - assert enforces ≥7 coefficients; stripped under python -O.
        - No ordering check for T_l < T_m < T_h.
        - No name/id attribute; extend for Reaction-layer integration.
    """

    def __init__(self, temp, temp_low, temp_mid, temp_high, a_l, a_h):
        self.T = temp
        self.gas_constant = 8.314
        self.T_l = temp_low
        self.T_m = temp_mid
        self.T_h = temp_high
        self.a_L = a_l
        self.a_H = a_h
        # NASA 7-coefficient polynomials require at least 7 coefficients per temperature range.
        assert len(self.a_L) >= 7, f"a_L must have at least 7 coefficients, got {len(self.a_L)}"
        assert len(self.a_H) >= 7, f"a_H must have at least 7 coefficients, got {len(self.a_H)}"
        self.H = None
        self.S = None
        self.Cp = None

    def cal_s_h_cp(self):
        """Calculate standard entropy S°(T), enthalpy H°(T), and heat capacity Cp°(T).
        Uses NASA 7-coefficient polynomials...
        """

        if self.T < self.T_l or self.T > self.T_h:
            raise ValueError(f"Temperature {self.T} K is outside valid range [{self.T_l}, {self.T_h}]")
        if self.T_l <= self.T < self.T_m:
            coefficient = self.a_L
        elif self.T_m <= self.T <= self.T_h:
            coefficient = self.a_H
        else:
            raise ValueError(f"Temperature {self.T} K not covered by any polynomial")

        # S/R = a0*ln(T) + a1*T + a2*T^2/2 + a3*T^3/3 + a4*T^4/4 + a6
        # H/(RT) = a0 + a1*T/2 + a2*T^2/3 + a3*T^3/4 + a4*T^4/5 + a5/T
        # Cp/R = a0 + a1*T + a2*T^2 + a3*T^3 + a4*T^4
        # where a0..a5 correspond to coefficient[0]..coefficient[5].
        self.S = self.gas_constant * (coefficient[0] * math.log(self.T) + coefficient[1] * self.T + (coefficient[2] *
                 self.T ** 2) / 2 + (coefficient[3] * self.T ** 3) / 3 + (coefficient[4] * self.T ** 4) / 4 + coefficient[6])
        self.H = self.gas_constant * self.T * (coefficient[0] + (coefficient[1] * self.T) / 2 + (coefficient[2] * self.T ** 2
                 ) / 3 + (coefficient[3] * self.T ** 3) / 4 + (coefficient[4] * self.T ** 4) / 5 + coefficient[5] / self.T)
        self.Cp = self.gas_constant * (coefficient[0] + coefficient[1] * self.T + coefficient[2] * self.T ** 2 +
                 coefficient[3] * self.T ** 3 + coefficient[4] * self.T ** 4)


class ChemkinReaction:
    """A complete model for one CHEMKIN reaction: parsing (main line + auxiliary lines),
    type tagging, stoichiometric data, kinetics (kf/kr), and thermodynamics
    (ΔS/ΔH/Kp/Kc) calculations.
    """

    def __init__(self, chemkin_reaction_line=None, chemkin_aux_line=None, temp=None, pressure=None):
        self.chemkin_reaction_line = chemkin_reaction_line
        self.chemkin_aux_line = chemkin_aux_line
        self.type = "elementary"
        self.T = temp
        self.P = pressure
        self.gas_constant = 8.314
        self.sri_d = 1.0   # SRI 省略 d 时的默认值
        self.sri_e = 0.0   # SRI 省略 e 时的默认值
        self.sri_a = None
        self.sri_b = None
        self.sri_c = None
        self.reaction_express = None
        self.A = None
        self.N = None
        self.E = None
        self.A_L = None
        self.N_L = None
        self.E_L = None
        self.A_H = None
        self.N_H = None
        self.E_H = None
        self.troe_a = None     # TROE 参数 a（alpha）
        self.troe_ttt = None   # T***
        self.troe_t = None     # T*
        self.troe_tt = None    # T**（CHEMKIN 允许省略，省略时为 None）
        self.react_part = None
        self.product_part = None
        self.reversible_sep_idx = None
        self.third_body_line = None
        self.kc = None
        self.kp = None
        self.kf = None
        self.kr = None
        self.react_sto = []
        self.reactant = []
        self.pro_sto = []
        self.product = []
        self.third_body_spe_list = []
        self.third_para = []
        self.kp_list = []
        self.kc_list = []
        self.kr_list = []

    def extract_row_params(self) -> tuple[
        float, float, float, str,
        list[int], list[str], list[int], list[str]
    ]:
        """Parse the reaction line.

        Uses self.chemkin_reaction_line passed to the constructor:
        one chemkin reaction record, format "<reaction expression> <A> <N> <E>",
        e.g. "H+O2<=>O+OH  1.915E+14  0.000  1.644E+04".
        """

        # A chemkin reaction line = reaction expression + 3 Arrhenius parameters, whitespace-separated.
        parts = self.chemkin_reaction_line.split()
        self.A = float(parts[1])   # 指前因子
        self.N = float(parts[2])   # 温度指数
        self.E = float(parts[3])   # 活化能
        # Start splitting the reaction expression.
        reaction_express = parts[0].strip()
        self.reaction_express = reaction_express
        # First remove the "(+M)" form (e.g. A+B(+M)<=>C(+M)): it contains "+",
        # so it must be stripped before the sides are split into tokens.
        # Note: this form does NOT set self.type (unchanged behavior).
        reaction_express = reaction_express.replace("(+M)", "")
        # The standalone third-body "M" (e.g. A+B+M<=>C+M) is deliberately NOT
        # removed here: it is detected by exact token match in the parsing loops
        # below, so M-prefixed species names (MCH, MXY, ...) are never corrupted.

        # Reversible-reaction handling.
        self.reversible_sep_idx = reaction_express.find("<=>")
        if self.reversible_sep_idx > 0:
            part = reaction_express.split("<=>")
            # Reactant side.
            s_left = part[0]
            # Product side.
            s_right = part[1]
            # Split both sides by "+" into species fragments (may carry a leading coefficient, e.g. "2H").
            self.react_part = s_left.split("+")  # type: ignore
            self.product_part = s_right.split("+")

            for part in self.react_part:
                # Standalone "M" token = third-body collider: mark and skip (not a species).
                # Exact match keeps M-prefixed species names (MCH, MXY, ...) intact.
                if part == "M":
                    self.type = "third_body"
                    continue
                # Check each fragment's first char for an explicit coefficient (rule below).
                # First char is a digit: '0' < c <= '9' recognizes 1~9;
                # multi-digit and decimal coefficients are unsupported (e.g. 0.5O2, 10H2O).
                if '0' < part[0] <= '9':
                    # Negative coefficient: reactant is consumed.
                    reactant_stoichiometric_coefficient = -int(part[0])
                    # Append to the reactant-side coefficients.
                    self.react_sto.append(reactant_stoichiometric_coefficient)
                    # Drop the leading coefficient; the rest is the species name.
                    self.reactant.append(part[1:])
                else:
                    # 无显式系数，默认为 1（记为 -1）
                    self.react_sto.append(-1)
                    self.reactant.append(part[0:])

            for part in self.product_part:
                if part == "M":
                    self.type = "third_body"
                    continue
                if '0' < part[0] <= '9':
                    reactant_stoichiometric_coefficient = int(part[0])
                    self.pro_sto.append(reactant_stoichiometric_coefficient)
                    self.product.append(part[1:])
                else:
                    self.pro_sto.append(1)
                    self.product.append(part[0:])

            # Handle species present on both sides (e.g. catalysts, spectator species):
            #   reactant-side net coefficient = product coefficient - |reactant coefficient|
            #   product-side coefficient set to 0
            # Warning: net production (>0) wrongly stays in react_sto; zeroed pro_sto[j]
            #          can be double-subtracted by a later match; break handles only the
            #          first duplicate, and species names are never removed (ghost coefficient-0 entries).
            for i in range(len(self.reactant)):
                re = self.reactant[i]
                for j in range(len(self.product)):
                    pr = self.product[j]
                    if re == pr:
                        self.react_sto[i] = self.pro_sto[j] - abs(self.react_sto[i])
                        self.pro_sto[j] = 0
                        break

        else:
            # "<=>" not found (find returned -1 or 0); handle as irreversible "=>".
            part = reaction_express.split("=>")
            s_left = part[0]
            s_right = part[1]

            self.react_part = s_left.split("+")  # type: ignore
            self.product_part = s_right.split("+")

            for part in self.react_part:
                if part == "M":
                    self.type = "third_body"
                    continue
                if '0' < part[0] <= '9':
                    reactant_stoichiometric_coefficient = -int(part[0])
                    self.react_sto.append(reactant_stoichiometric_coefficient)
                    self.reactant.append(part[1:])
                else:
                    self.react_sto.append(-1)
                    self.reactant.append(part[0:])

            for part in self.product_part:
                if part == "M":
                    self.type = "third_body"
                    continue
                if '0' < part[0] <= '9':
                    reactant_stoichiometric_coefficient = int(part[0])
                    self.pro_sto.append(reactant_stoichiometric_coefficient)
                    self.product.append(part[1:])
                else:
                    self.pro_sto.append(1)
                    self.product.append(part[0:])

            # Net cancellation of identical species (same as the reversible branch: net stays on the reactant side, product side zeroed).
            # Handle species present on both sides.
            for i in range(len(self.reactant)):
                re = self.reactant[i]
                for j in range(len(self.product)):
                    pr = self.product[j]
                    if re == pr:
                        self.react_sto[i] = self.pro_sto[j] - abs(self.react_sto[i])
                        self.pro_sto[j] = 0
                        break
        return self.A, self.N, self.E, self.type, self.react_sto, self.reactant, self.pro_sto, self.product

    def parse_chemkin_aux_line(self, species):
        """Identify and supplement the reaction type by parsing one CHEMKIN
        auxiliary line that follows the main reaction line.

        Prerequisites:
            1. The main reaction line must have already been parsed by
               extract_row_params().
            2. This method takes no extra arguments. Before calling, the current
               auxiliary line must be assigned to self.chemkin_aux_line.
               One call processes exactly one auxiliary line.
            All results are written back to instance attributes; no return value.

        Keyword dispatch:
            LOW/<A> <N> <E>/
                Fall-off reaction: supplies the low-pressure-limit Arrhenius
                parameters for k0 (the three parameters on the main line
                correspond to the high-pressure limit k∞).
            HIGH/<A> <N> <E>/
                Chemically activated reaction: the main line gives k0, this line
                supplies the high-pressure limit k∞.
            TROE/<a> <T***> <T*> <T**>/
                Troe-type pressure dependence: four center-broadening parameters
                given in this exact order; T** is optional (3 or 4 params valid).
            SRI/.../
                SRI-type pressure dependence (originally 3 params; CHEMKIN
                extension allows 5). This implementation only appends a type
                marker; numeric values are not parsed here.
            DUPLICATE
                Duplicate reaction marker; allows multiple rate expressions for
                the same reactant/product set.
            REV/<A> <N> <E>/
                Explicit reverse-rate Arrhenius parameters, overriding the
                reverse rate derived from equilibrium constants. This
                implementation only sets the type marker; the three values are
                not parsed.
            Other:
                Third-body efficiency line, e.g.
                "H2/2.4/ H2O/15.4/ CH4/2.0/".

        Output destinations:
            self.chemkin_aux_lines
                Accumulates raw text of each keyword auxiliary line.
            self.third_body_line
                Raw text of a single third-body efficiency line.
            self.third_body_spe_list / self.third_para
                Species objects / corresponding collision efficiency values from
                the efficiency line (index-aligned).
            self.type
                Reaction type: overwritten by LOW / HIGH; appended by TROE / SRI;
                directly overwritten by DUPLICATE / REV / third-body lines.
            self.A_L / N_L / E_L, self.A_H / N_H / E_H, self.troe_*
                Numeric values parsed in the respective branches.
        """

        # Split by "/" and strip each field: leading/trailing whitespace around
        # species names and efficiency values is cleaned in one pass.
        # The trailing "/" still produces an empty-string field, which the else
        # branch removes via pop().
        parts = [tok.strip() for tok in self.chemkin_aux_line.split("/")]

        if "LOW" in self.chemkin_aux_line or "HIGH" in self.chemkin_aux_line:
            # LOW: fall-off reaction — main line gives k∞, this line supplies the
            # low-pressure limit k0. HIGH: chemically activated reaction — main line
            # gives k0, this line supplies the high-pressure limit k∞.
            # Both lines share the same Arrhenius parameter format.
            params = parts[1].split()
            a_val, n_val, e_val = (float(v) for v in params[:3])

            if "LOW" in self.chemkin_aux_line:
                self.type = "fall_off"
                self.A_L, self.N_L, self.E_L = a_val, n_val, e_val
            else:  # HIGH
                self.type = "chem_activate"
                self.A_H, self.N_H, self.E_H = a_val, n_val, e_val

        elif self.chemkin_aux_line.find("TROE") >= 0:  # Troe pressure-dependent parameters
            # Example: "TROE/ .5620 91.00 5836.00 8552.00/"
            # CHEMKIN column order: a / T*** / T* / T**
            # Used in the center broadening factor:
            #   Fcent(T) = (1-a)·exp(-T/T***) + a·exp(-T/T*) + exp(-T**/T)
            # The fall-off broadening function F is then obtained via
            # log10 F = log10 Fcent / (1 + f1²).
            i_arr_params_str = parts[1].split()
            self.type = self.type + " TROE"
            self.troe_a   = float(i_arr_params_str[0])   # a
            self.troe_ttt = float(i_arr_params_str[1])   # T***
            self.troe_t   = float(i_arr_params_str[2])   # T*
            # T** is optional; when omitted, the exp(-T**/T) term is inactive.
            # Length guard prevents IndexError on 3-parameter TROE lines.
            self.troe_tt  = float(i_arr_params_str[3]) if len(i_arr_params_str) > 3 else None

        elif self.chemkin_aux_line.find("SRI") >= 0:
            # SRI originally uses 3 parameters (a / b / c); CHEMKIN extension
            # allows up to 5 parameters by appending d / e.
            # This implementation only appends the type marker (e.g. "fall_off SRI")
            # and stores the values; raw text remains in chemkin_aux_lines.
            # Requires LOW to have been processed first.
            values = [float(v) for v in parts[1].split()]

            if len(values) not in (3, 5):
                raise ValueError(
                    f"SRI expects 3 or 5 parameters, got {len(values)}: {self.chemkin_aux_line}"
                )

            self.sri_a, self.sri_b, self.sri_c = values[:3]
            if len(values) == 5:
                self.sri_d, self.sri_e = values[3], values[4]
            # With 3 parameters, retain __init__ defaults: d=1.0, e=0.0
            # Append marker (requires LOW processed first; typical result: "fall_off SRI")
            self.type = self.type + " SRI"

        elif self.chemkin_aux_line.find("DUPLICATE") >= 0:
            # Overwrites the type string, discarding any previously appended markers
            # from LOW / TROE / SRI processing.
            self.type = "Duplicate"

        elif self.chemkin_aux_line.find("REV") >= 0:
            # CHEMKIN specifies three slash-separated Arrhenius coefficients after
            # REV, overriding the reverse rate obtained from equilibrium constants.
            # This implementation only sets the type marker; the three values are
            # not parsed here.
            self.type = "REV"

        else:  # the information of third_body
            # Third-body efficiency line format: "species/efficiency/ species/efficiency/ ... /"
            # Trailing "/" is required at the end of the line.
            # Example: "H2/2.4/ H2O/15.4/ CH4/2.0/"
            #   parts[0::2] → species names at even indices; the trailing empty string
            #                 from the final "/" must be removed via pop().
            #   parts[1::2] → efficiency values at odd indices, index-aligned with species.
            # Physical meaning: effective third-body concentration [M] = Σ f_i[M_i];
            # unlisted species default to f_i = 1.
            # NOTE: if the trailing "/" is missing, pop() will erroneously remove
            # the last species name instead of the empty string.
            self.type = "third_body"
            # Reusing the variable name; this slice actually contains species names
            i_arr_params_str = parts[0::2]
            i_arr_params_str.pop()
            for spe_name in i_arr_params_str:
                # To_spe is not extracted with this file: the original implementation
                # looks up a global species list by name and returns a species object with id.
                species_obj = Helps(species=species).get_specie_by_name(target_specie=spe_name)
                self.third_body_spe_list.append(species_obj["name"])  # type: ignore
            for efficiency_str in parts[1::2]:
                # float() inherently strips leading/trailing whitespace
                efficiency_value = float(efficiency_str)
                self.third_para.append(efficiency_value)

    def is_reactant(self, species_name):
        """Check whether the given species name is one of the reactants (case-insensitive).

        Note: CHEMKIN species names are case-sensitive by specification. This loose
        match tolerates capitalization typos, but may conflate species that differ
        only in case; the original implementation used a case-sensitive ``==``
        comparison.
        """
        return any(name.strip().upper() == species_name.strip().upper() for name in self.reactant)

    def is_product(self, species_name):
        """Check whether the given species name is one of the products (case-insensitive)."""
        return any(name.strip().upper() == species_name.strip().upper() for name in self.product)

    def is_in_reaction(self, species_name):
        """Check whether the given species appears in the reaction (as a reactant or a product)."""
        return self.is_reactant(species_name) or self.is_product(species_name)

    def get_stoichiometric_coefficient(self, species_name):
        """Return the stoichiometric coefficient of the given species (positive for products, negative for reactants)."""
        for idx, name in enumerate(self.reactant):
            if name.strip().upper() == species_name.strip().upper():
                return self.react_sto[idx]
        for idx, name in enumerate(self.product):
            if name.strip().upper() == species_name.strip().upper():
                return self.pro_sto[idx]
        raise ValueError(f"{species_name} not found in reaction")

    def are_on_opposite_sides(self, species_a, species_b):
        """Check whether two distinct species lie on opposite sides of the reaction (in either order)."""
        if species_a == species_b:
            return False
        return (self.is_reactant(species_a) and self.is_product(species_b)) or \
            (self.is_reactant(species_b) and self.is_product(species_a))

class ReactionThermoKinetics:
    def __init__(self, temp, third_type, a, n, e, reactions, species):
        self.delt_S = 0
        self.delt_H = 0
        self.gas_constant = 8.314
        self.T = temp
        self.type = third_type
        self.reactions = reactions
        self.species = species
        self.A = a
        self.N = n
        self.E = e
        self.kp = None
        self.kc = None
        self.kf = None
        self.kr = None

    def cal_s_h(self):
        """一次遍历净计量系数，同时计算 ΔS = Σ ν_i·S_i 与 ΔH = Σ ν_i·H_i。"""
        net_stoic = self.reactions["net_stoic"]
        for species_name, coefficient in net_stoic.items():
            species_record = self.species.get(species_name)
            if species_record is None:
                raise ValueError(f"Species '{species_name}' not found")

            s_val = species_record["S"]
            h_val = species_record["H"]

            if s_val is None:
                raise ValueError(f"Entropy for species '{species_name}' has not been calculated")
            if h_val is None:
                raise ValueError(f"Enthalpy for species '{species_name}' has not been calculated")

            self.delt_S += s_val * coefficient
            self.delt_H += h_val * coefficient


    def cal_k_p(self):
        """Calculate the thermodynamic equilibrium constant from ΔG° = ΔH° - T·ΔS°.

        Formula: ln K = ΔS°/R - ΔH°/(R·T), then Kp = exp(ln K).

        The resulting K is a dimensionless thermodynamic equilibrium constant
        (referenced to the standard state; CHEMKIN convention uses 1 atm as the
        standard-state pressure). When pressure is expressed in the standard-state
        unit, its numerical value equals the Kp expressed as a partial-pressure
        quotient.

        Unit consistency: ΔS° in J/(mol·K), ΔH° in J/mol, R = 8.314 J/(mol·K).
        Overflow guards: ln_kp > 700 → Kp = +∞; ln_kp < -700 → Kp = 0
        (math.exp overflows near ±709).

        ⚠️ Prerequisites: cal_s() and cal_h() must be called first to populate
        self.delt_S / self.delt_H. Both default to 0; if not called, this method
        silently yields Kp = 1.
        """
        # Calculate dimensionless ln Kp = ΔS°/R - ΔH°/(R·T)
        ln_kp = self.delt_S / self.gas_constant - self.delt_H / (self.gas_constant * self.T)
        # Overflow guard: math.exp would raise OverflowError for excessively large ln_kp
        if ln_kp > 700:
            self.kp = float('inf')
        # Underflow guard: exp approaches zero for very negative ln_kp; clip to 0
        elif ln_kp < -700:
            self.kp = 0.0
        # Normal range: Kp = exp(ln_kp)
        else:
            self.kp = math.exp(ln_kp)
        # Append the computed Kp to the history list (supports sequential multi-temperature calculations)

    def cal_k_c(self):
        """Convert dimensionless thermodynamic Kp to concentration-based Kc.

        For ideal gases, p_i = c_i R T and
            Kp = Kc * (R T / p°)^Δn
        hence
            Kc = Kp * (p° / (R T))^Δn,
        where Δn is the signed sum of net stoichiometric coefficients and p° is
        the standard-state pressure. Chemkin's conventional standard state is
        1 atm; this method uses SI units (p°=101325 Pa, R=8.314 J/(mol·K),
        concentration in mol/m³).

        Prerequisite: cal_k_p() must have populated self.kp. The resulting Kc
        carries concentration-unit exponent Δn, as required for kf/kr consistency.
        """
        if self.kp is None:
            raise RuntimeError("cal_k_p() must be called before cal_k_c()")
        if self.T <= 0:
            raise ValueError("Temperature must be positive")

        delta_n = sum(self.reactions["net_stoic"].values())
        standard_pressure_pa = 101325.0
        standard_concentration = standard_pressure_pa / (self.gas_constant * self.T)
        self.kc = self.kp * standard_concentration ** delta_n

    def cal_k_f(self):
        """Calculate the modified-Arrhenius rate constant and convert its concentration basis to SI.

        Formula:
            k_f = A_SI · T^N · exp[-(E · 4.184)/(R · T)]

        Input units under the default CHEMKIN convention:
            - A: concentration-unit-dependent; with concentration in mol/cm³, its
              units are (cm³/mol)^(n-1)·s⁻¹ for an n-th-order reaction.
            - N (temperature exponent): dimensionless.
            - E: cal/mol by default; converted to J/mol by multiplying by 4.184.
            - T: K; R is expected in J/(mol·K).

        SI conversion used here:
            to_si = (10⁻⁶)^(n-1), converting A from a mol/cm³-based concentration
            convention to a mol/m³-based convention. The method writes the result to
            self.kf and returns nothing.

        ⚠️ Assumptions and limitations:
        1. The mechanism uses default CHEMKIN activation-energy units cal/mol and
           concentration units mol/cm³. UNITS declarations are not parsed; other E or
           concentration units require a different conversion.
        2. n is currently estimated as sum(abs(sto) for sto in self.react_sto), then
           reduced by one for the A conversion. This is valid only when react_sto still
           contains the original forward reactant stoichiometry and no FORD/custom
           reaction orders apply. If parsing has net-canceled shared species, this
           estimate may be wrong.
        3. Third-body and fall-off rate parameters have different effective orders:
           the ordinary third-body rate and LOW (k₀) may include an extra [M] order;
           the fall-off main-line A (k∞) generally does not. This method does not
           distinguish those cases when calculating to_si.
        4. For fall_off, main-line A/N/E describes the high-pressure limit k∞; for
           chem_activate it describes k₀. No pressure/fall-off correction (Pr, Fcent)
           is applied, so this is not necessarily the complete pressure-dependent k_f.
        5. The type map validates supported labels only. REV/Duplicate or a type label
           absent from the map raises ValueError. E < 0 with a sufficiently large
           magnitude can also make math.exp overflow; only underflow is guarded.
        """

        net_stoic = self.reactions["net_stoic"]
        reaction_order = sum(-sto for sto in net_stoic.values() if sto < 0)
        to_si = 1e-6 ** reaction_order
        if self.T <= 0:
            raise ValueError("Temperature must be positive")
        # CHEMKIN default E is cal/mol; convert to J/mol for consistency with R=8.314 J/(mol·K).
        # Every supported type uses the same energy-unit factor; this map only validates labels.
        factor_map = {
            "elementary": 4.184,
            "fall_off": 4.184,
            "chem_activate": 4.184,
            "chem_activate TROE": 4.184,
            "fall_off TROE": 4.184,
            "third_body": 4.184,
            "fall_off SRI": 4.184,
        }
        factor = factor_map.get(self.type)
        if factor is None:
            raise ValueError(f"Unknown reaction type: {self.type}")

        exponent = -self.E * factor / (self.gas_constant * self.T)

        # math.exp(-700) ≈ 10^(-304), close to the double-precision lower limit
        if exponent < -700:
            self.kf = 0.0
        else:
            self.kf = self.A * to_si * (self.T ** self.N) * math.exp(exponent)

    def cal_k_r(self):
        """Calculate the reverse rate constant kr = kf / Kc（Kc = kf/kr）。

        Raises:
        RuntimeError: If cal_k_f() or cal_k_c() has not been called.
    """
        if self.kf is None:
            raise RuntimeError('cal_k_f() must be called first')
        if self.kc is None:
            raise RuntimeError('cal_k_c() must be called first')

        if self.kc == 0:
            self.kr = float('inf')
        else:
            self.kr = self.kf / self.kc

class ChemkinStandardizer:
    def __init__(self, mech_file_path, therm_file_path, old_mech_path=None, new_mech_path=None):
        self.Old_mech = old_mech_path
        self.New_mech = new_mech_path
        self.mech_file = mech_file_path
        self.therm_file = therm_file_path
        self.elements = {}
        self.species = {}
        self.reactions = []
        self.a_L = []
        self.a_H = []
        self.T_l = None
        self.T_m = None
        self.T_h = None

    def convert_to_standard(self):
        """Convert a non-standard CHEMKIN mechanism file to a standardized format.

        Conversion rules:
            1. Convert all content to uppercase.
            2. Skip blank lines within ELEMENTS / SPECIES / REACTIONS blocks;
               write the original END line when encountered（不会自动补写 END）。
            3. Replace " = " with the reversible separator "<=>" in reaction lines
               （CHEMKIN 中 " = " 本就是可逆记号，"=> " 才是不可逆）。
            4. Preserve comment lines (starting with !) as-is.
        """

        # Open the original mechanism file (read) and the standardized output file (write).
        file_old = open(self.Old_mech, 'r')
        file_new = open(self.New_mech, 'w')
        raw_lines = file_old.readlines()
        # Block start index; used to retain header comments only before the first block.
        block_start_idx = float('inf')

        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            line = line.rstrip("\n")
            line = line.upper()
            line = line.lstrip()

            # Header comment lines (starting with !) are preserved only before ELEMENTS.
            if line.startswith('!') and i < block_start_idx:
                file_new.write(f'{line}\n')
                i += 1

            # Detect ELEMENTS or SPECIES block header.
            elif line.startswith('ELEMENTS') or line.startswith('SPECIES'):
                # Record the current line index to control comment retention range.
                block_start_idx = i
                # Write the block header line (ELEMENTS or SPECIES).
                file_new.write(f'{line}\n')
                j = 1
                while i + j < len(raw_lines):
                    # Read the next line, strip whitespace, and convert to uppercase.
                    l_next = raw_lines[i + j].strip().upper()
                    # Skip blank lines (whitespace-only or empty string).
                    if l_next.isspace() or l_next == "":
                        j += 1
                        continue
                    # Encounter END: write it and terminate block processing.
                    elif l_next.startswith('END'):
                        file_new.write(l_next + '\n')
                        break
                    # Regular data line (element/species name): write and continue.
                    else:
                        file_new.write(l_next + '\n')
                        j += 1
                i = i + j + 1

            # REACTIONS block: process reaction lines, replace ' = ' with '<=>'.
            elif line.startswith('REACTIONS'):
                file_new.write(f'{line}\n')
                j = 1
                while i + j < len(raw_lines):
                    l_next = raw_lines[i + j].strip().upper()

                    if l_next.isspace() or l_next == '':
                        j += 1
                        continue
                    elif l_next.startswith('!'):
                        # Write comment lines as-is
                        file_new.write(l_next + '\n')
                        j += 1
                    elif l_next.find(' = ') > 0:
                        l_next = l_next.replace(' = ', '<=>')
                        file_new.write(l_next + '\n')
                        j += 1
                    elif l_next.startswith('END'):
                        file_new.write(l_next + '\n')
                        break
                    else:
                        file_new.write(l_next + '\n')
                        j += 1
                i = i + j + 1

            # All other lines (THERMO, TRANSPORT, global END, etc.) are kept as-is.
            else:
                file_new.write(f'{line}\n')
                i += 1

        file_old.close()
        file_new.close()
        print('Standard file created successfully.')


    def load_mechanism(self):
        """Read a CHEMKIN mechanism file and attempt to build element, species,
        and reaction objects.

        Expected workflow:
            1. Load the entire mechanism file into memory.
            2. Scan the ELEMENTS and SPECIES blocks to construct corresponding objects.
            3. Starting from the REACTIONS block, identify reversible and irreversible
               main reaction lines.
            4. Attach subsequent auxiliary lines to the current reaction.
            5. Output reading statistics.

        Note: this function still uses the legacy interface and is NOT yet aligned
        with the newer class interfaces (e.g., ChemkinReaction). Known mismatches
        are flagged in the comments below; the current implementation should NOT
        be considered verified or production-ready.
        """

        # Read the entire mechanism file; different blocks are located by slicing
        # with line indices. No encoding is specified, and open() is not used as
        # a context manager — if an exception occurs mid-read, the file handle
        # may not be closed promptly.
        mech_input = open(self.mech_file, "r")
        all_lines = mech_input.readlines()
        mech_input.close()
        # Line-index cursor: incremented by 1 for each processed line. When the
        # REACTIONS header is encountered and the loop breaks, line_id equals the
        # 0-based index of that header plus 1, so slicing all_lines[line_id:]
        # starts from the next line after the header.
        line_id = 0

        # Phase 1: scan ELEMENTS and SPECIES blocks, stop at the REACTIONS header.
        for i in all_lines:
            line_id += 1
            if i.startswith("ELEMENTS"):
                for j in all_lines[line_id:]:
                    if j.find("END") >= 0:
                        break
                    for element_name in j.split():
                        if element_name.startswith("!"):
                            # Inline comment: the following token is not an element
                            break
                        key = element_name.strip().upper()
                        self.elements[key] = {
                            "name": key,
                            "mass": getattr(Element(key), "mass", None),
                        }

            if i.startswith("SPECIES"):  # 读取物种信息
                for j in all_lines[line_id:]:
                    if j.find("END") >= 0:
                        break
                    part = j.split()
                    for species_key in part:
                        species_key.strip().upper()
                        self.species[species_key] = {  # 键是字符串，值是字典
                            "name": species_key,
                            "elements": Helps(formula=species_key).parse_formula(),
                            "a_H": [],  # 高温段 7 个系数
                            "a_L": [],  # 低温段 7 个系数
                            "T_l": None,
                            "T_h": None,
                            "T_m": None,
                            "T": None,
                            "H": None,  # 计算后为 J/mol
                            "S": None,  # 计算后为 J/(mol·K)
                            "Cp": None,
                        }

            if i.find("REACTIONS") >= 0:
                break

        # 第二阶段：从 line_id 开始扫描反应主行与辅助行。
        # ⚠️ 此起点及内层扫描需与实际输入格式一起验证；当前没有跳过空行/注释行。
        total_reactions = 0
        reversible_count = 0
        irreversible_count = 0
        reaction_index = 0
        for line in all_lines[line_id:]:
            line = line.upper()
            if " = " in line:
                line = line.replace(" = ", "<=>")
            if line.find("<=>") > 0:
                total_reactions += 1  # type: ignore
                reversible_count += 1
                react = ChemkinReaction(chemkin_reaction_line=line)
                react.extract_row_params()
                net_stoic = {}
                for species, sto in zip(
                        react.reactant + react.product,
                        react.react_sto + react.pro_sto,
                ):
                    net_stoic[species] = net_stoic.get(species, 0) + sto
                net_stoic = {
                    species: sto
                    for species, sto in net_stoic.items()
                    if sto != 0
                }

                reaction_record = {
                    "index": reaction_index,
                    "equation": react.reaction_express,
                    "reversibility": "reversible",
                    "net_stoic": net_stoic,
                    # 不要把反应方向、第三体、fall-off 混成一个 type 字符串
                    "rate_model": react.type,
                    "third_body": {
                        "enabled": False,
                        "efficiencies": {},
                    },

                    # 主反应行 Arrhenius 参数
                    "arrhenius": {
                        "A": react.A,
                        "N": react.N,
                        "E": react.E,
                        "E_unit": "cal/mol",
                        "A_unit": None,  # A 的单位依赖反应级数和机理单位制
                    },

                    # 可选压力依赖数据
                    "low_pressure": {},  # LOW 行：A0、b0、E0
                    "high_pressure": {},  # HIGH 行：高压极限参数
                    "broadening": {},  # TROE 或 SRI 参数
                    "plog": [],
                    "chebyshev": None,

                    "duplicate": False,
                    "reverse_arrhenius": None,  # REV 参数
                    "raw_aux_lines": [],
                    "evaluations": [],
                    "rate_net": [],
                    "rate_rev": [],
                }
                self.reactions.append(reaction_record)
                current_reaction = reaction_record
                reaction_index += 1

            elif line.find("=>") > 0:  # 不可逆反应
                total_reactions += 1  # type: ignore
                irreversible_count += 1
                # 构造、调用和保存存在与上方分支相同的问题。
                react = ChemkinReaction(chemkin_reaction_line=line)
                react.extract_row_params()
                net_stoic = {}
                for species, sto in zip(
                        react.reactant + react.product,
                        react.react_sto + react.pro_sto,
                ):
                    net_stoic[species] = net_stoic.get(species, 0) + sto
                net_stoic = {
                    species: sto
                    for species, sto in net_stoic.items()
                    if sto != 0
                }

                reaction_record = {
                    "index": reaction_index,
                    "equation": react.reaction_express,
                    "reversibility": "irreversible",
                    "net_stoic": net_stoic,
                    # 不要把反应方向、第三体、fall-off 混成一个 type 字符串
                    "rate_model": react.type,
                    "third_body": {
                        "enabled": False,
                        "efficiencies": {},
                    },

                    # 主反应行 Arrhenius 参数
                    "arrhenius": {
                        "A": react.A,
                        "N": react.N,
                        "E": react.E,
                        "E_unit": "cal/mol",
                        "A_unit": None,  # A 的单位依赖反应级数和机理单位制
                    },

                    # 可选压力依赖数据
                    "low_pressure": {},  # LOW 行：A0、b0、E0
                    "high_pressure": {},  # HIGH 行：高压极限参数
                    "broadening": {},  # TROE 或 SRI 参数
                    "plog": [],
                    "chebyshev": None,
                    "duplicate": False,
                    "reverse_arrhenius": None,  # REV 参数
                    "raw_aux_lines": [],
                    "evaluations": [],
                    "rate_net": [],
                    "rate_rev": [],
                }
                self.reactions.append(reaction_record)
                current_reaction = reaction_record
                reaction_index += 1
            else:
                # 非主反应行预期是上一条主反应的辅助续行（LOW/TROE/效率等）。
                # ⚠️ 若此前没有成功处理过主反应行，react 尚未绑定；新接口方法名也不是 para_add_line。
                react = ChemkinReaction(chemkin_aux_line=line)
                react.parse_chemkin_aux_line(species=self.species)
                if react.type == 'fall_off':
                    values = {'A': react.A_L, 'N': react.N_L, 'E': react.E_L,}
                    current_reaction['low_pressure'].update(values) # type: ignore
                    current_reaction['rate_model'] = react.type

                elif react.type == 'chem_activate':
                    values = {'A': react.A_H, 'N': react.N_H, 'E': react.E_H,}
                    current_reaction['high_pressure'].update(values) # type: ignore
                    current_reaction['rate_model'] = react.type

                elif react.chemkin_aux_line.find("TROE") >= 0:
                    current_reaction["third_body"]["enabled"] = True  # type: ignore
                    values = {'a': react.troe_a, 'T***': react.troe_ttt, 'T*': react.troe_t, }
                    current_reaction['broadening'].update(values)  # type: ignore
                    current_reaction['rate_model'] = "fall_off TROE"

                elif react.chemkin_aux_line.find("SRI") >= 0:
                    # SRI 是 fall-off 的展宽模型，参数已由 parse_chemkin_aux_line() 解析。
                    current_reaction["rate_model"] = "fall_off SRI"
                    values = {
                        "model": "SRI",
                        "a": react.sri_a,
                        "b": react.sri_b,
                        "c": react.sri_c,
                        "d": react.sri_d,  # 3 参数时默认 1.0
                        "e": react.sri_e,  # 3 参数时默认 0.0
                    }
                    current_reaction["broadening"].update(values)  # type: ignore
                    current_reaction["raw_aux_lines"].append(line)  # type: ignore

                else:
                    efficiencies = dict(zip(
                        react.third_body_spe_list,
                        react.third_para,
                    ))
                    current_reaction["third_body"]["enabled"] = True  # type: ignore
                    current_reaction["third_body"]["efficiencies"].update(efficiencies)  # type: ignore
                    current_reaction["raw_aux_lines"].append(line)  # type: ignore
            # 该自增只修改计数变量；for 迭代器本身独立推进，不影响其索引。
            line_id += 1

        print(f'Loading the file of reaction mechanism: {self.mech_file}.')

    def load_therm(self):
        """Read the thermodynamic data file (NASA 7-coefficient format) and load
        temperature bounds and polynomial coefficients into the species dictionary.

        NASA 7 format uses fixed column positions:
            Column 80 (0-based index 79) is the line-type marker:
                "1" — species name line + temperature bounds (T_l, T_m, T_h)
                "2" — high-temperature coefficients a0–a4 (5 values, 15 columns each)
                "3" — high-temperature coefficients a5–a6 + low-temperature coefficients a0–a2
                "4" — low-temperature coefficients a3–a6 (completes the 7 coefficients)
            High-temperature set (a_H) has 7 coefficients; low-temperature set (a_L) has 7.
        """

        therm_input = open(self.therm_file, 'r')
        all_lines = therm_input.readlines()
        # Currently active species dict entry; None means no species matched yet.
        current_spe: Optional[Dict[str, Any]] = None

        for line in all_lines:
            # Column 80 (index 79) is the line-type marker; treat short lines as non-data.
            line_type = line[79] if len(line) > 79 else ""

            if line_type == "1":
                # Extract species name from the first 18 columns, strip whitespace, uppercase.
                species_name = line[:18].split()[0].upper()
                # Look up the corresponding species in the species dictionary.
                current_spe = self.species.get(species_name)

                # Raise if the therm file references a species not declared in the mechanism.
                if current_spe is None:
                    raise KeyError(f"Thermo file contains unknown species: {species_name}.")

                # Extract the three temperature boundaries (in K) from fixed column positions.
                current_spe["T_l"] = float(line[45:55])
                current_spe["T_h"] = float(line[55:65])
                current_spe["T_m"] = float(line[65:75])

            elif line_type in {"2", "3", "4"}:
                # Coefficient lines must follow a type "1" line that sets the active species.
                if current_spe is None:
                    raise ValueError("NASA coefficient line has no preceding known species")

                if line_type == "2":
                    current_spe["a_H"].extend(
                        float(line[start:start + 15]) for start in (0, 15, 30, 45, 60)
                    )
                elif line_type == "3":
                    current_spe["a_H"].extend(
                        float(line[start:start + 15]) for start in (0, 15)
                    )
                    current_spe["a_L"].extend(
                        float(line[start:start + 15]) for start in (30, 45, 60)
                    )
                else:  # line_type == "4"
                    current_spe["a_L"].extend(
                        float(line[start:start + 15]) for start in (0, 15, 30, 45)
                    )
        print(f'Loading the file of thermodynamics : {self.therm_file}')
        therm_input.close()

class Helps:
    def __init__(self, formula=None, species=None, elements=None):
        self.species = species
        self.elements = elements
        self.formula = formula

    def get_specie_by_name(self, target_specie):
        """给定物种名，返回 self.species 中对应的物种记录字典；找不到返回 None。"""
        if not target_specie:
            return None
        return self.species.get(target_specie.strip().upper())

    def get_element_by_name(self, target_element):
        """给定元素名，返回 * element *对象"""
        if not target_element:
            return None
        return self.elements.get(target_element.strip().upper())

    def parse_formula(self):
        """把全大写物种名解析为 {元素: 原子数} 字典。"""

        n = len(self.formula)
        element_counts, i = {}, 0
        last_element = None

        while i < n:
            ch = self.formula[i]

            if ch.isdigit():
                num_start = i
                while i < n and self.formula[i].isdigit():
                    i += 1
                number = int(self.formula[num_start:i])

                if last_element is not None:
                    element_counts[last_element] = number
                continue

            if ch.isupper():
                if i + 1 < n and self.formula[i + 1].islower():
                    symbol = self.formula[i:i+2]
                    i += 2
                else:
                    symbol = ch
                    i += 1

                element_counts[symbol] = 1
                last_element = symbol
                continue
            # 其他字符（小写字母单独出现、括号等）跳过
            i += 1
        return element_counts
