import arcade
import numpy as np
from PIL import Image

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
OVERLAY_WIDTH, OVERLAY_HEIGHT = 290, 50
MEMBRANE_SIZE = 50
MIN_TENSION, DEFAULT_TENSION, MAX_TENSION = 0.0, 0.1, 1.0
MIN_DAMPING, DEFAULT_DAMPING, MAX_DAMPING = 0.0, 0.05, 1.0
SCALE_X = WINDOW_WIDTH / MEMBRANE_SIZE
SCALE_Y = WINDOW_HEIGHT / MEMBRANE_SIZE


def interpolate_edge(corner1_value, corner2_value, x1, y1, x2, y2):
    """
    Linearly interpolate along an edge to find the intersection point
    where a contour crosses between two corner values

    Args:
        corner1_value (np.ndarray): Value at the first corner
        corner2_value (np.ndarray): Value at the second corner
        x1 (float): X-coordinate of the first corner
        y1 (float): Y-coordinate of the first corner
        x2 (float): X-coordinate of the second corner
        y2 (float): Y-coordinate of the second corner

    Returns:
        tuple[float, float] | None: The (x, y) intersection point, or None if no crossing
    """
    if corner1_value * corner2_value < 0:  # Sign change means crossing
        t = corner1_value / (corner1_value - corner2_value)
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return ix, iy
    return None


def draw_contour(heights, level, color):
    """
    Draw a single contour line for the given height matrix at the specified level

    Args:
        heights (np.ndarray): 2D array of membrane height values
        level (tuple[int, Any]): The contour level to highlight
        color (float): RGBA color used for drawing the contour line
    """
    rows, cols = heights.shape
    for i in range(rows - 1):
        for j in range(cols - 1):
            # Evaluate each corner minus the contour level
            corner_values = [
                heights[i, j] - level,
                heights[i, j + 1] - level,
                heights[i + 1, j + 1] - level,
                heights[i + 1, j] - level
            ]

            # Compute the corresponding screen-space coordinates
            corner_coords = [
                (j * SCALE_X, i * SCALE_Y),
                ((j + 1) * SCALE_X, i * SCALE_Y),
                ((j + 1) * SCALE_X, (i + 1) * SCALE_Y),
                (j * SCALE_X, (i + 1) * SCALE_Y)
            ]

            # Define edges as (corner index 1, corner index 2)
            edges = [(0, 1), (1, 2), (2, 3), (3, 0)]

            # Find intersection points on edges
            points = [
                interpolate_edge(
                    corner_values[i1], corner_values[i2],
                    *corner_coords[i1], *corner_coords[i2]
                )
                for i1, i2 in edges
            ]

            # Filter out None values (edges without crossings)
            points = [p for p in points if p is not None]

            # If exactly two intersections, draw one line
            if len(points) == 2:
                arcade.draw_line(*points[0], *points[1], color, 1)


class Membrane:
    """
    Represents a 2D wave membrane with height and velocity values at each point

    Attributes:
        size (int): The number of grid points along one dimension of the membrane
        heights (np.ndarray): An array storing the height (displacement) values of the membrane
        velocities (np.ndarray): An array storing the velocity values of the membrane
    """
    def __init__(self, size):
        self.size = size
        self.heights = np.zeros((size, size))
        self.velocities = np.zeros((size, size))

    def update(self, tension, damping, dt):
        """
        Updates the membrane state using the wave equation with tension and damping

        Args:
            tension (float): Controls the stiffness of the membrane; higher values
                             increase wave propagation speed.
            damping (float): Controls the energy loss per update; higher values
                             cause waves to dissipate faster.
            dt (float): The time step for numerical integration.
        """
        # Compute the Laplacian for interior grid points using vectorized operations
        laplacian = (self.heights[2:, 1:-1] + self.heights[:-2, 1:-1] +
                     self.heights[1:-1, 2:] + self.heights[1:-1, :-2] -
                     4 * self.heights[1:-1, 1:-1])

        # Update interior velocities and heights using dynamic tension and damping
        self.velocities[1:-1, 1:-1] += dt * (tension * laplacian - damping * self.velocities[1:-1, 1:-1])
        self.heights[1:-1, 1:-1] += dt * self.velocities[1:-1, 1:-1]

        # Pinned edges (height = 0 at boundary):
        self.heights[0, :] = 0
        self.heights[-1, :] = 0
        self.heights[:, 0] = 0
        self.heights[:, -1] = 0

    def disturb(self, x, y):
        """
        Introduces a localized disturbance to the membrane at the specified coordinates

        This function modifies the height values in a circular pattern centered at (x, y),
        using a sinusoidal function to create a smooth initial displacement.

        Args:
            x (int): The x-coordinate (column index) of the disturbance center
            y (int): The y-coordinate (row index) of the disturbance center
        """
        for i in range(-5, 6):
            for j in range(-5, 6):
                if 0 <= x + i < self.size and 0 <= y + j < self.size:
                    self.heights[x + i, y + j] = np.sin(np.sqrt(i ** 2 + j ** 2))


