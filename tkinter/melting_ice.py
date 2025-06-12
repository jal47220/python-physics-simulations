import tkinter as tk
import random
import time

# Spatial constants
WIDTH, HEIGHT = 800, 600                # Canvas dimensions (pixels)
PLATE_WIDTH, PLATE_HEIGHT = 400, 50     # Hot plate dimensions (pixels)
PLATE_Y = HEIGHT - PLATE_HEIGHT - 50    # Vertical position of the plate’s top edge
WATER_DROPLET_SIZE = 5                  # Diameter of each water droplet (pixels)
WATER_POOL_HEIGHT = 4                   # Height of each pool segment (pixels)
ICE_SIZE = 100                          # Initial side length of the ice cube (pixels)

# Time constants
TARGET_FPS = 60                         # Simulation frame rate
FRAME_DELAY = int(1000 / TARGET_FPS)    # Delay between frames (ms)

# Physics constants
CONDUCTION_K = 0.2                      # Thermal conduction coefficient (J/s·°C)
SPECIFIC_HEAT_ICE = 2.09                # Specific heat of ice (J/g·°C)
SPECIFIC_HEAT_WATER = 4.18              # Specific heat of water (J/g·°C)
LATENT_HEAT_FUSION = 334                # Latent heat of fusion (J/g)
ICE_DENSITY = 0.92                      # Density of ice (g/cm³)
INIT_ICE_MASS = 920                     # Initial mass of the ice cube (g)
WATER_DENSITY = 1.0                     # Density of water (g/cm³)
WATER_FLOW_RATE = 0.5                   # Rate at which water flows off the plate (pixels/frame)


