import numpy as np
import pyglet

# Window dimensions
WIDTH, HEIGHT = 800, 600

# Number of particles
NUM_PARTICLES = 1000

# Drain properties
DRAIN_RADIUS = 50

# Particle properties
PARTICLE_SIZE = 3
PARTICLE_SPEED = 2

# Vortex strength for tangential acceleration
VORTEX_STRENGTH = 0.0005


class Particle:
    """
    Represents a particle in the fluid vortex simulation.

    Initializes a particle with a random starting position and initial velocity within the window.
    These properties are then used to simulate fluid-like motion within the vortex.

    Attributes:
        x (float): The x-coordinate of the particle.
        y (float): The y-coordinate of the particle.
        vx (float): The velocity of the particle along the x-axis in px per frame.
        vy (float): The velocity of the particle along the y-axis in px per frame.
    """
    def __init__(self):
        self.x = np.random.uniform(0, WIDTH)
        self.y = np.random.uniform(0, HEIGHT)
        self.vx = np.random.uniform(-PARTICLE_SPEED, PARTICLE_SPEED)
        self.vy = np.random.uniform(-PARTICLE_SPEED, PARTICLE_SPEED)

    def update(self, drain_x, drain_y, drain_radius):
        """
        Updates the particle's velocity and position based on fluid dynamics.

        Applies radial acceleration toward the drain if the particle is outside the drain's radius,
        adds a tangential vortex acceleration for swirling motion, updates the particle's position
        based on its velocity, then inverts the velocity when the particle exceeds window bounds.

        Args:
            drain_x (float): The x-coordinate of the drain center.
            drain_y (float): The y-coordinate of the drain center.
            drain_radius (float): The radius of the drain in px.
        """
        dx = drain_x - self.x
        dy = drain_y - self.y
        r = np.sqrt(dx**2 + dy**2) or 1e-6  # Avoid division by zero

        # Apply vortex (ie, tangential) acceleration for swirling fluid motion around the drain
        self.vx += -VORTEX_STRENGTH * drain_radius * (self.y - drain_y) / r
        self.vy += VORTEX_STRENGTH * drain_radius * (self.x - drain_x) / r

        # Apply radial force: inward if particle is outside the drain, outward if inside
        radial_force = VORTEX_STRENGTH * (drain_radius - r)
        self.vx += radial_force * (self.x - drain_x) / r
        self.vy += radial_force * (self.y - drain_y) / r

        # Update particle positions based on current velocity
        self.x += self.vx
        self.y += self.vy


class Slider(pyglet.shapes.Rectangle):
    """
    Represents a slider widget for adjusting simulation parameters.

    Adjusts a numerical value via mouse drag events. Inherits from pyglet.shapes.Rectangle to
    utilize its drawing capabilities.

    Attributes:
        value (float): The current slider value, represented as a fraction between 0 and 1.
    """
    def __init__(self, x, y, width, height, color, batch):
        """
        Initializes the Slider widget with specified geometry and appearance.

        Args:
            x (float): The x-coordinate of the slider's position.
            y (float): The y-coordinate of the slider's position.
            width (float): The width of the slider in px.
            height (float): The height of the slider in px.
            color (tuple): The color of the slider as an (R, G, B) tuple.
            batch (pyglet.graphics.Batch): The graphics batch to which the slider will be added.
        """
        super().__init__(x, y, width, height, color, batch=batch)
        self.value = 0
        self.dragging = False

    def on_press(self, x, y):
        """
        Activates dragging if the mouse press occurs within the slider bounds.

        Args:
            x (float): The x-coordinate of the mouse press.
            y (float): The y-coordinate of the mouse press.
        """
        if self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height:
            self.dragging = True

    def on_drag(self, x, _):
        """
        Updates the slider's value based on the current drag position.

        The value is computed as the horizontal distance from the slider's starting x-coordinate,
        normalized by the slider's total width.

        Args:
            x (float): The current x-coordinate of the mouse during the drag.
            _ (float): The current y-coordinate of the mouse during the drag (unused).
        """
        if self.dragging:
            self.value = (x - self.x) / self.width

    def on_release(self, *_):
        """
        Deactivates dragging when the mouse button is released.

        Args:
            *_: The x- and y-coordinates of the mouse release (unused).
        """
        self.dragging = False


