import tkinter as tk
import random
import time

# Window and spatial conversion constants
WIDTH, HEIGHT = 800, 600                    # Window dimensions in pixels
PPM = 40                                    # Spatial scale; e.g., 40 pixels represent 1 meter

# Ground constants
GROUND_HEIGHT_METERS = 1.2                  # Visual height of snowy ground in meters
GROUND_HEIGHT = GROUND_HEIGHT_METERS * PPM  # Visual height of snowy ground in pixels
GROUND_LEVEL = HEIGHT - GROUND_HEIGHT       # Top of ground x-value in pixels

# Fence constants
FENCE_X = WIDTH // 2                        # Bottom of fence x-value in pixels (e.g., middle of screen)
FENCE_HEIGHT_METERS = 2                     # Fence height in meters
FENCE_HEIGHT = FENCE_HEIGHT_METERS * PPM    # Fence height in pixels
FENCE_Y = HEIGHT - GROUND_HEIGHT            # Bottom of fence y-value in pixels
FENCE_WIDTH_METERS = 0.25                   # Fence width in meters
FENCE_WIDTH = FENCE_WIDTH_METERS * PPM      # Fence width in pixels
FENCE_LEFT = FENCE_X - FENCE_WIDTH / 2      # Left of fence x-value in pixels
FENCE_RIGHT = FENCE_X + FENCE_WIDTH / 2     # Right of fence x-value in pixels
ACCUMULATION_ZONE_WIDTH = 50                # Width of the drift zone in pixels

# Snowflake constants
SNOWFLAKE_SIZE = 3                          # Snowflake radius in pixels
SNOWFALL_RATE = 10                          # Number of snowflakes generated per frame
MAX_SLOPE = 1                               # Max height difference between adjacent pixels, in pixels

# Physics constants
INITIAL_VX_VARIATION = 0.5                  # Initial horizontal speed variation for snowflakes in meters per second
CONTINUOUS_VX_FLUTTER = 0.2                 # Max random change to horizontal speed due to fluttering per time step
HORIZONTAL_DRIFT_FLUTTER = 0.3              # Max sideways drift speed component in meters per second
WIND_SPEED = 3                              # Average wind speed in meters per second
GRAVITY = 9.81                              # Acceleration due to gravity in meters per second^2
DT = 0.1                                    # Physics time step in seconds


