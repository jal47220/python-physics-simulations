import tkinter as tk
from random import randint

# Simulation constants
WINDOW_SIZE = 800                       # Window dimensions in px
GRID_SIZE = 50                          # Number of grid cells per row/col
CELL_SIZE = WINDOW_SIZE // GRID_SIZE    # Cell size in px
WATER_COLOR = '#1E90FF'                 # Hex value of tkinter's dodger blue color
GRASS_COLOR = '#6B8E23'                 # Hex value of tkinter's olive drab color
TREE_COLOR = '#556B2F'                  # Hex value of tkinter's dark olive green color

# Physics constants
UPDATE_TIME_STEP = 0.1                  # tkinter update time step in s
BURN_DURATION = 1                       # Cell burn duration in s
THERMAL_DIFFUSIVITY = 0.07              # Rate of heat diffusion in °C/time step
HEAT_LOSS_COEFFICIENT = 0.2             # Fraction of heat lost per time step due to cooling
GRASS_IGNITION_TEMPERATURE = 250        # Ignition threshold for grass cells in °C
GRASS_MAX_TEMPERATURE = 800             # Peak ignited temperature for grass in °C
TREE_IGNITION_TEMPERATURE = 300         # Ignition threshold for tree cells in °C
TREE_MAX_TEMPERATURE = 1000             # Peak ignited temperature for trees in °C

# Precomputed neighbor offsets for reduced update_heat loop overhead
NEIGHBOR_OFFSETS = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1),  (-1, 1), (-1, 0)]


class Cell:
    """
    Represents a single grid cell in the forest-fire simulation.

    Attributes:
        canvas (tk.Canvas): Canvas used for drawing this cell.
        x (int): Column index of the cell in the grid.
        y (int): Row index of the cell in the grid.
        type (int): Cell type (0 = water, 1 = grass, 2 = tree).
        heat (float): Current temperature of the cell in °C.
        burning (bool): True if the cell is currently burning.
        burned (bool): True once the cell has finished burning.
        burn_time (float): Elapsed time since ignition in s.
        rect (int): ID of the rectangle on the canvas representing this cell.
    """
    def __init__(self, canvas, x, y):
        """
        Initializes a Cell on the canvas at grid position (x, y).

        Args:
            canvas (tk.Canvas): The tkinter Canvas on which the cell is drawn.
            x (int): Column index of the cell in the grid.
            y (int): Row index of the cell in the grid.
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.type = randint(0, 2)
        self.heat = 0
        self.burning = False
        self.burned = False
        self.burn_time = 0
        self.rect = self.canvas.create_rectangle(x * CELL_SIZE, y * CELL_SIZE,
                                                 (x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE,
                                                 fill=self.get_base_color())

    def get_base_color(self):
        """
        Returns the default fill color based on the cell type.

        Returns:
            str: Hex color code corresponding to water, grass, or tree.
        """
        if self.type == 0:
            return WATER_COLOR
        elif self.type == 1:
            return GRASS_COLOR
        else:
            return TREE_COLOR

    def get_heated_color(self):
        """
        Returns the cell’s color blended toward red based on current heat.

        Returns:
            str: Hex color code representing the heated color.
        """
        # Determine base color by cell type
        base_hex = GRASS_COLOR if self.type == 1 else TREE_COLOR

        # Convert hex to RGB components
        r0 = int(base_hex[1:3], 16)
        g0 = int(base_hex[3:5], 16)
        b0 = int(base_hex[5:7], 16)

        # Compute heat ratio relative to type-specific ignition
        threshold = (GRASS_IGNITION_TEMPERATURE if self.type == 1 else TREE_IGNITION_TEMPERATURE)
        ratio = min(self.heat / threshold, 1.0)

        # Interpolate toward red (255,0,0)
        r = int(r0 + ratio * (255 - r0))
        g = int(g0 * (1 - ratio))
        b = int(b0 * (1 - ratio))

        return f'#{r:02x}{g:02x}{b:02x}'

    def ignite(self):
        """Ignites the cell if it is flammable and not already burning"""
        if self.type != 0 and not self.burning:
            self.burning = True
            self.canvas.itemconfig(self.rect, fill='red')

    def burn(self):
        """Advances the burn timer and finalizes the burning process """
        if self.burning:
            self.burn_time += 1
            if self.burn_time >= BURN_DURATION / UPDATE_TIME_STEP:
                self.burning = False
                self.burned = True
                self.canvas.itemconfig(self.rect, fill='black')

    def update_heat(self, grid):
        """
        Updates a cell’s temperature and visual state each update step.

        Args:
            grid (list[list[Cell]]): 2D grid of cells for neighbor heat lookup.
        """
        # Skip heat logic for water cells
        if self.type == 0:
            self.heat = 0.0
            self.canvas.itemconfig(self.rect, fill=WATER_COLOR)
            return

        # Maintain maximum temperature while burning
        if self.burning:
            self.heat = (GRASS_MAX_TEMPERATURE if self.type == 1 else TREE_MAX_TEMPERATURE)
            return

        # Compute diffusion-driven temperature change
        total = 0.0
        count = 0
        for dx, dy in NEIGHBOR_OFFSETS:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                total += grid[ny][nx].heat
                count += 1

        # Apply heat loss
        delta = total - count * self.heat
        self.heat += THERMAL_DIFFUSIVITY * delta
        self.heat = max(0.0, self.heat * (1 - HEAT_LOSS_COEFFICIENT))

        # Update color toward red based on current heat, or set to base if cooled
        self.canvas.itemconfig(self.rect, fill=self.get_heated_color())

        # Enforce permanent black for burned cells
        if self.burned:
            self.canvas.itemconfig(self.rect, fill='black')
            return

        # Ignite at physical threshold
        threshold = GRASS_IGNITION_TEMPERATURE if self.type == 1 else TREE_IGNITION_TEMPERATURE
        if self.heat >= threshold:
            self.ignite()


class App:
    """
    Main application for the forest‐fire simulation.

    Manages the tkinter window, canvas, and grid of Cell objects, and handles user interaction and
    the simulation update loop.

    Attributes:
        root (tk.Tk): The main tkinter window.
        canvas (tk.Canvas): Canvas widget for drawing the cells.
        grid (list[list[Cell]]): 2D list of Cell instances forming the simulation grid.
    """
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(self.root, width=WINDOW_SIZE, height=WINDOW_SIZE)
        self.canvas.pack()
        self.grid = [[Cell(self.canvas, x, y) for x in range(GRID_SIZE)] for y in range(GRID_SIZE)]
        self.canvas.bind('<Button-1>', self.click)
        self.update()

    def click(self, event):
        """
        Handle mouse click to ignite a cell at the clicked position.

        Args:
            event (tk.Event): Mouse click event containing pixel coordinates.
        """
        x = event.x // CELL_SIZE
        y = event.y // CELL_SIZE
        if self.grid[y][x].type != 0:
            self.grid[y][x].ignite()

    def update(self):
        """Performs one simulation update step and schedules the next update"""
        for row in self.grid:
            for cell in row:
                cell.update_heat(self.grid)
                cell.burn()
        self.root.after(100, self.update)


# Initialize and run the simulation
if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
