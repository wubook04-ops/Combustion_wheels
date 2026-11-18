import numpy as np
import torch.nn as nn
import torch
import os

class GenerateQ:
    def __init__(self, n_species, dt, start_step, end_step, concentration_cols,
                 learning_rate=1e-1, n_epochs=1000000, epsilon=1e-12,filepath_q='./train_datas/q/', ext='csv'):
        self.n_species = n_species
        self.n_epochs = n_epochs
        self.epsilon = epsilon
        self.dt = dt
        self.start_step = start_step
        self.end_step = end_step
        self.k_ini = torch.randn((self.n_species, self.n_species)) * 0.1
        self.learning_rate = learning_rate
        self.best_loss = float("inf")
        self.no_improve_counter = 0
        self.valid_data_tensor = torch.tensor(concentration_cols.to_numpy(), dtype=torch.float32)
        self.ext = ext
        self.filepath_q = filepath_q
        self.k_pos = None
        self.mask = None
        self.Q = None
        self.best_k_raw = None
        self.diag = None
        self.index = None
        self.k_raw = None
        self.optimizer = None
        self.scheduler = None
        self.best_Q = None
        self.P = None
        self.c_0 = None
        self.c_0_basic = None
        self.c_true_next = None
        self.c_pred_next = None
        self.loss = None
        self.total_loss = None
        self.grad_norm = None
        self.lr = None
        self.prediction = None
        self.pred_c_all = None
        self.local_start_step = None
        self.local_end_step = None
        self.c_0_next = None
        self.orig_c_all = None

    def build_matrix_q(self):

        """
        Construct the transition rate matrix Q (generator matrix) for the Markov chain.

        The diagonal elements of matrix Q are negative, representing the total rate
        of leaving the current state; the off-diagonal elements are positive,
        representing the transition rates between different states. The sum of each
        row is constrained to be zero (generator matrix property).
        """

        # Apply Softplus activation to raw rate parameters to ensure all rates are non-negative.
        # Softplus is a smooth approximation of ReLU, outputting strictly positive values.
        self.k_pos = nn.functional.softplus(self.k_raw)
        # Create a mask matrix: 0 on the diagonal, 1 on off-diagonals.
        # Used to block self-transitions (a state cannot transition to itself).
        self.mask = 1.0 - torch.eye(self.n_species)
        # Apply the mask to zero out the diagonal positions of the rate matrix.
        # Only cross-state transitions are physically meaningful.
        self.k_pos = self.k_pos * self.mask
        # Clone the masked rate matrix as the initial Q matrix.
        # Off-diagonal elements represent transition rates between states.
        self.Q = self.k_pos.clone()
        # Compute the sum of off-diagonal elements for each row (total leaving rate).
        # This value will be used as the absolute value for the diagonal elements.
        self.diag = torch.sum(self.Q, dim=1)
        self.index = np.arange(self.n_species)
        self.Q[self.index,self.index] = -1 * self.diag[self.index]
        return self.Q

    def optimize_matrix_q(self):
        # Wrap the initial rate tensor as a trainable parameter (softplus later keeps rates non-negative).
        self.k_raw = nn.Parameter(self.k_ini)
        # Adam optimizer over the rate parameters only.
        self.optimizer = torch.optim.Adam([self.k_raw], lr=self.learning_rate)
        # LR scheduler: monitor min loss; halve lr after 50 epochs without improvement.
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, 'min', patience=50, factor=0.5)

        # Train for the configured number of epochs.
        for epoch in range(self.n_epochs):
            # Clear gradients from the previous epoch.
            self.optimizer.zero_grad()
            # Rebuild generator matrix Q from current k_raw (negative diagonal = total leaving rate, row sums = 0).
            self.Q = self.build_matrix_q()
            # Matrix exponential gives the one-step transition matrix P = exp(Q * dt).
            self.P = torch.matrix_exp(self.Q * self.dt)

            # Take the concentration at the start of the validation window as the initial state.
            c_0_step = self.valid_data_tensor[self.local_start_step]
            # Scalar loss accumulator for backprop (created on CPU by default).
            loss_sum = torch.zeros((), dtype=torch.float32)
            # Value-only accumulator for logging / scheduler / early stopping (plain Python float, no graph).
            total_loss_value = 0.0

            # Free-run forward from the step after the start to the end of the window.
            for step in range(self.local_start_step+1, self.local_end_step):
                self.c_true_next = self.valid_data_tensor[step]
                self.c_pred_next = torch.matmul(c_0_step, self.P)
                # Clamp to epsilon or above to avoid log(0).
                self.c_pred_next = torch.clamp(self.c_pred_next, min=self.epsilon)
                self.loss = torch.mean(torch.pow((torch.log(self.c_pred_next) - torch.log(self.c_true_next + self.epsilon)),2))
                # Attach each step loss to loss_sum's autograd graph; keep a separate detached float for logging / early stopping.
                loss_sum += self.loss
                # .item() extracts a scalar value, detached from the graph; only the float is accumulated.
                total_loss_value += self.loss.item()
                # Free-running: feed this prediction into the next step (no teacher forcing, no detach).
                c_0_step = self.c_pred_next

            loss_sum.backward()
            # Clip gradients to keep parameter updates stable.
            nn.utils.clip_grad_norm_([self.k_raw], max_norm=1.0)
            # Update the rate parameters using the computed gradients.
            self.optimizer.step()
            # The scheduler takes a plain float, not a tensor carrying the graph.
            self.scheduler.step(total_loss_value)
            # Keep only the value (detach from the computation graph) for logging / early stopping.
            self.total_loss = total_loss_value

            # If the best loss is improved, save a snapshot.
            if self.total_loss < self.best_loss:
                self.best_loss = self.total_loss
                self.best_Q = self.Q.detach().clone()
                # Reset the no-improvement counter.
                self.no_improve_counter = 0
                # Save the best rate parameters, also detached.
                self.best_k_raw = self.k_raw.detach().clone()
            else:
                self.no_improve_counter += 1

            # Print training status every 10000 epochs.
            if epoch % 10000 == 0:
                # Mean absolute gradient of the rate parameters (.item() returns a float).
                self.grad_norm = self.k_raw.grad.abs().mean().item()
                self.lr = self.optimizer.param_groups[0]['lr']
                print(
                    f'Epoch [{epoch:5d}/{self.n_epochs}], Loss: {self.total_loss:.8e}, Grad: {float(self.grad_norm):.3e} LR: {self.lr:.2e}')
            # Early stop after 200 epochs without improvement.
            if self.no_improve_counter >= 200:
                break
        print(f'Best loss = {self.best_loss:.8e}')

    def pred_c(self):
        # Disable gradient tracking; inference builds no graph and holds no extra memory.
        with torch.no_grad():
            self.P = torch.matrix_exp(self.best_Q * self.dt)
            self.c_0_basic = self.valid_data_tensor[self.local_start_step]
            self.c_0_next = torch.matmul(self.c_0_basic, self.P)
            # Same lower-bound clamp as in training for consistent numerics.
            self.c_0_next = torch.clamp(self.c_0_next, min=self.epsilon)

    def main(self):
        os.makedirs(str(self.filepath_q), exist_ok=True)
        self.c_0 = self.valid_data_tensor[self.start_step]
        # Predicted concentration sequence, initialized with the start value.
        self.pred_c_all = [self.c_0, ]
        # Sliding window: treat each step as a local start and train one segment at a time.
        for i in range(self.start_step, self.end_step):
            self.best_loss = float('inf')
            self.no_improve_counter = 0
            # Local window start fed to optimize_matrix_q().
            self.local_start_step = int(i)
            # Local window end (length 2: only "current step -> next step" is supervised).
            self.local_end_step = int(i) + 2
            # Train this segment; updates best_Q / best_k_raw / best_loss on the object.
            self.optimize_matrix_q()
            q_np = self.best_Q.numpy()
            np.savetxt(str(self.filepath_q) + str(i) + '.csv', q_np, delimiter=',', fmt='%.8e')
            print(f"Training completed. Best loss: {self.best_loss:.8f}\n")
            self.pred_c()
            # Append this step's prediction to the predicted sequence.
            self.pred_c_all.append(self.c_0_next)
            # Warm-start the next segment with this segment's best rate parameters.
            self.k_ini = self.best_k_raw