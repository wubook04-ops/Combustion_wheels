import numpy as np
import os

class ConvertMatrixQKT:
    def __init__(self, start_step, end_step,filepath_q='./train_datas/q/',
                 filepath_k='./train_datas/k/', filepath_t='./train_datas/t/', filepath_dt='./train_datas/dt/'):
        self.filepath_q = filepath_q
        self.filepath_k = filepath_k
        self.filepath_t = filepath_t
        self.filepath_dt = filepath_dt
        self.start_step = start_step
        self.end_step =end_step
        self.sum_q_ij = None

    def main(self):
        # Create the three output directories: k (transition probabilities), t (transition amounts), dt (time steps).
        # exist_ok=True avoids errors if a directory already exists (note: the source filepath_q is not created here).
        for _ in (self.filepath_k, self.filepath_t, self.filepath_dt):
            os.makedirs(_, exist_ok=True)

        # Process step by step: range excludes end_step, so there are (end_step - start_step) step indices.
        for i_step in range(self.start_step, self.end_step):
            # Load this step's rate matrix q_ij (off-diagonal part of Q); the filename is the step index.
            q_ij = np.loadtxt(os.path.join(self.filepath_q, f'{i_step}.csv'), delimiter=',')
            # Matrix dimension, i.e. number of species / nodes (original variable name n_mile kept).
            n_mile = len(q_ij)
            # Work on a copy so the original q_ij stays untouched while the diagonal is zeroed.
            q_ij_ = q_ij.copy()
            # Zero the diagonal, keeping only cross-state transition rates i -> j.
            # As in the original, this runs n_mile times inside the loop; one call would suffice.
            np.fill_diagonal(q_ij_, 0.0)
            # One characteristic time step per row dt0[i] = reciprocal of that row's rate sum.
            dt0 = np.zeros(n_mile)
            # Transition probability matrix k0: k0[i,j] = q_ij / row sum.
            k0 = np.zeros((n_mile, n_mile))
            # Transition amount matrix t0: t0[i,j] = k0[i,j] * dt0[i].
            t0 = np.zeros((n_mile, n_mile))

            # Normalize / decompose row by row (one source state i at a time).
            for i in range(n_mile):
                # Sum of off-diagonal rates in row i = total leaving rate of state i.
                self.sum_q_ij = sum(q_ij_[i])
                if self.sum_q_ij != 0:
                    # Characteristic time / mean waiting time: reciprocal of the total leaving rate.
                    dt0[i] = 1.0 / self.sum_q_ij
                    for j in range(n_mile):
                        # Normalize into a transition probability (inverse of q_ij = k_ij / dt_i).
                        k0[i][j] = q_ij_[i][j] / self.sum_q_ij
                        # Transition amount = probability * time step (source concentration c_i is NOT multiplied here).
                        # Substituting gives q_ij_[i][j] / (row sum)^2; kept as in the original.
                        t0[i][j] = k0[i][j] * dt0[i]
                else:
                    # Zero row sum: no outflow from this state (absorbing / no transition); set all three to 0.
                    dt0[i] = 0.0
                    dt0[i] = 0.0
                    for j in range(n_mile):
                        k0[i][j] = 0.0
                        t0[i][j] = 0.0

            # Save k / t / dt by step index, scientific notation with 8 decimals.
            # k and t are 2-D matrices with comma delimiter; dt is 1-D and uses the default (space) delimiter.
            np.savetxt(os.path.join(self.filepath_k, f'{i_step}.csv'), k0, delimiter=',', fmt='%.8e')
            np.savetxt(os.path.join(self.filepath_t, f'{i_step}.csv'), t0, delimiter=',', fmt='%.8e')
            np.savetxt(os.path.join(self.filepath_dt, f'{i_step}.csv'), dt0, fmt='%.8e')