class IceMeltingSimulation:
    """
    Simulates an ice cube melting on a heated plate in a Tkinter canvas.

    Attributes:
        plate_temperature (float): Current temperature of the plate (°C).
        ice_temperature (float): Current temperature of the ice (°C).
        water_temperature (float): Current temperature of the meltwater (°C).
        ice_mass (float): Mass of the ice cube remaining (g).
        water_mass (float): Mass of collected meltwater (g).
        previous_frame_time (float): Timestamp of the last frame (s).
        previous_cube_size (int): Last drawn side length of the ice cube (px).
        water_droplets (list): Active falling droplet data.
        water_pool (list): Accumulated pool segment data.
        glow_layers (list): Canvas IDs for glow effect rings.
        root (tk.Tk): Main Tkinter window.
        canvas (tk.Canvas): Drawing surface for the simulation.
        temp_text_label (int): Canvas text ID for temperature display.
        mass_text_label (int): Canvas text ID for mass display.
        instructions_text (int): Canvas text ID for instructions.
    """
    def __init__(self):
        # Simulation state
        self.plate_temperature = 50
        self.ice_temperature = -5
        self.water_temperature = 0
        self.ice_mass = INIT_ICE_MASS
        self.water_mass = 0
        self.previous_frame_time = time.time()
        self.previous_cube_size = ICE_SIZE

        # Dynamic element collection lists
        self.water_droplets = []
        self.water_pool = []
        self.glow_layers = []

        # Create the main window and add keybinds
        self.root = tk.Tk()
        self.root.title("Ice Cube Melting Simulation")
        self.root.bind('<Left>', self.adjust_plate_temperature)
        self.root.bind('<Right>', self.adjust_plate_temperature)

        # Initialize canvas and get background color for glow fading
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg='#87CEEB')
        self.canvas.pack()
        self.background_color = self.canvas['bg']
        self.background_red = int(self.background_color[1:3], 16)
        self.background_green = int(self.background_color[3:5], 16)
        self.background_blue = int(self.background_color[5:7], 16)

        # Define static plate
        self.plate = self.canvas.create_rectangle(
            (WIDTH - PLATE_WIDTH) // 2, PLATE_Y,
            (WIDTH + PLATE_WIDTH) // 2, PLATE_Y + PLATE_HEIGHT,
            fill='#A0522D', outline='black', width=2
        )

        # Initialize ice cube
        self.ice_cube = self.canvas.create_rectangle(
            (WIDTH - ICE_SIZE) // 2, PLATE_Y - ICE_SIZE,
            (WIDTH + ICE_SIZE) // 2, PLATE_Y,
            fill='white', outline='blue', width=2
        )

        # Initialize UI text
        self.temp_text_label = self.canvas.create_text(10, 10, anchor='nw', font=('Arial', 16), fill='black')
        self.mass_text_label = self.canvas.create_text(10, 40, anchor='nw', font=('Arial', 16), fill='black')
        self.instructions_text = self.canvas.create_text(
            WIDTH // 2, HEIGHT - 20, anchor='s', font=('Arial', 14), fill='black',
            text="Use LEFT/RIGHT arrow keys to adjust plate temperature"
        )

    def conduction(self, plate_temp, ice_temp):
        """
        Calculates heat transfer rate between the plate and ice via conduction.

        Parameters:
            plate_temp (float): Temperature of the plate (°C)
            ice_temp (float): Temperature of the ice (°C)

        Returns:
            float: Heat transfer rate (J/s)
        """
        delta_temp = plate_temp - ice_temp
        area = ICE_SIZE * ICE_SIZE
        return CONDUCTION_K * area * delta_temp

    def draw_glow(self, plate_temp):
        """
        Draw a glow effect around the plate based on its temperature.

        Parameters:
            plate_temp (float): Temperature of the plate (°C)
        """
        # Remove any existing glow rings
        for glow_layer in self.glow_layers:
            self.canvas.delete(glow_layer)
        self.glow_layers.clear()

        # Normalize plate temperature to a 0.0–1.0 range (capped at 50°C)
        temperature_fraction = min(1.0, plate_temp / 50.0)

        # Pure orange RGB components
        orange = (255, 165, 0)

        # Glow ring settings
        number_of_rings = 10
        maximum_spread = 10
        plate_left_x = (WIDTH - PLATE_WIDTH) // 2
        plate_right_x = (WIDTH + PLATE_WIDTH) // 2

        # Draw concentric, fading rings above the plate’s top edge
        for ring_index in range(number_of_rings):
            fade_factor = (1 - ring_index / number_of_rings) * temperature_fraction
            red = int(self.background_red + (orange[0] - self.background_red) * fade_factor)
            green = int(self.background_green + (orange[1] - self.background_green) * fade_factor)
            blue= int(self.background_blue + (orange[2] - self.background_blue) * fade_factor)
            ring_color = f'#{red:02x}{green:02x}{blue:02x}'

            # Draw current ring
            offset = int(maximum_spread * (ring_index + 1) / number_of_rings)
            glow_id = self.canvas.create_rectangle(
                plate_left_x - offset + 5,
                PLATE_Y - offset,
                plate_right_x + offset - 5,
                PLATE_Y,
                outline=ring_color,
                width=2
            )
            self.glow_layers.append(glow_id)

    def draw_water_droplets(self):
        """Draw water droplets falling from the ice cube"""
        active_droplets = []
        for droplet in self.water_droplets:
            # Move and draw each drop
            x, y = droplet['coords']
            self.canvas.coords(
                droplet['id'],
                x - WATER_DROPLET_SIZE // 2, y - WATER_DROPLET_SIZE // 2,
                x + WATER_DROPLET_SIZE // 2, y + WATER_DROPLET_SIZE // 2
            )
            self.canvas.tag_raise(droplet['id'])
            droplet['coords'][1] += droplet['speed']

            # Sustain active droplet or convert to pool segment
            if droplet['coords'][1] <= PLATE_Y + PLATE_HEIGHT - 5:
                active_droplets.append(droplet)
            else:
                self.water_pool.append({
                    'coords': [x, PLATE_Y + PLATE_HEIGHT - 5],
                    'width': WATER_DROPLET_SIZE,
                    'id': self.canvas.create_rectangle(
                        x - WATER_DROPLET_SIZE // 2, PLATE_Y,
                        x + WATER_DROPLET_SIZE // 2, PLATE_Y + WATER_POOL_HEIGHT,
                        fill='#0000FF', outline=''
                    )
                })
                self.canvas.delete(droplet['id'])

        # Replace droplet list with survivors
        self.water_droplets = active_droplets

    def draw_water_pool(self):
        """Draw the water pool accumulating at the bottom of the plate"""
        for segment in self.water_pool[:]:
            x, y = segment['coords']
            self.canvas.coords(
                segment['id'],
                x - (segment['width'] // 2), y,
                x + (segment['width'] // 2), y + WATER_POOL_HEIGHT + 2
            )
            segment['width'] += 0.2

    def update_labels(self):
        """Update the text labels displaying simulation information"""
        self.canvas.itemconfig(self.temp_text_label,
                          text=f"Plate Temp: {self.plate_temperature:.1f}°C | "
                               f"Ice Temp: {self.ice_temperature:.1f}°C")
        self.canvas.itemconfig(self.mass_text_label,
                          text=f"Ice Mass: {self.ice_mass:.1f} g | "
                               f"Water Mass: {self.water_mass:.1f} g")

    def simulate(self):
        """Main simulation loop updating physics and rendering changes"""

        # Compute real time since last frame
        current_time = time.time()
        dt = current_time - self.previous_frame_time
        self.previous_frame_time = current_time

        # Determine current ice cube side length and contact area (pixels²)
        cube_side = ICE_SIZE * (self.ice_mass / INIT_ICE_MASS) ** (1/3)
        area = cube_side * cube_side

        # Heat transfer rate via Fourier’s law: k·A·ΔT (J/s)
        rate = CONDUCTION_K * area * (self.plate_temperature - self.ice_temperature)

        # Melt ice based on latent heat; update masses
        melted_mass = max(0.0, rate * dt / LATENT_HEAT_FUSION)
        self.ice_mass = max(0.0, self.ice_mass - melted_mass)
        self.water_mass += melted_mass

        # Update temperatures only if mass > 0 to avoid division-by-zero
        if self.ice_mass > 0:
            self.ice_temperature = 0.0
        if self.water_mass > 0:
            self.water_temperature += (rate * dt) / (self.water_mass * SPECIFIC_HEAT_WATER)

        # Resize ice cube visually, clamping to previous size to prevent unrealistic growth
        computed_size = int(
            ICE_SIZE * (self.ice_mass / INIT_ICE_MASS) ** (1/3)
        )
        new_ice_size = min(computed_size, self.previous_cube_size)
        self.previous_cube_size = new_ice_size
        left = (WIDTH - new_ice_size) // 2
        self.canvas.coords(
            self.ice_cube,
            left, PLATE_Y - new_ice_size,
            left + new_ice_size, PLATE_Y
        )

        # Draw the glow effect
        self.draw_glow(self.plate_temperature)

        # Create water droplets along the sides of the ice based on melt mass
        if melted_mass > 0:
            count = int(melted_mass)
            if random.random() < (melted_mass  - count):
                count += 1

            for _ in range(count):
                new_drop = {
                    'coords': [random.randint((WIDTH - new_ice_size) // 2, (WIDTH + new_ice_size) // 2),
                               PLATE_Y - new_ice_size],
                    'speed': random.randint(2, 5),
                    'id': self.canvas.create_oval(0, 0, 0, 0, fill='#0000FF', outline='')
                }

                self.water_droplets.append(new_drop)
                self.canvas.tag_raise(new_drop['id'])

        # Draw the water droplets and pool
        self.draw_water_droplets()
        self.draw_water_pool()

        # Update the labels
        self.update_labels()

        # Schedule the next update
        self.root.after(FRAME_DELAY, self.simulate)

    def adjust_plate_temperature(self, event):
        """
        Adjust the plate temperature based on user input.

        Parameters:
            event (tk.Event): Keyboard event
        """
        if event.keysym == 'Left':
            self.plate_temperature = max(0, self.plate_temperature - 5)
        elif event.keysym == 'Right':
            self.plate_temperature = min(100, self.plate_temperature + 5)


if __name__ == "__main__":
    # Start the simulation
    simulation = IceMeltingSimulation()
    simulation.simulate()

    # Start the main loop
    simulation.root.mainloop()
