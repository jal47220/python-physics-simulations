import tkinter as tk
import math
import random
import time

# --- Constants ---
WIDTH, HEIGHT = 800, 600            # Canvas dimensions in pixels
SKY_TOP = (0, 102, 204)             # RGB color for the top of the sky gradient (light blue)
SKY_BOTTOM = (255, 255, 255)        # RGB color for the bottom of the sky gradient (white)
STEM_COLOR = "#228B22"              # Hex color code for the main dandelion stem (forest green)
STEM_WIDTH = 3                      # Width of the main dandelion stem in pixels
SEED_BODY_COLOR = "#DAA520"         # Hex color code for the body of a seed (goldenrod)
SEED_BODY_WIDTH = 3                 # Default width for the seed body line in pixels
SEED_RESISTANCE = (0.5, 1.5)        # Range for a seed's resistance to detachment by wind
SEED_SPACING = 25                   # Spacing parameter for seed placement in pixels
NUM_SEEDS = 100                     # Total number of seeds on the dandelion puffball
STEM_LENGTH = 150                   # Length of the main dandelion stem in pixels
PAPPUS_COLOR = "#FFFFFF"            # Hex color code for the pappus branches (white)
PAPPUS_LENGTH = 15                  # Base length of each individual pappus branch in pixels
PAPPUS_BRANCHES = 8                 # Number of individual filament branches in each seed's pappus
GRAVITY = 0.03                      # Downward acceleration factor applied to seeds per update cycle in pixels/cycle^2
WIND_BASE = 0.8                     # Base component of the wind speed
WIND_VARIATION = (-0.4, 0.7)        # Rang for random variation added to WIND_BASE
WIND_CHANGE_INTERVAL = 2000         # Interval for updating wind speed and direction in milliseconds
HORIZONTAL_DRAG_FACTOR = 0.05       # Proportional reduction factor for horizontal seed velocity per update cycle


