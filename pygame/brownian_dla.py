import sys
import math
import time
import random
import imageio
import pygame
import pymunk

# Constants
WIDTH, HEIGHT = 800, 600  # Simulation dimensions in pixels (microns)
RADIUS = 3 # Particle radius in pixels (microns)
MASS = 1e-15  # Particle mass in kg
MOMENT = 1666  # Uniform moment of inertia in kg*pixel^2 (kg*micron^2)
DT = 1 / 60  # Time step in seconds
D = 1  # Diffusion coefficient in micron^2/s

# Adjustable simulation parameters
BROWNIAN_INTENSITY = 1  # Scaling factor for Brownian noise intensity
SPAWN_RATE = 0.15  # Probability per frame of spawning a new particle
SPEED_MULTIPLIER = 20  # Multiplier for animation speed (proportionally affects mp4 output length)
SIM_DURATION = 60  # Simulation duration in seconds

# Colors for visualization
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Collision types
COLL_TYPE_PARTICLE = 2  # Identifier for dynamic particles (free, Brownian motion)
COLL_TYPE_CLUSTER = 3  # Identifier for static particles that have adhered to the cluster

# Force scaling factor
NOISE_STRENGTH = MASS * math.sqrt(2 * D / DT) * BROWNIAN_INTENSITY

class Particle:
    """
    Represents a particle in the simulation.

    Attributes:
        body: Pymunk body representing the particle's dynamics.
        shape: Pymunk shape associated with the particle.
        adhesion_order: Order in which the particle adhered to the cluster.
    """

    def __init__(self, body, shape):
        self.body = body
        self.shape = shape
        self.adhesion_order = None

class Cluster:
    """
    Represents the aggregated cluster of adhered particles and the order they adhered.

    Attributes:
        central_body: The central nucleation site (first cluster particle)
        adhered_particles: List of Particle instances that have adhered
    """

    def __init__(self, central_body):
        self.central_body = central_body
        self.adhered_particles = []

    def add_particle(self, particle):
        """
        Add a particle to the cluster and record its adhesion order.

        :param particle: Particle instance to add.
        """
        particle.adhesion_order = len(self.adhered_particles)
        self.adhered_particles.append(particle)

    def get_gradient_color(self, particle):
        """
        Compute the gradient color for a given particle in the cluster.
        The oldest particle is blue and the newest is red.

        :param particle: Particle instance from the cluster.
        :return: Tuple representing an RGB color.
        """
        n = len(self.adhered_particles)

        # Avoid division by zero when there's only one particle
        t = particle.adhesion_order / (n - 1) if n > 1 else 0

        # Linear interpolation: oldest (t=0) is blue (0,0,255), newest (t=1) is red (255,0,0)
        r = int(255 * t)
        g = 0
        b = int(255 * (1 - t))
        return r, g, b

def create_particle():
    """Spawn a new dynamic particle along a random boundary, ensuring it is fully within bounds."""

    # Choose a random boundary side and compute spawn coordinates.
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        x = random.randint(RADIUS, WIDTH - RADIUS)
        y = RADIUS
    elif side == "bottom":
        x = random.randint(RADIUS, WIDTH - RADIUS)
        y = HEIGHT - RADIUS
    elif side == "left":
        x = RADIUS
        y = random.randint(RADIUS, HEIGHT - RADIUS)
    elif side == "right":
        x = WIDTH - RADIUS
        y = random.randint(RADIUS, HEIGHT - RADIUS)

    # Create a new dynamic body for the particle
    body = pymunk.Body(mass=MASS, moment=MOMENT)
    body.position = (x, y)
    body.velocity = (0, 0)  # Start with zero velocity; Brownian force drives motion

    # Create a circular shape for the body
    shape = pymunk.Circle(body, RADIUS)
    shape.elasticity = 1
    shape.friction = 0
    shape.collision_type = COLL_TYPE_PARTICLE
    space.add(body, shape)
    particle = Particle(body, shape)
    dynamic_particles.append(particle)

