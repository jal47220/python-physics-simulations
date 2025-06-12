import pyglet
import numpy as np

# Simulation properties
WIDTH = 800                             # Simulation window width in pixels
HEIGHT = 600                            # Simulation window height in pixels
PIXELS_TO_M = 0.0001                    # Distance conversion factor in meters per pixel
DT = 1 / 60                             # Timestep in seconds per frame

# Seawater properties
SEAWATER_TEMPERATURE = 2                # Ambient seawater temperature in °C
LIGHT_WATER = (100, 150, 255)           # Background seawater bottom color (light blue)
DARK_WATER = (0, 0, 100)                # Background seawater top color (dark blue)
THERMAL_EXPANSION_K = 2.1e-4            # Thermal expansion coefficient of seawater in 1/°C
DIFFUSION_K = 1e-6                      # Turbulent diffusion coefficient in m^2 per second
COOLING_RATE = 0.5                      # Exponential cooling rate coefficient per second

# Ground properties
GROUND_HEIGHT = 100                     # Position of the top of the ground in pixels

# Vent properties
VENT_TEMPERATURE = 300                  # Vent fluid temperature in °C
VENT_INNER_COLOR = (255, 0, 0)          # Hydrothermal vent inner color (red)
VENT_OUTER_COLOR = (200, 0, 0)          # Hydrothermal vent outer color (red)
VENT_RADIUS = 15                        # Vent radius in pixels
VENT_X = WIDTH // 2                     # Horizontal vent position in pixels
VENT_Y = 50                             # Vertical vent position in pixels

# Plume properties
DRAG_K = 20                             # Drag limiting plume speed per frame
PLUME_PARTICLE_SIZE = 5                 # Radius of each plume particle in pixels
PLUME_PARTICLE_COLOR = (255, 255, 0)    # Plume particle color (red)
PLUME_RISE_SPEED = 2                    # Base rise speed of plume particles in pixels per frame
PLUME_SPREAD_SPEED = 1                  # Horizontal spread magnitude per frame in pixels per frame
MAX_PLUME_PARTICLES = 1000              # Maximum number of active plume particles


def create_water_sprite(width, height):
    """
    Creates a sprite which displays a vertical color gradient representing water at a depth.

    Args:
        width (int): Sprite width in pixels.
        height (int): Sprite height in pixels.

    Returns:
        pyglet.sprite.Sprite: A sprite covering the window with a watery gradient.
    """
    # Build image from raw RGB data by linearly interpolating each channel
    gradient_data = bytearray()
    for y in range(height):
        temperature = y / (height - 1)
        r = int(DARK_WATER[0] * (1 - temperature) + LIGHT_WATER[0] * temperature)
        g = int(DARK_WATER[1] * (1 - temperature) + LIGHT_WATER[1] * temperature)
        b = int(DARK_WATER[2] * (1 - temperature) + LIGHT_WATER[2] * temperature)
        gradient_data.extend((r, g, b))
    image = pyglet.image.ImageData(1, height, 'RGB', bytes(gradient_data))

    # Create sprite positioned at the origin and stretch to fill the window
    sprite = pyglet.sprite.Sprite(image, x=0, y=0)
    sprite.scale_x = width
    return sprite