class Seed:
    """
    Represents a single dandelion seed (body + pappus) with physics and wind resistance.

    Attributes:
        canvas (tk.Canvas): The tkinter canvas on which the seed's visual elements are drawn.
        attached (bool): True if the seed is currently attached to the dandelion puffball, otherwise False.
        released (bool): True if the seed has been released from the puffball. Initially False.
        resistance (float): A random factor for the seed's resistance to being detached by wind.
        size (float): A multiplier affecting the visual size of the seed and some of its physics properties.
        x (float): The current x-coordinate of the seed's central point on the canvas, in pixels.
        y (float): The current y-coordinate of the seed's central point on the canvas, in pixels.
        vx (float): The current horizontal velocity of the seed, in pixels/cycle.
        vy (float): The current vertical velocity of the seed, in pixels/cycle.
        terminal_velocity (float): The maximum speed the seed can reach due to gravity.
        wind_factor (float): A multiplier, scaled by the seed's size, that determines how susceptible the seed
                             is to wind forces.
        body (int): The canvas item ID for the line representing the seed's body.
        pappus (list of int): A list containing the IDs for each branch of the seed's pappus.
    """
    def __init__(self, canvas, seed_x, seed_y, puffball_x, puffball_y, attached=True):
        """
        Initializes a new dandelion seed.

        The seed is initially drawn with its body pointing radially inward towards the
        center of the puffball if it is attached. Its pappus branches are spread symmetrically.

        Args:
            canvas (tk.Canvas): The tkinter canvas on which to draw the seed.
            seed_x (float): The initial x-coordinate of the seed's attachment point in pixels.
            seed_y (float): The initial y-coordinate of the seed's attachment point in pixels.
            puffball_x (float): The x-coordinate of the center of the dandelion puffball in pixels.
            puffball_y (float): The y-coordinate of the center of the dandelion puffball in pixels.
            attached (bool, optional): True if the seed is attached to the puffball, False otherwise. Defaults to True.
        """
        self.canvas = canvas
        self.attached = attached
        self.released = False
        self.resistance = random.uniform(*SEED_RESISTANCE)
        self.size = random.uniform(0.8, 1.2)

        # Physics properties
        self.x = seed_x
        self.y = seed_y
        self.vx = 0
        self.vy = 0
        self.terminal_velocity = 0.5 * self.size
        self.wind_factor = 0.8 * self.size

        # Seed visual elements
        length = 25 * self.size
        width = 3 * self.size

        # Calculate end point for the radially drawn seed body when attached
        dx_to_center = puffball_x - seed_x
        dy_to_center = puffball_y - seed_y
        dist_to_center = math.sqrt(dx_to_center**2 + dy_to_center**2)

        # Normalized direction vector from seed towards puffball center
        norm_dx = dx_to_center / dist_to_center
        norm_dy = dy_to_center / dist_to_center

        # Calculate the end point of the body line
        body_end_x = seed_x + norm_dx * length
        body_end_y = seed_y + norm_dy * length

        # Draw initial seeds
        self.body = self.canvas.create_line(
            seed_x, seed_y,
            body_end_x, body_end_y,
            fill=SEED_BODY_COLOR,
            width=width,
            capstyle=tk.ROUND,
            smooth=False,
            tags="seed_body"
        )
        self.pappus = []
        angle_step = math.pi * 2 / PAPPUS_BRANCHES
        for i in range(PAPPUS_BRANCHES):
            angle = i * angle_step
            end_x = seed_x + math.cos(angle) * PAPPUS_LENGTH * self.size
            end_y = seed_y + math.sin(angle) * PAPPUS_LENGTH * self.size
            line = self.canvas.create_line(
                seed_x, seed_y, end_x, end_y,
                fill=PAPPUS_COLOR,
                width=1,
                capstyle=tk.ROUND,
                smooth=False,
                tags="seed_pappus"  # Tag for layering when drawing
            )
            self.pappus.append(line)

    def update(self, wind_speed):
        """
        Updates the seed's state, position, and visual representation.

        Args:
            wind_speed (float): The current speed of the wind in the simulation environment.

        Returns:
            bool: True if the seed has moved off-screen and should be removed from the simulation. False otherwise.
        """
        if self.attached:
            # Check if wind speed overcomes the seed's resistance to detach
            if wind_speed > self.resistance:
                self.attached = False
                self.released = True

                # Apply initial velocity when released
                self.vx = wind_speed * self.wind_factor
                self.vy = -0.5 * self.size  # Small upward boost

        elif self.released: # Only move if released
            # Apply physics
            self.vy += GRAVITY
            self.vx *= (1 - HORIZONTAL_DRAG_FACTOR)
            self.vx += wind_speed * self.wind_factor

            # Terminal velocity based on seed size
            if self.vy > self.terminal_velocity:
                self.vy = self.terminal_velocity

            self.x += self.vx
            self.y += self.vy

            # Check if seed is off-screen
            if (self.y > HEIGHT + 25 * self.size or self.x < -PAPPUS_LENGTH * self.size or
                    self.x > WIDTH + PAPPUS_LENGTH * self.size):
                self.canvas.delete(self.body)
                self.canvas.delete(*self.pappus)
                return True  # Signal to remove from list

            # Update visual representation of the seed body
            self.canvas.coords(
                self.body,
                self.x, self.y,
                self.x, self.y + 25 * self.size
            )

            # Check if seed has significant velocity to apply parachute effect
            trail_angle = 0
            apply_parachute_effect = False
            velocity_magnitude_sq = self.vx**2 + self.vy**2
            if velocity_magnitude_sq > 1e-6: # Avoid division by zero when used later
                apply_parachute_effect = True

                # Calculate the angle directly opposite to the direction of motion
                trail_angle = math.atan2(-self.vy, -self.vx)

            # Update visual representation of the pappus
            default_angle_step  = math.pi * 2 / PAPPUS_BRANCHES
            for i, line_id in enumerate(self.pappus):
                if apply_parachute_effect:
                    # Distribute branches, centered on trail_angle
                    if PAPPUS_BRANCHES > 1:
                        angle_offset = (i / (PAPPUS_BRANCHES - 1) - 0.5) * math.pi
                    else:
                        angle_offset = 0 # Single branch points directly along trail_angle
                    current_branch_angle = trail_angle + angle_offset
                else:
                    # Default uniform spread for stationary released seeds (or if effect is off)
                    current_branch_angle = i * default_angle_step

                end_x = self.x + math.cos(current_branch_angle) * PAPPUS_LENGTH * self.size
                end_y = self.y + math.sin(current_branch_angle) * PAPPUS_LENGTH * self.size
                self.canvas.coords(
                    line_id,
                    self.x, self.y,
                    end_x, end_y
                )

        return False  # Seed not removed


