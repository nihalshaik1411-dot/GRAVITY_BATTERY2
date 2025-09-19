import streamlit as st
import time
import plotly.graph_objects as go

st.set_page_config(page_title="Gravity Battery - Seesaw Simulation", layout="wide")

# ---------- CONFIG ----------
FRAME_DELAY = 0.08   # seconds per animation frame (lower = faster)
GRAVITY = 9.81      # m/s²
HEIGHT = 100        # m (from +50m to -50m)
B1_CAPACITY = 100_000  # Joules (100 kJ for Battery 1)
B2_CAPACITY = 1_000_000  # Joules (1 MJ for Battery 2)
STORAGE_THRESHOLD = 80  # kg to trigger big cycle
MAX_TOTAL_BLOCKS = 20  # Max blocks (200kg) at A and B combined

# ---------- SESSION STATE ----------
if "blocks_top_A" not in st.session_state:
    st.session_state.blocks_top_A = 1
if "blocks_top_B" not in st.session_state:
    st.session_state.blocks_top_B = 2
if "tied_bottom_C" not in st.session_state:
    st.session_state.tied_bottom_C = 0
if "tied_bottom_D" not in st.session_state:
    st.session_state.tied_bottom_D = 0
if "storage_left" not in st.session_state:
    st.session_state.storage_left = 0
if "storage_right" not in st.session_state:
    st.session_state.storage_right = 0
if "battery1" not in st.session_state:
    st.session_state.battery1 = 0
if "battery2" not in st.session_state:
    st.session_state.battery2 = 0
if "generator_angle" not in st.session_state:
    st.session_state.generator_angle = 0
if "houses_lit" not in st.session_state:
    st.session_state.houses_lit = False
if "running" not in st.session_state:
    st.session_state.running = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "step_count" not in st.session_state:
    st.session_state.step_count = 0

# ---------- DRAW / ANIMATION HELPERS ----------
def draw_scene(dropping=None, drop_y=None, dropping_size=10, note=""):
    fig = go.Figure()
    # Ground line
    fig.add_shape(type="line", x0=-3, y0=0, x1=3, y1=0, line=dict(color="black", width=3))
    # Labels
    fig.add_annotation(x=-1.8, y=55, text="A (+50m)", showarrow=False)
    fig.add_annotation(x=1.8, y=55, text="B (+50m)", showarrow=False)
    fig.add_annotation(x=-1.8, y=-55, text="C (−50m)", showarrow=False)
    fig.add_annotation(x=1.8, y=-55, text="D (−50m)", showarrow=False)

    # Blocks at top
    for i in range(st.session_state.blocks_top_A):
        y0 = 50 + i * 1.05
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5, y0=y0, y1=y0 + 0.95,
                      fillcolor="#2b6cb0", line=dict(color="black"))
    for i in range(st.session_state.blocks_top_B):
        y0 = 50 + i * 1.05
        fig.add_shape(type="rect", x0=1.5, x1=2.1, y0=y0, y1=y0 + 0.95,
                      fillcolor="#c53030", line=dict(color="black"))

    # Tied at bottom
    if st.session_state.tied_bottom_C > 0:
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5, y0=-51, y1=-50.05,
                      fillcolor="gray", line=dict(color="black"))
    if st.session_state.tied_bottom_D > 0:
        fig.add_shape(type="rect", x0=1.5, x1=2.1, y0=-51, y1=-50.05,
                      fillcolor="gray", line=dict(color="black"))

    # Storage
    num_stored_left = st.session_state.storage_left // 10
    for i in range(num_stored_left):
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5,
                      y0=-52 - i * 1.05, y1=-51 - i * 1.05,
                      fillcolor="#dd6b20", line=dict(color="black"))
    num_stored_right = st.session_state.storage_right // 10
    for i in range(num_stored_right):
        fig.add_shape(type="rect", x0=1.5, x1=2.1,
                      y0=-52 - i * 1.05, y1=-51 - i * 1.05,
                      fillcolor="#dd6b20", line=dict(color="black"))

    # Dropping / lifting block
    if dropping and drop_y is not None:
        pt, color = dropping
        if pt == "left":
            x0, x1 = -2.1, -1.5
        elif pt == "right":
            x0, x1 = 1.5, 2.1
        elif pt == "BIG":
            x0, x1 = -1.2, 1.2
        else:
            x0, x1 = -0.6, 0.6
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=drop_y, y1=drop_y + 0.95,
                      fillcolor=color, line=dict(color="black"))
        fig.add_annotation(x=0, y=drop_y + 1.2,
                           text=f"{'Moving' if start_y < end_y else 'Dropping'}: {dropping_size}kg",
                           showarrow=False)

    # Generator
    angle = st.session_state.generator_angle % 360
    fig.add_shape(type="circle", x0=-0.4, y0=-20.6, x1=0.4, y1=-21.6,
                  line=dict(color="orange", width=3))
    fig.add_annotation(x=0, y=-21.1, text=f"⚙ {angle:.0f}°",
                       showarrow=False, font=dict(color="orange"))

    # Battery labels
    fig.add_annotation(x=-2.7, y=45,
                       text=f"🔋 B1: {st.session_state.battery1:.0f}%", showarrow=False)
    fig.add_annotation(x=2.7, y=45,
                       text=f"🔋 B2: {st.session_state.battery2:.0f}%", showarrow=False)

    # Houses
    houses_text = "🏠 lit" if st.session_state.houses_lit else "🏠 dark"
    fig.add_annotation(x=0, y=45, text=houses_text, showarrow=False)

    fig.update_xaxes(visible=False, range=[-4, 4])
    fig.update_yaxes(visible=False, range=[-65, 65])
    fig.update_layout(height=600, margin=dict(l=10, r=10, t=10, b=10), autosize=True)
    return fig

