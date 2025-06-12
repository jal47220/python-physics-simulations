import pygame
import numpy as np

# Window dimensions
WIDTH, HEIGHT = 800, 800

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Sierpiński carpet parameters
LEVELS = 5  # Fractal iterations

# Wavefunction parameters
L = 1.0  # Domain size
PKT_WIDTH = 0.1  # Gaussian wave packet width
K = 2 * np.pi / 0.2  # Wave vector

# Spatial/Time Steps
DX = L / WIDTH
DT = 0.001

class Wavefunction:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.laplacian = 0
        self.potential = 0

        # Gaussian wave packet
        self.psi = np.exp(-((x - L / 2) / PKT_WIDTH)**2 - ((y - L / 2) / PKT_WIDTH)**2) * np.exp(1j * K * x)

    def evolve(self):
        # Approximate the Laplacian using second-order finite difference
        self.laplacian = (np.roll(self.psi, -1, axis=0) + np.roll(self.psi, 1, axis=0) +
                            np.roll(self.psi, -1, axis=1) + np.roll(self.psi, 1, axis=1) -
                            4 * self.psi) / DX**2

        # Potential (Sierpiński carpet boundary)
        potential = sierpinski_carpet(self.x, LEVELS)
        self.potential = np.where(potential == 1, 1.0, 0.0)  # make sure it's either 1 or 0

        # Time-evolution
        self.psi += DT * (-1j * self.laplacian - 1j * self.potential * self.psi)

        # Apply boundary conditions to avoid infinite energy
        self.psi[0, :] = 0
        self.psi[-1, :] = 0
        self.psi[:, 0] = 0
        self.psi[:, -1] = 0

        # Normalize the wave function to avoid energy buildup
        self.psi /= np.linalg.norm(self.psi)

    def calculate_probability_density(self):
        return np.abs(self.psi)**2

    def get_total_energy(self):
        # Calculate kinetic energy
        kinetic_energy = -0.5 * np.sum(np.conj(self.psi) * self.laplacian * self.psi)

        # Calculate potential energy
        potential_energy = np.sum(np.conj(self.psi) * self.potential * self.psi)

        # Total energy is the sum of kinetic and potential energy
        total_energy = np.real(kinetic_energy + potential_energy)
        return total_energy

def sierpinski_carpet(x, level):
    # Create a binary grid for the Sierpiński Carpet fractal
    carpet = np.ones_like(x)
    size = len(x)

    for i in range(level):
        # Reduce the block size at each level
        block_size = size // (3 ** (i + 1))

        for j in range(3 ** (i + 1)):
            for k in range(3 ** (i + 1)):
                if (j % 3 == 1) and (k % 3 == 1):  # Designate the "hole" in the middle of each block
                    carpet[j * block_size:(j + 1) * block_size, k * block_size:(k + 1) * block_size] = 0
    return carpet

def draw_carpet(surface, x, y, width, height, level):
    if level == 0:
        pygame.draw.rect(surface, WHITE, (x, y, width, height))
    else:
        w = width // 3
        h = height // 3
        for i in range(3):
            for j in range(3):
                if (i, j) != (1, 1):
                    draw_carpet(surface, x + i * w, y + j * h, w, h, level - 1)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    x = np.linspace(0, L, WIDTH)
    y = np.linspace(0, L, HEIGHT)
    x, y = np.meshgrid(x, y)
    wavefunction = Wavefunction(x, y)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BLACK)

        # Draw Sierpiński carpet boundary
        draw_carpet(screen, 0, 0, WIDTH, HEIGHT, LEVELS)

        # Evolve and draw wavefunction
        wavefunction.evolve()
        probability_density = wavefunction.calculate_probability_density()
        heatmap = np.uint8(255 * probability_density / np.max(probability_density))
        surf = pygame.surfarray.make_surface(heatmap)
        surf = pygame.transform.flip(surf, False, True)
        screen.blit(surf, (0, 0))

        # Draw total energy tracker
        total_energy = wavefunction.get_total_energy()
        font = pygame.font.Font(None, 36)
        text = font.render(f"Total Energy: {total_energy:.2f}", True, WHITE)
        screen.blit(text, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