class Window(pyglet.window.Window):
    """
    Main window for the 2D fluid vortex simulation.

    Manages the simulation, rendering, and updates for the vortex simulation. Initializes and
    maintains a list of particles, sets up the drain properties at the center of the window,
    and creates a slider widget for adjusting the drain radius.

    Attributes:
        particles (list[Particle]): List of particles in the simulation.
        drain_x (int): The x-coordinate of the drain center.
        drain_y (int): The y-coordinate of the drain center.
        drain_radius (int): The current radius of the drain in px.
        slider (Slider): The slider widget for adjusting the drain radius.
    """
    def __init__(self):
        super().__init__(WIDTH, HEIGHT)
        self.particles = [Particle() for _ in range(NUM_PARTICLES)]
        self.drain_x = WIDTH // 2
        self.drain_y = HEIGHT // 2
        self.drain_radius = DRAIN_RADIUS
        self.slider = Slider(10, 10, 200, 20, (255, 255, 255), batch=None)
        self.slider.opacity = 100

    def on_draw(self):
        """
        Renders the simulation frame.

        Clears the window and draws all simulation elements, including:
        - Each particle as a line segment with color interpolated based on distance from the drain.
        - The drain as a red circle.
        - The slider for adjusting the drain radius.
        """
        self.clear()

        # Draw the drain as a red circle
        pyglet.shapes.Circle(self.drain_x, self.drain_y, self.drain_radius, color=(255, 0, 0)).draw()

        # Vectorize computation of particle positions and velocities
        positions = np.array([[p.x, p.y] for p in self.particles])  # Shape: (n, 2)
        velocities = np.array([[p.vx, p.vy] for p in self.particles])  # Shape: (n, 2)
        end_positions = positions - velocities * 3  # Scale velocities to compute end positions

        # Compute distances from the drain center
        dx = positions[:, 0] - self.drain_x
        dy = positions[:, 1] - self.drain_y
        distances = np.sqrt(dx**2 + dy**2)
        ratio = distances / (WIDTH / 2)
        ratio = np.minimum(1, ratio)  # Clamp ratio to a maximum of 1

        # Compute color components
        red = (255 * (1 - ratio) + 100 * ratio).astype(np.int32)
        blue = (100 * (1 - ratio) + 255 * ratio).astype(np.int32)

        # Draw each particle as a line using the vectorized computed values
        for pos, end, r, b in zip(positions, end_positions, red, blue):
            color = (int(r), 100, int(b))  # Constant green value of 100 for contrast
            pyglet.shapes.Line(pos[0], pos[1], end[0], end[1], thickness=2, color=color).draw()

        # Draw the slider for drain radius adjustment
        self.slider.draw()

    def update(self, _):
        """
        Updates the simulation state for each frame.

        Each particle's state is updated using the current drain properties. Then, the drain
        radius is adjusted based on the slider's value.

        Args:
            _ (float): Delta time since the last update (ignored).
        """
        for particle in self.particles:
            particle.update(self.drain_x, self.drain_y, self.drain_radius)
        self.drain_radius = DRAIN_RADIUS + self.slider.value * 100

    def on_mouse_press(self, x, y, *_):
        """
        Handles mouse press events to potentially activate slider dragging.

        Args:
            x (float): The x-coordinate of the mouse press.
            y (float): The y-coordinate of the mouse press.
            *_: Additional arguments provided by the event that are ignored.
        """
        self.slider.on_press(x, y)

    def on_mouse_drag(self, x, y, *_):
        """
        Handles mouse drag events to update the slider's value.

        Updates the slider's value based on the current mouse position during a drag event.
        Additional arguments are ignored in this implementation.

        Args:
            x (float): The current x-coordinate of the mouse.
            y (float): The current y-coordinate of the mouse.
            *_: Additional arguments provided by the event that are ignored.
        """
        self.slider.on_drag(x, y)

    def on_mouse_release(self, x, y, *_):
        """
        Handles mouse release events to deactivate slider dragging.

        Args:
            x (float): The x-coordinate of the mouse release.
            y (float): The y-coordinate of the mouse release.
            *_: Additional arguments provided by the event that are ignored.
        """
        self.slider.on_release(x, y)


if __name__ == "__main__":
    window = Window()
    pyglet.clock.schedule_interval(window.update, 1/60)
    pyglet.app.run()