class Snowflake:
    """
    Represents a single particle in the simulation.

    Manages the state and physics of an individual particle, including its position, velocity, and
    interaction with the environment.

    Attributes:
        canvas (tk.Canvas): The Tkinter canvas object where the particle is drawn.
        id (int): The unique identifier for the particle's canvas object.
        sim (SnowDriftSimulation): A reference to the main simulation instance.
        landed (bool): True if the particle has hit a surface and stopped moving.
        x (float): The current horizontal position of the particle, in pixels.
        y (float): The current vertical position of the particle, in pixels.
        vx (float): The current horizontal velocity in meters per second.
        vy (float): The current vertical velocity in meters per second.
    """
    def __init__(self, canvas, x, y, sim):
        """
        Initializes a Snowflake instance.

        Args:
            canvas (tk.Canvas): The canvas object for drawing the particle.
            x (float): The initial horizontal position of the particle in pixels.
            y (float): The initial vertical position of the particle in pixels.
            sim (SnowDriftSimulation): A reference to the main simulation instance
                to access shared data like the height map.
        """
        self.canvas = canvas
        self.id = self.canvas.create_oval(x, y, x + SNOWFLAKE_SIZE, y + SNOWFLAKE_SIZE, fill='white', outline='')
        self.sim = sim

        # Positional values
        self.landed = False
        self.x = x
        self.y = y
        self.vx = WIND_SPEED + random.uniform(-INITIAL_VX_VARIATION, INITIAL_VX_VARIATION)
        self.vy = random.uniform(0.1, 0.5)

    def move(self):
        """Advances the particle's state by a single simulation time step."""
        if self.landed:
            return

        # Apply wind and gravity
        self.vx += random.uniform(-CONTINUOUS_VX_FLUTTER, CONTINUOUS_VX_FLUTTER) * DT  # Wind variation
        self.vy += GRAVITY * DT

        # Apply displacement from velocity
        self.x += self.vx * PPM * DT
        self.y += self.vy * PPM * DT

        # Drift effect - sideways movement influenced by wind
        self.x += random.uniform(-HORIZONTAL_DRIFT_FLUTTER, HORIZONTAL_DRIFT_FLUTTER) * PPM * DT

        # Handle fence collision
        if self.y + SNOWFLAKE_SIZE > (FENCE_Y - FENCE_HEIGHT) and self.y < FENCE_Y:
            # If moving right into the fence
            if self.vx > 0 and self.x + SNOWFLAKE_SIZE >= FENCE_LEFT > self.x:
                self.x = FENCE_LEFT - SNOWFLAKE_SIZE
                self.vx = 0

            # If moving left into the fence
            elif self.vx < 0 and self.x <= FENCE_RIGHT < self.x + SNOWFLAKE_SIZE:
                self.x = FENCE_RIGHT
                self.vx = 0

        # Determine the landing surface across the snowflake's full width
        start_check_x = max(0, int(self.x))
        end_check_x = min(WIDTH, int(self.x + SNOWFLAKE_SIZE))

        # Handle landing on the ground or on top of other grounded snowflakes
        if end_check_x > start_check_x:
            # Find the highest point of snow (lowest Y value) under the flake
            highest_surface_y = min(self.sim.snow_heights[start_check_x:end_check_x])

            # Check if the snowflake's bottom hits this surface
            if self.y + SNOWFLAKE_SIZE >= highest_surface_y:
                self.landed = True

                # Check if the snowflake is in the accumulation zone
                if FENCE_LEFT - ACCUMULATION_ZONE_WIDTH < self.x < FENCE_LEFT:
                    # Update the snow surface height over the snowflake's full width
                    for i in range(start_check_x, end_check_x):
                        self.sim.snow_heights[i] = min(self.sim.snow_heights[i], highest_surface_y - SNOWFLAKE_SIZE)

                    # Mark that accumulation pile needs to be updated
                    self.sim.drift_updated = True

        if not self.landed:
            self.canvas.coords(self.id, self.x, self.y, self.x + SNOWFLAKE_SIZE, self.y + SNOWFLAKE_SIZE)


class Fence:
    """
    Represents the fence obstacle in the simulation.

    Attributes:
        canvas (tk.Canvas): The Tkinter canvas on which the fence is drawn.
        id (int): The unique identifier for the fence's canvas object.
    """
    def __init__(self, canvas):
        """
        Initializes the Fence and draws it on the canvas.

        Args:
            canvas (tk.Canvas): The canvas widget to draw the fence on.
        """
        self.canvas = canvas
        self.id = self.canvas.create_rectangle(FENCE_LEFT, FENCE_Y,
                                              FENCE_RIGHT, FENCE_Y - FENCE_HEIGHT,
                                              fill='brown', outline='')