class WavePropagation(arcade.Window):
    """
    Represents the simulation window for wave propagation on a 2D membrane

    Attributes:
        membrane (Membrane): The 2D wave simulation model
        contour_levels (int): Number of contour levels to display
        tension (float): The wave tension parameter, affecting propagation speed
        damping (float): The wave damping parameter, affecting energy dissipation
        heatmap_texture (arcade.Texture): A reusable texture for rendering as an image.
    """
    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, "Wave Propagation")
        self.membrane = Membrane(MEMBRANE_SIZE)
        self.contour_levels = 10
        self.tension = DEFAULT_TENSION
        self.damping = DEFAULT_DAMPING

        # Create a single texture to reuse each frame
        initial_data = np.zeros((MEMBRANE_SIZE, MEMBRANE_SIZE), dtype=np.uint8)
        initial_img = Image.fromarray(initial_data, mode='L').convert('RGBA')
        self.heatmap_texture = arcade.Texture(name="heatmap_texture", image=initial_img)

    def on_draw(self):
        """Handles rendering for the simulation window"""
        self.clear()
        self.draw_membrane()
        self.draw_contours()
        self.draw_overlay()

    def draw_membrane(self):
        """Renders the membrane as a heatmap texture"""
        # Normalize the height values to the range [0, 255] for image representation
        heights = self.membrane.heights
        ptp_val = np.ptp(heights)
        if ptp_val < 1e-5:
            # If the entire membrane is nearly uniform, assign mid-gray
            norm = np.full_like(heights, 0.5)
        else:
            # Otherwise, normalize to [0, 1]
            norm = (heights - heights.min()) / ptp_val
        image_data = (norm * 255).astype(np.uint8)

        # Create a grayscale PIL image from the normalized data and convert it to RGB
        img = Image.fromarray(image_data, mode='L').convert('RGBA')

        # Draw the texture covering the entire membrane grid region
        rect = arcade.rect.XYWH(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.heatmap_texture.image = img
        arcade.draw_texture_rect(self.heatmap_texture, rect)

    def draw_contours(self):
        """Renders contour lines over the membrane visualization"""
        # Same fixed contour range as before
        contour_values = np.linspace(-1, 1, self.contour_levels)

        # Go through each contour level
        for i, level in enumerate(contour_values):
            # fraction goes from 0.0 (for the first contour) up to 1.0 (for the last)
            fraction = i / (len(contour_values) - 1) if len(contour_values) > 1 else 0

            # Simple color gradient: blue -> red
            r = int(255 * fraction)
            g = 0
            b = int(255 * (1 - fraction))
            a = 255
            color = (r, g, b, a)
            draw_contour(self.membrane.heights, level, color)

    def draw_overlay(self):
        """Renders an overlay displaying simulation parameters"""
        # Define the dimensions for the overlay background
        overlay_rect = arcade.rect.XYWH(0, self.height - 35, OVERLAY_WIDTH, OVERLAY_HEIGHT)

        # Draw the background rectangle using draw_rect_filled with the created rectangle
        arcade.draw_rect_filled(overlay_rect, (0, 0, 0, 150))

        # Create arcade.Text objects for the simulation parameters (more efficient than draw_text)
        tension_label = arcade.Text(f"Tension: {self.tension:.2f}", 20, self.height - 30, arcade.color.WHITE, 14)
        damping_label = arcade.Text(f"Damping: {self.damping:.2f}", 20, self.height - 50, arcade.color.WHITE, 14)

        # Draw the text objects
        tension_label.draw()
        damping_label.draw()

    def on_update(self, dt):
        """
        Updates the simulation state for the current time step

        Args:
            dt (float): The time step duration in seconds
        """
        self.membrane.update(self.tension, self.damping, dt)

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Handles mouse press events to introduce disturbances in the membrane

        Args:
            x (float): The x-coordinate of the mouse click in window space (px)
            y (float): The y-coordinate of the mouse click in window space (px)
            button (int): The mouse button pressed (e.g., left, right, middle)
            modifiers (int): Any modifier keys held during the click (e.g., Shift, Ctrl)
        """
        grid_x = int(x // (WINDOW_WIDTH // MEMBRANE_SIZE))
        grid_y = int(y // (WINDOW_HEIGHT // MEMBRANE_SIZE))
        self.membrane.disturb(grid_y, grid_x)

    def on_key_press(self, key, modifiers):
        """
        Handles key press events to adjust simulation parameters

        Allows the user to modify the tension and damping values using the arrow keys:
        - UP increases tension, DOWN decreases tension
        - RIGHT increases damping, LEFT decreases damping
        The values are clamped within their predefined min/max ranges

        Args:
            key (int): The key code of the pressed key
            modifiers (int): Any modifier keys held during the press (e.g., Shift, Ctrl)
        """
        if key == arcade.key.UP:
            self.tension = min(self.tension + 0.01, MAX_TENSION)
        elif key == arcade.key.DOWN:
            self.tension = max(self.tension - 0.01, MIN_TENSION)
        elif key == arcade.key.LEFT:
            self.damping = max(self.damping - 0.01, MIN_DAMPING)
        elif key == arcade.key.RIGHT:
            self.damping = min(self.damping + 0.01, MAX_DAMPING)


def main():
    WavePropagation()
    arcade.run()

if __name__ == "__main__":
    main()