class Dandelion:
    """
    Represents a complete dandelion, including its main stem and a puffball of seeds.

    Attributes:
        canvas (tk.Canvas): The tkinter canvas on which the dandelion and its seeds are drawn.
        stem (int): The canvas item ID for the line representing the main dandelion stem.
        seeds (list of Seed): A list containing all the Seed objects that make up the dandelion's puffball.
    """
    def __init__(self, canvas):
        """
        Initializes a new Dandelion object on the given canvas.

        Args:
            canvas (tk.Canvas): The tkinter canvas on which the dandelion will be drawn.
        """
        self.canvas = canvas
        self.stem = self.canvas.create_line(
            WIDTH / 2, HEIGHT,
            WIDTH / 2, HEIGHT - STEM_LENGTH,
            fill=STEM_COLOR,
            width=STEM_WIDTH,
            smooth=True
        )

        # Create seeds in a Fibonacci sphere pattern
        self.seeds = []
        puffball_x, puffball_y = WIDTH / 2, HEIGHT - STEM_LENGTH
        puff_radius = 45  # Puffball sphere radius
        golden_angle_increment = math.pi * (3. - math.sqrt(5.)) # Approx 2.39996 radians
        for i in range(NUM_SEEDS):
            # Convert spherical to 2D screen coordinates
            y_sphere = 1 - (2 * (i + 0.5)) / NUM_SEEDS
            radius_at_y = math.sqrt(1 - y_sphere * y_sphere)
            theta = golden_angle_increment * i
            x_sphere = math.cos(theta) * radius_at_y
            z_sphere = math.sin(theta) * radius_at_y
            seed_x = puffball_x + puff_radius * x_sphere
            seed_y = puffball_y + puff_radius * y_sphere

            # Determine and apply size variation
            z_factor = 0.75 + (z_sphere * 0.25)
            seed = Seed(canvas, seed_x, seed_y,puffball_x, puffball_y, attached=True)
            seed.size *= z_factor # Scale seed by z-factor

            self.seeds.append(seed)

        # Ensure all pappus elements are drawn on top of all seed body elements
        self.canvas.tag_raise("seed_pappus", "seed_body")

    def update(self, wind_speed):
        """
        Updates the state of all seeds in the dandelion's puffball.

        Args:
            wind_speed (float): The current speed of the wind in the simulation environment.

        Returns:
            int: The number of seeds that were removed from the simulation during this update cycle.
        """
        removed_seeds = 0
        for seed in self.seeds[:]:
            if seed.update(wind_speed):
                self.seeds.remove(seed)
                removed_seeds += 1
        return removed_seeds


def draw_sky(canvas):
    """
    Draws a vertical gradient sky on the given canvas.

    Args:
        canvas (tk.Canvas): The tkinter canvas object on which the sky gradient will be drawn.
    """
    top_r, top_g, top_b = SKY_TOP
    bottom_r, bottom_g, bottom_b = SKY_BOTTOM
    for i in range(HEIGHT):
        r = int(top_r + (bottom_r - top_r) * i / HEIGHT)
        g = int(top_g + (bottom_g - top_g) * i / HEIGHT)
        b = int(top_b + (bottom_b - top_b) * i / HEIGHT)
        color = f'#{r:02x}{g:02x}{b:02x}'
        canvas.create_line(0, i, WIDTH, i, fill=color)


def main():
    """Sets up the simulation and runs the main loop."""
    root = tk.Tk()
    root.title("Dandelion Puffball Simulation")

    # Create canvas
    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT)
    canvas.pack()

    # Draw sky
    draw_sky(canvas)

    # Create dandelion
    dandelion = Dandelion(canvas)

    # Wind simulation variables
    wind_speed = WIND_BASE
    last_wind_change = time.time()

    # Function to update wind
    def update_wind():
        """Periodically updates the global wind_speed."""
        nonlocal wind_speed, last_wind_change
        current_time = time.time()
        if current_time - last_wind_change > WIND_CHANGE_INTERVAL / 1000:
            wind_speed = WIND_BASE + random.uniform(*WIND_VARIATION)
            last_wind_change = current_time

    # Function for main animation loop
    def animate():
        """Executes a single frame of the animation and schedules the next frame."""
        update_wind()
        dandelion.update(wind_speed)
        root.after(16, animate)  # ~60 FPS

    # Start animation
    animate()

    # Start Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    main()
