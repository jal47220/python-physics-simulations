import numpy as np
import pygame
import cv2

# Constants
WIDTH, HEIGHT = 800, 600        # Window dimensions in pixels
PARTICLE_SIZE = 5               # Radius of gas particles
PARTICLE_COUNT = 100            # Number of particles in the simulation
LENGTH_CHANGE = 10              # Change distance for boundaries in pixels
GAS_CONSTANT = 1                # Simplified gas constant for calculations
CELL_SIZE = PARTICLE_SIZE * 2   # Each cell is at least as big as a particle's diameter

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)

class Particle:
    """
    Represents a gas particle in the simulation, including movement and wall collisions.

    Attributes:
        x (float): Current x-position.
        y (float): Current y-position.
        vx (float): Current x-velocity.
        vy (float): Current y-velocity.
        radius (float): Particle radius.
        mass (float): Mass of the particle.
        color (tuple): RGB color of the particle.
        cell_x (int): x-index in spatial grid.
        cell_y (int): y-index in spatial grid.
    """

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = PARTICLE_SIZE
        self.mass = 1.0
        self.color = self.get_color()
        self.cell_x = int(x // CELL_SIZE)
        self.cell_y = int(y // CELL_SIZE)

    def get_color(self):
        """Calculate particle color based on speed (red=fast, blue=slow)"""
        speed = np.sqrt(self.vx ** 2 + self.vy ** 2)
        return (int(min(speed * 25.5, 255)), 0, max(0, int(255 - speed * 25.5)))

    def update(self, width, height):
        """
        Update the particle's position and handle collisions with container walls.

        Parameters:
            width (float): Width of the container.
            height (float): Height of the container.

        Returns:
            bool: True if a wall collision occurred, False otherwise.
        """

        # Update position based on velocity
        self.x += self.vx
        self.y += self.vy

        # Wall collisions - horizontal
        collision = False
        if self.x - self.radius < 0:
            self.vx = abs(self.vx)  # Reflect off left wall
            self.x = self.radius  # Prevent sticking in wall
            collision = True
        elif self.x + self.radius > width:
            self.vx = -abs(self.vx)  # Reflect off right wall
            self.x = width - self.radius  # Prevent sticking in wall
            collision = True

        # Wall collisions - vertical
        if self.y - self.radius < 0:
            self.vy = abs(self.vy)  # Reflect off top wall
            self.y = self.radius  # Prevent sticking in wall
            collision = True
        elif self.y + self.radius > height:
            self.vy = -abs(self.vy)  # Reflect off bottom wall
            self.y = height - self.radius  # Prevent sticking in wall
            collision = True

        # Update grid cell position
        new_cell_x = int(self.x // CELL_SIZE)
        new_cell_y = int(self.y // CELL_SIZE)
        if new_cell_x != self.cell_x or new_cell_y != self.cell_y:
            self.cell_x = new_cell_x
            self.cell_y = new_cell_y

        # Update color based on new velocity
        self.color = self.get_color()
        return collision

class SpatialGrid:
    """
    Grid-based spatial partitioning to efficiently find potential collision pairs

    Attributes:
        cell_size (float): The size of each grid cell.
        cols (int): Number of columns in the grid.
        rows (int): Number of rows in the grid.
        grid (list): 2D list storing particles in each cell.
    """

    def __init__(self, width, height):
        self.cell_size = CELL_SIZE
        self.cols = int(width // self.cell_size) + 1
        self.rows = int(height // self.cell_size) + 1
        self.grid = [[[] for _ in range(self.rows)] for _ in range(self.cols)]

    def clear(self):
        """Clear the grid for the next update"""
        for col in range(self.cols):
            for row in range(self.rows):
                self.grid[col][row] = []

    def insert(self, particle):
        """Insert a particle into the appropriate grid cell"""
        col = min(max(0, int(particle.x // self.cell_size)), self.cols - 1)
        row = min(max(0, int(particle.y // self.cell_size)), self.rows - 1)
        self.grid[col][row].append(particle)

    def get_potential_collisions(self, particle):
        """
        Get list of particles that could potentially collide with the given particle
        by checking its own cell and adjacent cells
        """
        potential_collisions = []
        col = min(max(0, int(particle.x // self.cell_size)), self.cols - 1)
        row = min(max(0, int(particle.y // self.cell_size)), self.rows - 1)

        # Check neighboring cells (including diagonal neighbors and own cell)
        for i in range(max(0, col - 1), min(col + 2, self.cols)):
            for j in range(max(0, row - 1), min(row + 2, self.rows)):
                potential_collisions.extend(self.grid[i][j])

        return potential_collisions

def check_particle_collision(p1, p2):
    """
    Check and resolve elastic collision between two particles.

    Parameters:
        p1 (Particle): The first particle.
        p2 (Particle): The second particle.

    Returns:
        bool: True if a collision occurred, False otherwise.
    """
    # Skip if same particle
    if p1 is p2:
        return False

    # Calculate distance between particles
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    distance = np.sqrt(dx ** 2 + dy ** 2)

    # Check if particles are colliding
    if distance < p1.radius + p2.radius:
        # Calculate normal vector (direction from p1 to p2)
        nx = dx / distance
        ny = dy / distance

        # Tangent vector (perpendicular to normal)
        tx = -ny
        ty = nx

        # Relative velocity
        dvx = p2.vx - p1.vx
        dvy = p2.vy - p1.vy

        # Project relative velocity onto normal
        normal_vel = dvx * nx + dvy * ny

        # Only resolve collision if particles are moving toward each other
        if normal_vel >= 0:
            return False

        # Extract masses for calculation
        m1, m2 = p1.mass, p2.mass

        # Calculate normal velocities after collision using conservation of momentum and kinetic energy
        v1n = ((m1 - m2) * (p1.vx * nx + p1.vy * ny) + 2 * m2 * (p2.vx * nx + p2.vy * ny)) / (m1 + m2)
        v2n = ((m2 - m1) * (p2.vx * nx + p2.vy * ny) + 2 * m1 * (p1.vx * nx + p1.vy * ny)) / (m1 + m2)

        # Project current velocities to tangent direction (these don't change in collision)
        v1t = p1.vx * tx + p1.vy * ty
        v2t = p2.vx * tx + p2.vy * ty

        # Convert back to x,y coordinates
        p1.vx = v1n * nx + v1t * tx
        p1.vy = v1n * ny + v1t * ty
        p2.vx = v2n * nx + v2t * tx
        p2.vy = v2n * ny + v2t * ty

        # Slightly separate particles to prevent sticking
        overlap = p1.radius + p2.radius - distance
        if overlap > 0:
            p1.x -= 0.5 * overlap * nx
            p1.y -= 0.5 * overlap * ny
            p2.x += 0.5 * overlap * nx
            p2.y += 0.5 * overlap * ny

        return True
    return False

class Simulation:
    """
    Manages the ideal gas simulation including particles, collisions, and gas properties.

    Attributes:
        width (float): Current container width.
        height (float): Current container height.
        particles (list): List of Particle objects.
        spatial_grid (SpatialGrid): Grid for collision detection.
        volume (float): Container area.
        pressure (float): Calculated pressure.
        temperature (float): Calculated temperature.
        collision_count (int): Count of wall collisions for pressure calculation.
        time_elapsed (float): Time elapsed since last pressure update.
    """
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Initialize particles with random positions and velocities
        self.particles = [Particle(np.random.uniform(PARTICLE_SIZE, width - PARTICLE_SIZE),
                                   np.random.uniform(PARTICLE_SIZE, height - PARTICLE_SIZE),
                                   np.random.uniform(-5, 5),
                                   np.random.uniform(-5, 5))
                          for _ in range(PARTICLE_COUNT)]

        # Create spatial grid for efficient collision detection
        self.spatial_grid = SpatialGrid(width, height)

        # Physical properties
        self.volume = width * height
        self.pressure = 0
        self.temperature = 0

        # Tracking variables
        self.collision_count = 0
        self.time_elapsed = 0

    def update(self, dt):
        """
        Update the simulation state for a time step.

        Parameters:
            dt (float): Time step in seconds.
        """
        self.time_elapsed += dt
        wall_collisions = 0

        # Update particles and count wall collisions
        for particle in self.particles:
            if particle.update(self.width, self.height):
                wall_collisions += 1

        # Clear and rebuild spatial grid
        self.spatial_grid = SpatialGrid(self.width, self.height)
        for particle in self.particles:
            self.spatial_grid.insert(particle)

        # Check for and handle particle-particle collisions using spatial grid
        for particle in self.particles:
            potential_collisions = self.spatial_grid.get_potential_collisions(particle)
            for other in potential_collisions:
                check_particle_collision(particle, other)

        # Track collisions for pressure calculation
        self.collision_count += wall_collisions

        # Update pressure every second
        if self.time_elapsed >= 1.0:
            # Pressure is proportional to collision frequency and momentum transfer
            self.pressure = self.collision_count / (self.time_elapsed * self.width * self.height) * 1e3
            self.collision_count = 0
            self.time_elapsed = 0

        # Calculate temperature using ideal gas law: PV = nRT
        self.temperature = (self.pressure * self.volume) / (PARTICLE_COUNT * GAS_CONSTANT)

    def resize(self, width, height):
        """
        Resize the simulation container and scale particle positions accordingly.

        Parameters:
            width (float): New container width (meters).
            height (float): New container height (meters).
        """
        old_width = self.width
        old_height = self.height

        # Update dimensions
        self.width = width
        self.height = height
        self.volume = width * height

        # Scale particle positions to new dimensions
        for particle in self.particles:
            # Scale positions proportionally while ensuring particles stay within bounds
            particle.x = min(max(particle.x * (width / old_width), particle.radius), width - particle.radius)
            particle.y = min(max(particle.y * (height / old_height), particle.radius), height - particle.radius)

            # Update grid cell position
            particle.cell_x = int(particle.x // CELL_SIZE)
            particle.cell_y = int(particle.y // CELL_SIZE)

def draw_text(screen, text, x, y):
    """Render text on the screen at position (x, y)."""
    font = pygame.font.Font(None, 36)
    text_surface = font.render(text, True, WHITE)
    screen.blit(text_surface, (x, y))

def capture_frame(screen, out):
    """Capture the current screen frame for video recording."""
    frame = pygame.image.tostring(screen, 'RGB')
    frame = np.frombuffer(frame, dtype=np.uint8)
    frame = frame.reshape((HEIGHT, WIDTH, 3))
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    out.write(frame)

def main():
    pygame.init()
    window_width, window_height = WIDTH, HEIGHT
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Ideal Gas Simulation")
    clock = pygame.time.Clock()

    # Create simulation with initial box size
    box_width, box_height = WIDTH - 100, HEIGHT - 100
    simulation = Simulation(box_width, box_height)

    # Video recording setup
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('T4_IDealGasLaw_edit.mp4', fourcc, 60.0, (WIDTH, HEIGHT))

    # Main game loop
    running = True
    while running:
        dt = clock.tick(60) / 1e3  # Time in seconds (convert from milliseconds)

        # Handle quit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Handle volume control with arrow keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and box_width > 100:
            box_width -= LENGTH_CHANGE
            simulation.resize(box_width, box_height)
        elif keys[pygame.K_RIGHT] and box_width < window_width - 50:
            box_width += LENGTH_CHANGE
            simulation.resize(box_width, box_height)
        elif keys[pygame.K_UP] and box_height > 100:
            box_height -= LENGTH_CHANGE
            simulation.resize(box_width, box_height)
        elif keys[pygame.K_DOWN] and box_height < window_height - 50:
            box_height += LENGTH_CHANGE
            simulation.resize(box_width, box_height)

        # Update simulation physics
        simulation.update(dt)

        # ---- Drawing ----
        screen.fill(BLACK)

        # Draw container box
        box_x = (window_width - box_width) // 2
        box_y = (window_height - box_height) // 2 + 50  # Offset to avoid text overlay
        pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height), 2)

        # Draw particles
        for particle in simulation.particles:
            pygame.draw.circle(screen, particle.color,
                               (int(particle.x + box_x), int(particle.y + box_y)),
                               PARTICLE_SIZE)

        # Draw stats
        draw_text(screen, f"Pressure: {simulation.pressure:.2f}", 10, 10)
        draw_text(screen, f"Temperature: {simulation.temperature:.2f}", 10, 50)
        draw_text(screen, "Use arrow keys to change volume", window_width - 400, 10)

        # Update display and record video frame
        pygame.display.flip()
        capture_frame(screen, out)

    # Clean up and exit
    out.release()
    pygame.quit()

if __name__ == "__main__":
    main()
