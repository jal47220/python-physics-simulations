import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import animation

# Set the seed for reproducibility
np.random.seed(123)

# Define constants
J = 1.0e-21  # Interaction energy in Joules (typical for ferromagnetic materials)
H = 0  # External magnetic field in Tesla (no external field for this simulation)
KB = 1.380649e-23  # Boltzmann constant in Joules per Kelvin
T = 2.269  # Initial temperature of the region/material in Kelvin
T_C = T * J / KB  # Approximate critical temperature in Kelvin
L = 100  # Lattice size in number of spins
SEED_CENTER = L // 2  # Center of nucleation seed in number of spins (rounded down to Int value)
SEED_SIZE = L // 5  # Nucleation seed size in number of spins (rounded down to Int value)
STEPS = 100  # Number of Monte Carlo steps

# Ferromagnetic lattice initialized as region of up spins
ferro_lattice = np.ones((L, L))

# Nucleation seed initialized as small region of aligned spins in larger region of opposite spins
seed_lattice = -np.ones((L, L))  # Background spins set to down
seed_lattice[SEED_CENTER - SEED_SIZE:SEED_CENTER + SEED_SIZE,
             SEED_CENTER - SEED_SIZE:SEED_CENTER + SEED_SIZE] = 1  # Seed region

def calculate_energy_difference(lattice, i, j):
    """
    Compute energy difference required to flip a spin at (i, j) based on neighboring spin values

    :param lattice: Region of spins
    :param i: x-value of designated spin position
    :param j: y-value of designated spin position
    :return energy_difference:
    """
    spin = lattice[i, j]  # Spin value at (i, j)
    # Calculate sum of the neighboring spins to the spin at (i, j)
    nb = (np.roll(lattice, 1, axis=0)[i, j] + np.roll(lattice, -1, axis=0)[i, j] +
          np.roll(lattice, 1, axis=1)[i, j] + np.roll(lattice, -1, axis=1)[i, j])
    energy_difference = 2 * spin * (J * nb + H)
    return energy_difference

def update_lattice(lattice):
    """
    Update the region of spins using the Metropolis algorithm

    :param lattice: Region of spins
    :return lattice: Updated region of spins
    """
    for _ in range(L * L):  # Randomly pick L^2 sites per step
        i, j = np.random.randint(0, L, size=2)  # Choose a random site
        d_e = calculate_energy_difference(lattice, i, j)
        if d_e <= 0 or np.random.rand() < np.exp(-d_e / (KB * T_C)):
            lattice[i, j] *= -1  # Flip the spin
    return lattice

def update(num, ferro_im, seed_im):
    """
    Update the plots for the current frame

    :param num: Current frame number
    :param ferro_im: Ferromagnetic lattice display object
    :param seed_im: Seed lattice display object
    """
    ferro_lattice[:] = update_lattice(ferro_lattice)
    seed_lattice[:] = update_lattice(seed_lattice)
    ferro_im.set_data(ferro_lattice)
    seed_im.set_data(seed_lattice)

def main():
    # Create a figure with two subplots
    fig, ax = plt.subplots(1, 2, figsize=(14, 6))
    ax[0].set_title('Ferromagnetic State')
    ax[1].set_title('Nucleation Seed')

    # Add a label for the figure
    fig.text(0.5, 0.95, 'Ising Model Simulation', ha='center', va='center',
             fontsize=16, fontweight='bold')

    # Display the two Ising lattices with appropriate color mapping and orientation
    ferro_im = ax[0].imshow(ferro_lattice, cmap='bwr', interpolation='nearest',
                       origin='lower', vmin=-1, vmax=1)
    seed_im = ax[1].imshow(seed_lattice, cmap='bwr', interpolation='nearest',
                       origin='lower', vmin=-1, vmax=1)

    # Create a legend for spin values and add it to the figure
    spin_legend = [
        mpatches.Patch(color='blue', label='Down Spin'),
        mpatches.Patch(color='red', label='Up Spin')
    ]
    fig.legend(handles=spin_legend, loc='center right', ncol=1)

    # Create and save the animation
    ani = animation.FuncAnimation(fig, update, frames=STEPS, interval=100, fargs=(ferro_im, seed_im))
    ani.save('ising_model.gif', writer='pillow')

if __name__ == "__main__":
    main()