def animate_fall(placeholder, pt, color="#2b6cb0", start_y=50, end_y=-50, steps=50, size_kg=20):
    """Animate downward movement (discharge)."""
    for step in range(steps):
        if st.session_state.stop_requested:
            return False
        t = step / (steps - 1)
        y = start_y + (end_y - start_y) * t
        fig = draw_scene(dropping=(pt, color), drop_y=y, dropping_size=size_kg)
        placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(FRAME_DELAY)
    return True

def animate_lift(placeholder, pt, color="#2b6cb0", start_y=-50, end_y=50, steps=50, size_kg=20):
    """Animate upward movement (charging)."""
    for step in range(steps):
        if st.session_state.stop_requested:
            return False
        t = step / (steps - 1)
        y = start_y + (end_y - start_y) * t
        fig = draw_scene(dropping=(pt, color), drop_y=y, dropping_size=size_kg)
        placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(FRAME_DELAY)
    return True

# ---------- MAIN UI ----------
st.title("⚡ Gravity Battery — Seesaw Continuous Simulation")

left_col, mid_col, right_col = st.columns([1, 2, 1])

with left_col:
    st.subheader("Controls")
    if st.button("Start"):
        st.session_state.running = True
        st.session_state.stop_requested = False
        st.session_state.logs = []
        st.session_state.step_count = 0
    if st.button("Stop"):
        st.session_state.stop_requested = True
        st.session_state.running = False

    st.write("Initial top stacks (editable, max 200kg total):")
    blocks_a = st.number_input("Blocks at top A (10kg each)", min_value=0, max_value=MAX_TOTAL_BLOCKS,
                               value=st.session_state.blocks_top_A, step=1)
    blocks_b = st.number_input("Blocks at top B (10kg each)", min_value=0, max_value=MAX_TOTAL_BLOCKS,
                               value=st.session_state.blocks_top_B, step=1)
    if blocks_a + blocks_b <= MAX_TOTAL_BLOCKS:
        st.session_state.blocks_top_A = blocks_a
        st.session_state.blocks_top_B = blocks_b
    else:
        st.error(f"Total blocks (A + B) must not exceed {MAX_TOTAL_BLOCKS} (200kg).")

with mid_col:
    scene_ph = st.empty()

with right_col:
    st.subheader("Status")
    st.write(f"Step: {st.session_state.step_count}")
    st.write(f"Top A: {st.session_state.blocks_top_A * 10} kg")
    st.write(f"Top B: {st.session_state.blocks_top_B * 10} kg")
    st.write(f"Tied at C: {st.session_state.tied_bottom_C * 10} kg")
    st.write(f"Tied at D: {st.session_state.tied_bottom_D * 10} kg")
    st.write(f"Storage left (C): {st.session_state.storage_left} kg")
    st.write(f"Storage right (D): {st.session_state.storage_right} kg")
    st.write(f"Battery B1: {st.session_state.battery1:.0f}%")
    st.write(f"Battery B2: {st.session_state.battery2:.0f}%")

# Initial scene
scene_ph.plotly_chart(draw_scene(), use_container_width=True)

# ---------- SIMULATION STEP ----------
if st.session_state.running and not st.session_state.stop_requested:
    dropped = False
    lifted = 0

    st.session_state.step_count += 1

    # Drop from A → C, lift D → B
    if st.session_state.blocks_top_A == 2 and st.session_state.blocks_top_B < 2:
        animate_fall(scene_ph, "left", color="#2b6cb0", steps=50, size_kg=20)
        st.session_state.blocks_top_A = 0
        st.session_state.storage_left += 10
        st.session_state.tied_bottom_C += 1
        lifted = st.session_state.tied_bottom_D
        if lifted > 0:
            animate_lift(scene_ph, "right", color="#c53030", steps=50, size_kg=lifted * 10)
        st.session_state.blocks_top_B += lifted
        st.session_state.tied_bottom_D = 0
        dropped = True

    # Drop from B → D, lift C → A
    elif st.session_state.blocks_top_B == 2 and st.session_state.blocks_top_A < 2:
        animate_fall(scene_ph, "right", color="#c53030", steps=50, size_kg=20)
        st.session_state.blocks_top_B = 0
        st.session_state.storage_right += 10
        st.session_state.tied_bottom_D += 1
        lifted = st.session_state.tied_bottom_C
        if lifted > 0:
            animate_lift(scene_ph, "left", color="#2b6cb0", steps=50, size_kg=lifted * 10)
        st.session_state.blocks_top_A += lifted
        st.session_state.tied_bottom_C = 0
        dropped = True

    # (same alternating case for both sides == 2, just add animate_lift like above...)

    # Update scene
    scene_ph.plotly_chart(draw_scene(), use_container_width=True)
    time.sleep(0.4)

    st.rerun()

# ---------- Logs ----------
st.subheader("Simulation Steps & Events")
st.text_area("Simulation Log", value="\n".join(st.session_state.logs), height=300, disabled=True)
