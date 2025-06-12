import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import matplotlib.patches as patches

# Constants
BOX_SIZE = 10.0
PARTICLE_RADIUS = 0.1
PARTICLE_MASS = 1.0
NUM_PARTICLES = 100
TEMPERATURE = 1.0
TIME_STEP = 0.01

def update(frame):
    # Update positions and velocities including wall and inter-particle collisions.
    global positions
    positions += velocities * TIME_STEP

    # Reflect and reposition inside the box when collisions occur.
    for i in range(NUM_PARTICLES):
        # Check x-boundaries
        if positions[i, 0] - PARTICLE_RADIUS < 0:
            positions[i, 0] = PARTICLE_RADIUS
            velocities[i, 0] = -velocities[i, 0]
        elif positions[i, 0] + PARTICLE_RADIUS > BOX_SIZE:
            positions[i, 0] = BOX_SIZE - PARTICLE_RADIUS
            velocities[i, 0] = -velocities[i, 0]

        # Check y-boundaries
        if positions[i, 1] - PARTICLE_RADIUS < 0:
            positions[i, 1] = PARTICLE_RADIUS
            velocities[i, 1] = -velocities[i, 1]
        elif positions[i, 1] + PARTICLE_RADIUS > BOX_SIZE:
            positions[i, 1] = BOX_SIZE - PARTICLE_RADIUS
            velocities[i, 1] = -velocities[i, 1]

    # Handle particle–particle collisions using velocity projection.
    for i in range(NUM_PARTICLES):
        for j in range(i + 1, NUM_PARTICLES):
            delta_pos = positions[i] - positions[j]
            distance = np.linalg.norm(delta_pos)
            if distance < 2 * PARTICLE_RADIUS:
                delta_v = velocities[i] - velocities[j]

                # Check if particles are moving toward each other
                if np.dot(delta_v, delta_pos) < 0:
                    unit_normal = delta_pos / distance
                    v_rel = np.dot(delta_v, unit_normal)

                    # Update velocities along the normal direction
                    velocities[i] -= v_rel * unit_normal
                    velocities[j] += v_rel * unit_normal

    # Update particle positions on the left plot without clearing the axis.
    for i, circle in enumerate(particle_circles):
        circle.center = positions[i]

    # Update the velocity distribution on the right plot.
    ax2.cla()  # Clear the axis so that the histogram does not accumulate.
    ax2.set_title('Velocity Distribution')
    ax2.set_xlim(0, 5)
    ax2.set_ylim(0, 1)
    ax2.set_xlabel('Speed')
    ax2.set_ylabel('Probability Density')

    # Compute absolute speeds from velocities
    speeds = np.linalg.norm(velocities, axis=1)
    ax2.hist(speeds, bins=30, density=True, alpha=0.5, label='Simulation')
    ax2.plot(v_vals, maxwell, 'r-', label='Maxwell-Boltzmann')
    ax2.legend()

# Initialize particle positions (with margin to avoid walls initially) and velocities
np.random.seed(0)
positions = np.random.uniform(PARTICLE_RADIUS, BOX_SIZE - PARTICLE_RADIUS, size=(NUM_PARTICLES, 2))
velocities = np.random.normal(0, np.sqrt(TEMPERATURE), size=(NUM_PARTICLES, 2))

# Create figure and subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

# Set up left plot (particle motion)
ax1.set_xlim(0, BOX_SIZE)
ax1.set_ylim(0, BOX_SIZE)
ax1.set_aspect('equal')
ax1.set_title('Particle Motion')

# Create circles once for each particle and add them to the axis
particle_circles = []
for pos in positions:
    circle = patches.Circle(pos, PARTICLE_RADIUS, fill=False, edgecolor='b')
    ax1.add_patch(circle)
    particle_circles.append(circle)

# Set up right plot (velocity distribution)
ax2.set_title('Velocity Distribution')
ax2.set_xlim(0, 5)
ax2.set_ylim(0, 1)
ax2.set_xlabel('Speed')
ax2.set_ylabel('Probability Density')

# Create an array for the Maxwell–Boltzmann overlay.
v_vals = np.linspace(0, 5, 100)

# 2D Maxwell–Boltzmann speed distribution (unnormalized form):
maxwell = (v_vals / TEMPERATURE) * np.exp(-v_vals ** 2 / (2 * TEMPERATURE))

# Create and save the animation
ani = FuncAnimation(fig, update, frames=range(200), interval=50)
ani.save('my_animation.gif', writer=PillowWriter(fps=15))

plt.show()