class Window(pyglet.window.Window):
    """
    Main application window for the hydrothermal vent simulation.

    Attributes:
        seawater_batch (pyglet.graphics.Batch): Batch for water-background sprite.
        water_sprite (pyglet.sprite.Sprite): Full-window gradient sprite.
        ground_batch (pyglet.graphics.Batch): Batch for ground rectangle.
        ground (pyglet.shapes.Rectangle): Seafloor representation.
        vent_batch (pyglet.graphics.Batch): Batch for vent graphic.
        vent (pyglet.shapes.Circle): Visual marker for vent location.
        plume_batch (pyglet.graphics.Batch): Batch for plume particles.
        plume_x_positions (np.ndarray): x-positions of active plume particles.
        plume_y_positions (np.ndarray): y-positions of active plume particles.
        plume_temperatures (np.ndarray): Temperatures of active plume particles.
        plume_vertical_velocities (np.ndarray): Vertical velocities of plume particles.
    """
    def __init__(self):
        """Initialize rendering batches and empty particle arrays."""
        super().__init__(WIDTH, HEIGHT)

        # Background water gradient sprite batch
        self.seawater_batch = pyglet.graphics.Batch()
        self.water_sprite = create_water_sprite(width=WIDTH, height=HEIGHT)

        # Seafloor ground drawn from y=0 to GROUND_HEIGHT
        self.ground_batch = pyglet.graphics.Batch()
        self.ground = pyglet.shapes.Rectangle(0, 0, WIDTH, GROUND_HEIGHT,
                                              color=(150, 125, 100), batch=self.ground_batch)

        # Centered vent graphic
        self.vent_batch = pyglet.graphics.Batch()
        self.vent = pyglet.shapes.Circle(VENT_X, VENT_Y, VENT_RADIUS,
                                         color=VENT_INNER_COLOR, batch=self.vent_batch)

        # Batch and arrays for plume particles
        self.plume_batch = pyglet.graphics.Batch()
        self.plume_particles = []
        self.plume_x_positions = np.zeros(MAX_PLUME_PARTICLES, dtype=float)
        self.plume_y_positions = np.zeros(MAX_PLUME_PARTICLES, dtype=float)
        self.plume_temperatures = np.zeros(MAX_PLUME_PARTICLES, dtype=float)
        self.plume_vertical_velocities = np.zeros(MAX_PLUME_PARTICLES, dtype=float)
        self.plume_shapes = [
            pyglet.shapes.Circle(0, 0, PLUME_PARTICLE_SIZE,
                                 color=PLUME_PARTICLE_COLOR, batch=self.plume_batch)
            for _ in range(MAX_PLUME_PARTICLES)  # one shape per possible particle
        ]
        self.plume_count = 0

    def update(self, dt):
        """
        Advances the plume simulation by one time step.

        Args:
            dt (float): Time step in seconds since last update.
        """
        # Spawn new particle if number of current particles is under the maximum count
        if self.plume_count < MAX_PLUME_PARTICLES:
            i = self.plume_count
            self.plume_x_positions[i] = VENT_X
            self.plume_y_positions[i] = VENT_Y
            self.plume_temperatures[i] = VENT_TEMPERATURE
            self.plume_vertical_velocities[i] = 0
            self.plume_count += 1

        # Apply buoyancy-driven vertical motion with linear drag
        buoyant_acceleration = ((9.81 * THERMAL_EXPANSION_K *
                                (self.plume_temperatures[:self.plume_count] -
                                 SEAWATER_TEMPERATURE)) / PIXELS_TO_M)
        self.plume_vertical_velocities[:self.plume_count] += (
                (buoyant_acceleration - DRAG_K *
                 self.plume_vertical_velocities[:self.plume_count]) * dt)
        self.plume_y_positions[:self.plume_count] += (
            self.plume_vertical_velocities[:self.plume_count] * dt
        )

        # Apply horizontal turbulent diffusion
        sigma = np.sqrt(2 * DIFFUSION_K * dt) / PIXELS_TO_M
        self.plume_x_positions[:self.plume_count] += np.random.normal(0, sigma,
                                                                      self.plume_count)

        # Apply uniform cooling and remove cooled particles via vector mask
        self.plume_temperatures[:self.plume_count] -= (COOLING_RATE *
                                                       (self.plume_temperatures[:self.plume_count] -
                                                       SEAWATER_TEMPERATURE)) * dt
        mask = self.plume_temperatures[:self.plume_count] >= SEAWATER_TEMPERATURE
        survivors = np.nonzero(mask)[0]
        for arr in (self.plume_x_positions,
                    self.plume_y_positions,
                    self.plume_vertical_velocities,
                    self.plume_temperatures):
            arr[:survivors.size] = arr[survivors]
        self.plume_count = survivors.size

    def on_draw(self):
        """Renders one frame of the simulation."""
        self.clear()

        # Draw background gradient, ground layer, and hydrothermal vent
        self.water_sprite.draw()
        self.ground_batch.draw()
        self.vent.draw()

        # Update position and opacity of each active particle
        for i in range(self.plume_count):
            shape = self.plume_shapes[i]
            shape.x = self.plume_x_positions[i]
            shape.y = self.plume_y_positions[i]

            # Set alpha based on temperature
            shape.opacity = int(
                255 * self.plume_temperatures[i] / VENT_TEMPERATURE
            )

        # Draw all particles
        self.plume_batch.draw()


# Initialize and run the simulation
if __name__ == '__main__':
    window = Window()
    pyglet.clock.schedule_interval(window.update, DT)
    pyglet.app.run()
