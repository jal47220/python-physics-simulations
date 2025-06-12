import tkinter as tk
import numpy as np
import random
import math

# Window constants
WIDTH = 800
HEIGHT = 600

# Chimney constants
CHIMNEY_HEIGHT = 50
CHIMNEY_WIDTH = 10
CHIMNEY_X = WIDTH // 2
CHIMNEY_Y = HEIGHT - CHIMNEY_HEIGHT

# Smoke constants
MAX_AGE = 150                           # Number of frames over which particles fully disperse
SMOKE_RISE_SPEED = 2                    # Buoyant rise speed of smoke particles in px/frame
DIFFUSION_STDDEV = 0.5                  # Diffusion coefficient for random dispersion in px/frame
RADIUS = 2                              # Particle radius in px

# Wind constants
WIND_SPEED_MEAN = 1                     # Mean wind speed in px/frame
WIND_SPEED_STDDEV = 0.5                 # Standard deviation of wind speed fluctuations
WIND_DIRECTION_MEAN = math.pi / 4       # Mean wind direction in radians
WIND_DIRECTION_STDDEV = math.pi / 3     # Standard deviation of wind direction fluctuations
ORIENTATION_FLIP_CHANCE = 0.005         # Probability of wind reversing direction each frame


class WindField:
    """
    Simulates a spatially uniform 2D wind field with stochastic fluctuations.

    Attributes:
            speed (float):Current wind speed in pixels per frame.
            direction (float): Current wind direction in radians.
            orientation (int): Current wind direction orientation (+1 for right-orientation,
                               -1 for left-orientation).
    """
    def __init__(self) -> None:
        """Initializes the wind field to its mean speed and direction with random orientation."""
        self.speed = WIND_SPEED_MEAN
        self.direction = WIND_DIRECTION_MEAN
        self.orientation = random.choice((1, -1))

    def update(self) -> None:
        """
        Advances the wind field by one time step.

        Occasionally flips the wind field orientation, then re-samples speed and direction around
        their respective means with specified variability.
        """
        # Occasional flip between left and right
        if random.random() < ORIENTATION_FLIP_CHANCE:
            self.orientation *= -1

        # Fluctuate wind speed and direction around mean
        self.speed = random.gauss(WIND_SPEED_MEAN, WIND_SPEED_STDDEV)
        self.direction = ((0 if self.orientation == 1 else math.pi) +
                          random.uniform(-WIND_DIRECTION_STDDEV, WIND_DIRECTION_STDDEV))


class SmokeParticles:
    """Manages a collection of smoke particles for a 2D simulation."""
    def __init__(self):
        """Initialize empty parameter lists for new particles."""
        self.x_positions = []
        self.y_positions = []
        self.ages = []

    def spawn(self, x: float, y: float) -> None:
        """
        Create a new smoke particle at a given location.

        Args:
            x (float): Initial x-coordinate of the particle.
            y (float): Initial y-coordinate of the particle.
        """
        self.x_positions.append(x)
        self.y_positions.append(y)
        self.ages.append(0)

    def update(self, wind: WindField) -> None:
        """
        Advance particles one frame, applying physics and culling old or out-of-bounds particles.

        Args:
            wind (WindField): Current wind conditions for advection.
        """
        # Convert list to array for vectorized operation and age particles
        x_positions_array = np.array(self.x_positions, dtype=float)
        y_positions_array = np.array(self.y_positions, dtype=float)
        ages_array = np.array(self.ages, dtype=int)
        ages_array += 1

        # Rise due to buoyancy
        y_positions_array -= SMOKE_RISE_SPEED

        # Advection by wind field
        x_positions_array += wind.speed * math.cos(wind.direction)
        y_positions_array += wind.speed * math.sin(wind.direction)

        # Diffusion via random dispersion
        x_positions_array += np.random.normal(0, DIFFUSION_STDDEV,
                                             x_positions_array.shape)
        y_positions_array += np.random.normal(0, DIFFUSION_STDDEV,
                                             y_positions_array.shape)

        # Remove off-screen particles
        mask = (y_positions_array >= 0) & (ages_array < MAX_AGE)
        self.x_positions = x_positions_array[mask].tolist()
        self.y_positions = y_positions_array[mask].tolist()
        self.ages = ages_array[mask].tolist()

    def draw(self, canvas: tk.Canvas) -> None:
        """
        Render all smoke particles onto the given Tkinter canvas.

        Args:
            canvas (tk.Canvas): Canvas to draw particles on.
        """
        # Get and parse the canvas background color
        bg_color = canvas.cget('bg')
        r16, g16, b16 = canvas.winfo_rgb(bg_color)
        bg_rgb = (r16 // 256, g16 // 256, b16 // 256)
        for x, y, age in zip(self.x_positions, self.y_positions, self.ages):
            ratio = min(age / MAX_AGE, 1.0)

            # Linearly interpolate each channel, then draw
            r = int(bg_rgb[0] * ratio)
            g = int(bg_rgb[1] * ratio)
            b = int(bg_rgb[2] * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_oval(x - RADIUS, y - RADIUS, x + RADIUS, y + RADIUS,
                               fill=color, outline='', tags='smoke')


class Simulation:
    """
    Encapsulates the Tkinter GUI and orchestrates wind, particles, and rendering.

    Attributes:
        master (tk.Tk): The root Tkinter application window.
        canvas (tk.Canvas): Drawing surface for rendering smoke and chimney.
        wind (WindField): Current wind field for particle advection.
        particles (SmokeParticles): Container managing smoke particle states.
        chimney (int): Canvas object ID for the static chimney rectangle.
    """
    def __init__(self, master) -> None:
        """Initializes the simulation components and starts the update loop."""
        self.master = master
        self.canvas = tk.Canvas(self.master, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        self.wind = WindField()
        self.particles = SmokeParticles()
        self.chimney = self.canvas.create_rectangle(
            CHIMNEY_X - CHIMNEY_WIDTH, CHIMNEY_Y - CHIMNEY_HEIGHT,
            CHIMNEY_X + CHIMNEY_WIDTH, CHIMNEY_Y,
            fill='gray'
        )
        self.update()

    def update(self) -> None:
        """Advances the simulation by one frame."""

        # Update wind conditions
        self.wind.update()

        # Spawn three pillars of new particles along the chimney top
        for offset in (-RADIUS * 2, 0, RADIUS * 2):
            self.particles.spawn(CHIMNEY_X + offset, CHIMNEY_Y - CHIMNEY_HEIGHT)

        # Update physics
        self.particles.update(self.wind)

        # Clear previous smoke drawing, draw particles, then schedule the next frame
        self.canvas.delete('smoke')
        self.particles.draw(self.canvas)
        self.master.after(16, self.update)


root = tk.Tk()
sim = Simulation(root)
root.mainloop()