class SnowDriftSimulation:
    """
    Manages the overall simulation, canvas, game loop, and particles.

    Attributes:
        root (tk.Tk): The root Tkinter window for the application.
        canvas (tk.Canvas): The canvas widget where all simulation objects are drawn.
        fence (Fence): The Fence object instance in the simulation.
        status_text (int): The canvas item ID for the status text overlay.
        snowflakes (list[Snowflake]): A list of all active Snowflake objects currently in the simulation.
        snowfall_counter (int): A timer to control the rate of new particle generation.
        snow_heights (list[float]): A height map storing the y-coordinate of the top of the snow for each column.
        snowdrift_id (int): ID of the snowdrift polygon.
        drift_updated (bool): True if the particle has landed in the accumulation zone.
    """
    def __init__(self, root):
        """
        Initializes the main simulation window and state.

        Args:
            root (tk.Tk): The root Tkinter window for the application.
        """
        self.root = root
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg='sky blue', highlightthickness=0)
        self.canvas.pack()

        # Draw gradient sky
        for y in range(HEIGHT):
            r = max(0, min(int(135 + y * 0.1), 255))
            g = max(0, min(int(206 + y * 0.1), 255))
            b = int(235)
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.canvas.create_line(0, y, WIDTH, y, fill=color)

        # Draw ground and fence
        self.canvas.create_rectangle(0, GROUND_LEVEL, WIDTH, HEIGHT, fill='white', outline='')
        self.fence = Fence(self.canvas)

        # Status text
        self.status_text = self.canvas.create_text(10, 10, anchor='nw', fill='black', text='Snowdrifts forming...')

        # Initialize snowflakes
        self.snowflakes = []
        self.snowfall_counter = 0
        self.snow_heights = [GROUND_LEVEL for _ in range(WIDTH)]  # Height map for snow mound
        self.snowdrift_id = None
        self.drift_updated = False

        self.update()

    def update(self):
        """Executes a single frame of the main simulation loop."""
        start_time = time.time()

        # Add new snowflakes
        if self.snowfall_counter % 10 == 0:
            for _ in range(SNOWFALL_RATE):
                x = random.uniform(0, WIDTH)
                y = random.uniform(0, HEIGHT // 4)
                self.snowflakes.append(Snowflake(self.canvas, x, y, self))
        self.snowfall_counter += 1

        # Move active snowflakes
        active_snowflakes = []
        for snowflake in self.snowflakes:
            snowflake.move()
            if snowflake.landed:
                self.canvas.delete(snowflake.id)
            else:
                active_snowflakes.append(snowflake)
        self.snowflakes = active_snowflakes

        # Only smooth the drift if it has actually changed this frame
        if self.drift_updated:
            self.smooth_snowdrift()
            self.drift_updated = False

        # Draw the snowdrift polygon
        self.draw_snowdrift()

        # Calculate and display the highest point of the snowdrift in the accumulation zone
        accumulation_zone = self.snow_heights[int(FENCE_LEFT - ACCUMULATION_ZONE_WIDTH):int(FENCE_LEFT)]
        if accumulation_zone:
            highest_snow_point = min(accumulation_zone)
            drift_height_pixels = GROUND_LEVEL - highest_snow_point
            drift_height_meters = drift_height_pixels / PPM
            status = f"Snowdrift height: {drift_height_meters:.2f} m"
            self.canvas.itemconfig(self.status_text, text=status)

        # Always draw fence in front
        self.canvas.tag_raise(self.fence.id)

        # Ensure simulation runs at ~60 FPS
        elapsed = time.time() - start_time
        delay = max(1, int(16 - elapsed * 1000))
        self.root.after(delay, self.update)

    def draw_snowdrift(self):
        """Draws the accumulated snow as a single, solid polygon."""
        # Define the vertices of the polygon based on the height map
        points = [0, HEIGHT]  # Start at bottom-left
        for x, y in enumerate(self.snow_heights):
            if not y > FENCE_Y:  # Avoid drawing over fence
                points.extend([x, y])
        points.extend([WIDTH, HEIGHT])  # End at bottom-right

        # If the polygon has already been drawn, update its coordinates; else, create it
        if self.snowdrift_id:
            self.canvas.coords(self.snowdrift_id, points)
        else:
            self.snowdrift_id = self.canvas.create_polygon(points, fill='white', outline='')

        # Ensure the polygon is drawn behind the fence
        self.canvas.tag_lower(self.snowdrift_id, self.fence.id)

    def smooth_snowdrift(self):
        """Simulates snow settling by smoothing the height map."""
        # Multiple passes to allow the smoothing effect to propagate across the drift.
        for _ in range(5):
            # If a column is lower than its left or right neighbors, it pulls snow down.
            for i in range(int(FENCE_LEFT) - 1, 0, -1):
                if self.snow_heights[i] > self.snow_heights[i - 1] + MAX_SLOPE:
                    self.snow_heights[i - 1] = self.snow_heights[i] - MAX_SLOPE
            for i in range(int(FENCE_LEFT)):
                if self.snow_heights[i] > self.snow_heights[i + 1] + MAX_SLOPE:
                    self.snow_heights[i + 1] = self.snow_heights[i] - MAX_SLOPE


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Snowdrift Simulation")
    app = SnowDriftSimulation(root)
    root.mainloop()
