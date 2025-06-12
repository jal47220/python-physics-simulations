import tkinter as tk
from Box2D import (b2World, b2BodyDef, b2FixtureDef, b2PolygonShape, b2_dynamicBody,
                   b2_staticBody, b2Vec2)
import math

# Constants
PPM = 20.0
TARGET_FPS = 60
TIME_STEP = 1.0 / TARGET_FPS
VELOCITY_ITERATIONS, POSITION_ITERATIONS = 8, 3
DOMINO_WIDTH, DOMINO_HEIGHT, DOMINO_SPACING = 10, 50, 20
MAX_RING_RADIUS = 50
IMPULSE_FORCE = 10


class DominoApp:
    """
    A Tkinter-based physics simulation using PyBox2D that displays a side view of three staggered
    horizontal platforms with upright dominoes arranged in a gradient. Users can click to emit a
    visible impulse ring that applies force to nearby dominoes, causing them to topple realistically.

    Attributes:
        master (tk.Tk): The root Tkinter window.
        screen_width (int): Width of the simulation window in pixels.
        screen_height (int): Height of the simulation window in pixels.
        canvas (tk.Canvas): The drawing canvas for rendering objects.
        world (b2World): The Box2D physics world with gravity and dynamics.
        platforms (list): List of static platform bodies.
        dominos (list): List of (body, color) tuples for dynamic domino bodies.
        impulse_rings (list): Expanding visual rings representing impulse events.
        domino_half_width (float): Half-width of a domino in world units.
        domino_half_height (float): Half-height of a domino in world units.
    """
    def __init__(self, master):
        self.master = master
        self.screen_width = 800
        self.screen_height = 350
        self.canvas = tk.Canvas(self.master, width=self.screen_width, height=self.screen_height)
        self.canvas.pack()

        self.world = b2World(gravity=(0.0, -10.0), doSleep=True)

        self.platforms = []
        self.dominos = []
        self.impulse_rings = []

        self.create_platforms()
        self.create_dominos()

        self.domino_half_width = (10 / PPM) / 2
        self.domino_half_height = (50 / PPM) / 2

        self.canvas.bind('<Button-1>', self.apply_impulse)

        self.update()

    def create_platforms(self):
        """Creates three evenly spaced static horizontal platforms at different heights"""

        # Determine platform dimensions in screen units
        platform_width = self.screen_width / 3
        platform_height = 20

        for i in range(3):
            # Convert platform position to world coordinates (centered and staggered vertically)
            platform_x = (i + 0.5) * platform_width / PPM
            platform_y = (self.screen_height - (i + 1) * 100) / PPM

            # Define static body for platform
            body_def = b2BodyDef(position=(platform_x, platform_y), type=b2_staticBody)
            body = self.world.CreateBody(body_def)

            # Create fixture shape and attach to body
            fixture_def = b2FixtureDef(shape=b2PolygonShape(box=(platform_width / 2 / PPM,
                                                                 platform_height / 2 / PPM)))
            body.CreateFixture(fixture_def)
            self.platforms.append(body)

    def create_dominos(self):
        """
        Creates a row of upright dynamic domino bodies on each platform. Dominoes are spaced evenly
        and colored with a horizontal gradient from blue to red.
        """
        self.dominos = []
        for i, platform in enumerate(self.platforms):
            # Determine how many dominoes fit on each platform
            num_dominos = int(self.screen_width / 3 / (DOMINO_WIDTH + DOMINO_SPACING))

            for j in range(num_dominos):
                # Calculate world-space position for each domino
                domino_x = (platform.position.x + (j - num_dominos // 2) *
                            (DOMINO_WIDTH + DOMINO_SPACING) / PPM)
                domino_y = platform.position.y + DOMINO_HEIGHT / 2 / PPM

                # Define and create dynamic body for the domino
                body_def = b2BodyDef(position=(domino_x, domino_y), type=b2_dynamicBody)
                body = self.world.CreateBody(body_def)

                # Define and attach a rectangular fixture to represent the domino
                fixture_def = b2FixtureDef(shape=b2PolygonShape(box=(DOMINO_WIDTH / 2 / PPM,
                                                                     DOMINO_HEIGHT / 2 / PPM)),
                                           density=1.0, friction=0.7)
                body.CreateFixture(fixture_def)

                # Calculate gradient color
                gradient_ratio = j / max(num_dominos - 1, 1)
                red = int(gradient_ratio * 255)
                blue = 255 - red
                color = f'#{red:02x}00{blue:02x}'

                self.dominos.append((body, color))

    def apply_impulse(self, event):
        """
        Applies an outward radial impulse to any domino within a certain radius of the click point.
        Also spawns a visual impulse ring at the click location.
        """
        # Convert screen coordinates to world coordinates
        x = event.x / PPM
        y = (self.screen_height - event.y) / PPM

        for domino, _ in self.dominos:
            # Compute distance from click to domino center
            dx = domino.position.x - x
            dy = domino.position.y - y
            distance = math.sqrt(dx ** 2 + dy ** 2)

            # Apply impulse if within ring radius
            if distance < MAX_RING_RADIUS / PPM:
                impulse = (dx / distance * IMPULSE_FORCE, dy / distance * IMPULSE_FORCE)
                domino.ApplyLinearImpulse(impulse, domino.position, True)

        self.impulse_rings.append({'x': event.x, 'y': event.y, 'radius': 0})

    def update(self):
        """
        Advances the physics simulation, redraws the scene, updates impulse rings, and schedules
        the next frame. Handles rendering of platforms, dominos, and impulse effects.
        """
        # Step the physics simulation forward and clear the canvas before redrawing
        self.world.Step(TIME_STEP, VELOCITY_ITERATIONS, POSITION_ITERATIONS)
        self.canvas.delete('all')

        # Update and draw expanding impulse rings
        ring_growth_rate = MAX_RING_RADIUS / (TARGET_FPS * 0.5)
        for ring in self.impulse_rings[:]:
            r = ring['radius']
            self.canvas.create_oval(
                ring['x']-r, ring['y']-r,
                ring['x']+r, ring['y']+r,
                outline='red'
            )
            ring['radius'] += ring_growth_rate
            if ring['radius'] >= MAX_RING_RADIUS:
                self.impulse_rings.remove(ring)

        # Draw each static platform as a gray rectangle
        for platform in self.platforms:
            x = platform.position.x * PPM
            y = self.screen_height - platform.position.y * PPM
            width = self.screen_width / 3
            height = 20
            self.canvas.create_rectangle(x - width / 2, y - height / 2, x + width / 2,
                                         y + height / 2, fill='gray')

        # Draw each domino polygon with its gradient color
        for domino, color in self.dominos:
            height_x = self.domino_half_width
            height_y = self.domino_half_height
            vertices = [
                domino.GetWorldPoint(b2Vec2(dx, dy))
                for dx, dy in [(-height_x, -height_y), (height_x, -height_y),
                               (height_x, height_y), (-height_x, height_y)]
            ]
            screen_coordinates = []
            for v in vertices:
                screen_coordinates += [v.x * PPM, self.screen_height - v.y * PPM]
            self.canvas.create_polygon(screen_coordinates, fill=color)

        # Schedule the next frame update
        self.master.after(1000 // TARGET_FPS, self.update)


root = tk.Tk()
app = DominoApp(root)
root.mainloop()