def initialize_space():
    """
    Initialize the Pymunk simulation space with boundary walls and a central nucleation site.

    :return: The initialized central cluster body.
    """

    # Initialize zero gravity
    space.gravity = (0, 0)

    # Define boundary walls
    walls = [
        pymunk.Segment(space.static_body, (0, 0), (0, HEIGHT), 1),
        pymunk.Segment(space.static_body, (WIDTH, 0), (WIDTH, HEIGHT), 1),
        pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 1),
        pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 1)
    ]
    for wall in walls:
        wall.elasticity = 1
        wall.friction = 0
    space.add(*walls)

    # Create central nucleation site
    cluster_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    cluster_body.position = (WIDTH // 2, HEIGHT // 2)
    cluster_shape = pymunk.Circle(cluster_body, RADIUS)
    cluster_shape.elasticity = 0
    cluster_shape.friction = 1
    cluster_shape.collision_type = COLL_TYPE_CLUSTER
    space.add(cluster_body, cluster_shape)

    # Initialize the cluster with the central seed as the first, oldest particle
    return cluster_body

def apply_brownian_force(body):
    """
    Apply a stochastic force to a dynamic body to simulate Brownian motion

    :param body: Pymunk body receiving the force.
    """
    fx = random.gauss(0, NOISE_STRENGTH)
    fy = random.gauss(0, NOISE_STRENGTH)
    body.apply_force_at_local_point((fx, fy))

def stick_particle(arbiter, space, _):
    """
    Collision callback that causes a particle to stick to the cluster.

    :param space: Pymunk simulation space.
    :param arbiter: Collision details.
    :param _: Unused additional data.
    """
    shape = (arbiter.shapes[0] if arbiter.shapes[0].collision_type == COLL_TYPE_PARTICLE
             else arbiter.shapes[1])
    space.add_post_step_callback(post_step_stick, shape)
    return True

def post_step_stick(space, shape):
    """
    Convert a dynamic particle into a static one upon adhesion to the cluster

    :param shape: Particle shape that has collided.
    """

    # Find the Particle instance corresponding to the given shape.
    for particle in dynamic_particles:
        if particle.shape == shape:
            dynamic_particles.remove(particle)
            particle.body.body_type = pymunk.Body.STATIC
            particle.shape.collision_type = COLL_TYPE_CLUSTER
            space.reindex_shape(particle.shape)
            cluster.add_particle(particle)
            break

def process_frame():
    """Process a single simulation frame"""

    # Clear the screen
    screen.fill(WHITE)

    # Spawn new particles based on SPAWN_RATE
    if random.random() < SPAWN_RATE:
        create_particle()

    # Render the central cluster (nucleation site)
    pygame.draw.circle(screen, BLUE, (int(cluster.central_body.position.x),
                                      int(cluster.central_body.position.y)), RADIUS)

    # Update and render dynamic particles (drawn in red).
    for particle in dynamic_particles:
        if particle.body.body_type == pymunk.Body.DYNAMIC:
            apply_brownian_force(particle.body)
        pygame.draw.circle(screen, RED, (int(particle.body.position.x),
                                         int(particle.body.position.y)), RADIUS)

    # Render cluster particles with gradient colors based on recency.
    for particle in cluster.adhered_particles:
        color = cluster.get_gradient_color(particle)
        pygame.draw.circle(screen, color, (int(particle.body.position.x),
                                           int(particle.body.position.y)), RADIUS)

    # Update the full display surface to the screen.
    pygame.display.flip()

    # Capture the current frame for the output video.
    frame = pygame.surfarray.array3d(screen)
    frames.append(frame)

def main():
    # Global variables for simulation objects
    global cluster, dynamic_particles, frames, screen, space
    dynamic_particles = []  # List to hold Particle instances that are still dynamic
    frames = []  # Frames for output video

    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Initialize the central nucleation site and create the initial Cluster.
    space = pymunk.Space()
    central_body = initialize_space()
    cluster = Cluster(central_body)

    # Set up collision handler for dynamic particles colliding with the cluster.
    h = space.add_collision_handler(COLL_TYPE_PARTICLE, COLL_TYPE_CLUSTER)
    h.begin = stick_particle

    # Simulation loop
    start_time = time.time()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        process_frame()

        clock.tick(60*SPEED_MULTIPLIER)
        space.step(DT)

        # Stop simulation after SIM_DURATION seconds.
        if time.time() - start_time > SIM_DURATION:
            running = False

    # Close the simulation, save the animation as a mp4 video, then exit
    pygame.quit()
    imageio.mimsave('dla_simulation.mp4', frames, fps=60, codec='libx264')
    sys.exit(0)

if __name__ == "__main__":
    main()
