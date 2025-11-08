import streamlit as st
import psycopg
import pandas as pd
from PIL import Image
import io
import time
import math
from datetime import datetime
import os

# Database connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mydb")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
PG_DSN = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

# Map configuration
MAP_CONFIG = {
    "default": {
        "name": "default",
        "image_width": 1200,
        "image_height": 675,
        # These will be calculated from data
        "x_min": 0,
        "x_max": 10,
        "y_min": 0,
        "y_max": 10,
    }
}


def load_lifting_data(limit=None):
    """Carica i dati di sollevamento dal database."""
    with psycopg.connect(PG_DSN) as conn:
        query = """
            SELECT id, arrival_time, begin_time, cur_duration, cur_mileage,
                   destination, mac, product_code, robot_name, shop_id,
                   shop_name, sn, stay_duration, task_time, inserted_at
            FROM robot_industrial_lifting_task
            ORDER BY arrival_time ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn)
        return df


def generate_lifting_info(df):
    """Genera dinamicamente le informazioni dell'area dai dati di sollevamento."""
    if df.empty:
        return {
            'area_id': 'N/A',
            'area_name': 'industrial_warehouse',
            'total_lifts': 0,
            'total_duration': 0,
            'total_mileage': 0,
            'robot_name': 'N/A',
            'shop_id': 'N/A',
            'shop_name': 'N/A',
            'area_type': 'Industrial'
        }
    
    # Statistiche dai dati
    total_lifts = len(df)
    total_duration = df['cur_duration'].sum() if 'cur_duration' in df.columns else 0
    total_mileage = df['cur_mileage'].sum() if 'cur_mileage' in df.columns else 0
    robot_name = df.iloc[0]['robot_name'] if 'robot_name' in df.columns and not df.empty else 'N/A'
    shop_id = df.iloc[0]['shop_id'] if 'shop_id' in df.columns and not df.empty else 'N/A'
    shop_name = df.iloc[0]['shop_name'] if 'shop_name' in df.columns and not df.empty else 'N/A'
    
    return {
        'area_id': f"warehouse-{shop_id}",
        'area_name': 'industrial_warehouse',
        'total_lifts': total_lifts,
        'total_duration': round(total_duration, 2),
        'total_mileage': round(total_mileage, 2),
        'robot_name': robot_name,
        'shop_id': shop_id,
        'shop_name': shop_name,
        'area_type': 'Industrial'
    }


def generate_industrial_warehouse_layout(width_px=800, height_px=600):
    """Genera layout SVG di un magazzino industriale."""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # === PAVIMENTO INDUSTRIALE ===
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=width_px, y1=height_px,
        line=dict(color="black", width=4),
        fillcolor="rgba(200, 200, 200, 0.3)"  # Grigio cemento
    )
    
    # Linee di marcatura pavimento (stile industriale)
    for i in range(5):
        y_pos = height_px * (0.2 * i + 0.1)
        fig.add_shape(
            type="line",
            x0=0, y0=y_pos, x1=width_px, y1=y_pos,
            line=dict(color="rgba(255, 255, 0, 0.3)", width=2, dash="dash")
        )
    
    # === AREA DI CARICO (sinistra) ===
    loading_w = width_px * 0.25
    loading_h = height_px * 0.4
    loading_x = width_px * 0.05
    loading_y = height_px * 0.3
    
    fig.add_shape(
        type="rect",
        x0=loading_x, y0=loading_y,
        x1=loading_x + loading_w, y1=loading_y + loading_h,
        line=dict(color="orange", width=3),
        fillcolor="rgba(255, 165, 0, 0.2)"
    )
    fig.add_annotation(
        x=loading_x + loading_w/2, y=loading_y + loading_h/2 - 20,
        text="📦",
        showarrow=False,
        font=dict(size=40)
    )
    fig.add_annotation(
        x=loading_x + loading_w/2, y=loading_y + loading_h/2 + 30,
        text="LOADING ZONE",
        showarrow=False,
        font=dict(size=12, color="orange", family="Arial Black")
    )
    
    # === SCAFFALATURE (centro-destra) ===
    shelf_w = width_px * 0.15
    shelf_h = height_px * 0.5
    
    # Scaffale 1
    shelf1_x = width_px * 0.4
    shelf1_y = height_px * 0.15
    
    fig.add_shape(
        type="rect",
        x0=shelf1_x, y0=shelf1_y,
        x1=shelf1_x + shelf_w, y1=shelf1_y + shelf_h,
        line=dict(color="darkblue", width=3),
        fillcolor="rgba(0, 0, 139, 0.3)"
    )
    
    # Ripiani scaffale
    for i in range(4):
        y_shelf = shelf1_y + (shelf_h / 4) * i
        fig.add_shape(
            type="line",
            x0=shelf1_x, y0=y_shelf,
            x1=shelf1_x + shelf_w, y1=y_shelf,
            line=dict(color="darkblue", width=2)
        )
    
    fig.add_annotation(
        x=shelf1_x + shelf_w/2, y=shelf1_y - 20,
        text="RACK A",
        showarrow=False,
        font=dict(size=10, color="darkblue", family="Arial Black")
    )
    
    # Scaffale 2
    shelf2_x = width_px * 0.6
    shelf2_y = height_px * 0.15
    
    fig.add_shape(
        type="rect",
        x0=shelf2_x, y0=shelf2_y,
        x1=shelf2_x + shelf_w, y1=shelf2_y + shelf_h,
        line=dict(color="darkblue", width=3),
        fillcolor="rgba(0, 0, 139, 0.3)"
    )
    
    # Ripiani scaffale
    for i in range(4):
        y_shelf = shelf2_y + (shelf_h / 4) * i
        fig.add_shape(
            type="line",
            x0=shelf2_x, y0=y_shelf,
            x1=shelf2_x + shelf_w, y1=y_shelf,
            line=dict(color="darkblue", width=2)
        )
    
    fig.add_annotation(
        x=shelf2_x + shelf_w/2, y=shelf2_y - 20,
        text="RACK B",
        showarrow=False,
        font=dict(size=10, color="darkblue", family="Arial Black")
    )
    
    # Scaffale 3
    shelf3_x = width_px * 0.8
    shelf3_y = height_px * 0.15
    
    fig.add_shape(
        type="rect",
        x0=shelf3_x, y0=shelf3_y,
        x1=shelf3_x + shelf_w * 0.6, y1=shelf3_y + shelf_h,
        line=dict(color="darkblue", width=3),
        fillcolor="rgba(0, 0, 139, 0.3)"
    )
    
    # Ripiani scaffale
    for i in range(4):
        y_shelf = shelf3_y + (shelf_h / 4) * i
        fig.add_shape(
            type="line",
            x0=shelf3_x, y0=y_shelf,
            x1=shelf3_x + shelf_w * 0.6, y1=y_shelf,
            line=dict(color="darkblue", width=2)
        )
    
    fig.add_annotation(
        x=shelf3_x + (shelf_w * 0.6)/2, y=shelf3_y - 20,
        text="RACK C",
        showarrow=False,
        font=dict(size=10, color="darkblue", family="Arial Black")
    )
    
    # === AREA DI SCARICO (angolo in alto a destra) ===
    unloading_w = width_px * 0.2
    unloading_h = height_px * 0.15
    unloading_x = width_px * 0.75
    unloading_y = height_px * 0.8
    
    fig.add_shape(
        type="rect",
        x0=unloading_x, y0=unloading_y,
        x1=unloading_x + unloading_w, y1=unloading_y + unloading_h,
        line=dict(color="green", width=3),
        fillcolor="rgba(0, 255, 0, 0.15)"
    )
    fig.add_annotation(
        x=unloading_x + unloading_w/2, y=unloading_y + unloading_h/2,
        text="🚚 UNLOADING",
        showarrow=False,
        font=dict(size=11, color="green", family="Arial Black")
    )
    
    # === STAZIONE DI CONTROLLO ===
    control_x = width_px * 0.05
    control_y = height_px * 0.05
    control_size = 60
    
    fig.add_shape(
        type="rect",
        x0=control_x, y0=control_y,
        x1=control_x + control_size, y1=control_y + control_size,
        line=dict(color="red", width=2),
        fillcolor="rgba(255, 0, 0, 0.2)"
    )
    fig.add_annotation(
        x=control_x + control_size/2, y=control_y + control_size/2,
        text="🖥️",
        showarrow=False,
        font=dict(size=20)
    )
    
    # === PALLET E MATERIALI ===
    pallet_positions = [
        (width_px * 0.1, height_px * 0.8, "🟫"),
        (width_px * 0.15, height_px * 0.8, "🟫"),
        (width_px * 0.2, height_px * 0.85, "📦"),
        (width_px * 0.35, height_px * 0.75, "📦"),
    ]
    
    for pallet_x, pallet_y, icon in pallet_positions:
        fig.add_annotation(
            x=pallet_x, y=pallet_y,
            text=icon,
            showarrow=False,
            font=dict(size=25)
        )
    
    # === SEGNALETICA DI SICUREZZA ===
    # Strisce gialle di sicurezza
    for i in range(3):
        x_stripe = width_px * (0.32 + i * 0.01)
        fig.add_shape(
            type="rect",
            x0=x_stripe, y0=0,
            x1=x_stripe + 5, y1=height_px,
            fillcolor="rgba(255, 255, 0, 0.5)",
            line=dict(width=0)
        )
    
    # === CARTELLI ===
    fig.add_annotation(
        x=width_px - 60, y=30,
        text="⚠️ ROBOT<br>ZONE",
        showarrow=False,
        font=dict(size=10, color="red", family="Arial Black"),
        bgcolor="rgba(255, 255, 0, 0.8)",
        bordercolor="red",
        borderwidth=2
    )
    
    # === TITOLO WAREHOUSE ===
    fig.add_annotation(
        x=width_px/2, y=20,
        text="🏭 INDUSTRIAL WAREHOUSE - AUTOMATED LIFTING ZONE",
        showarrow=False,
        font=dict(size=14, color="black", family="Arial Black"),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="black",
        borderwidth=2,
        borderpad=8
    )
    
    return fig


def create_lifting_visualization(task_data, lifting_info, config, current_phase="idle"):
    """Crea visualizzazione del magazzino con robot di sollevamento."""
    import plotly.graph_objects as go
    
    # Genera layout magazzino
    fig = generate_industrial_warehouse_layout(
        config['image_width'],
        config['image_height']
    )
    
    # === POSIZIONE ROBOT INDUSTRIALE ===
    # Il robot si posiziona in base alla destinazione e alla fase
    width_px = config['image_width']
    height_px = config['image_height']
    
    # Determina posizione in base alla destinazione
    if task_data is not None and 'destination' in task_data:
        destination = task_data['destination']
        
        # Mappa delle destinazioni
        dest_positions = {
            'home': (width_px * 0.25, height_px * 0.5),
            'carta': (width_px * 0.45, height_px * 0.4),
            'warehouse': (width_px * 0.5, height_px * 0.5),
            'rack_a': (width_px * 0.47, height_px * 0.4),
            'rack_b': (width_px * 0.67, height_px * 0.4),
            'rack_c': (width_px * 0.85, height_px * 0.4),
            'loading': (width_px * 0.175, height_px * 0.5),
            'unloading': (width_px * 0.85, height_px * 0.875),
        }
        
        # Prova a trovare la posizione, altrimenti usa default
        dest_lower = str(destination).lower() if destination else 'home'
        robot_x, robot_y = dest_positions.get(dest_lower, (width_px * 0.3, height_px * 0.5))
    else:
        robot_x, robot_y = width_px * 0.3, height_px * 0.5
    
    # === ROBOT INDUSTRIALE (braccio robotico) ===
    # Base del robot
    base_size = 40
    fig.add_shape(
        type="rect",
        x0=robot_x - base_size/2, y0=robot_y,
        x1=robot_x + base_size/2, y1=robot_y + base_size,
        line=dict(color="darkslategray", width=3),
        fillcolor="rgba(47, 79, 79, 0.8)"
    )
    
    # Braccio robotico - varia altezza in base alla fase
    arm_height = 60  # Default
    lift_offset = 0
    
    if current_phase == "lifting":
        lift_offset = -30  # Braccio sollevato
    elif current_phase == "moving":
        lift_offset = -20  # Braccio in movimento
    elif current_phase == "lowering":
        lift_offset = -10  # Braccio che scende
    
    arm_y = robot_y - arm_height + lift_offset
    
    # Braccio principale
    fig.add_shape(
        type="rect",
        x0=robot_x - 8, y0=arm_y,
        x1=robot_x + 8, y1=robot_y,
        line=dict(color="orange", width=2),
        fillcolor="rgba(255, 140, 0, 0.9)"
    )
    
    # Giunto
    fig.add_shape(
        type="circle",
        x0=robot_x - 12, y0=arm_y - 12,
        x1=robot_x + 12, y1=arm_y + 12,
        line=dict(color="black", width=2),
        fillcolor="rgba(255, 165, 0, 1)"
    )
    
    # Pinza/gripper
    gripper_width = 30
    fig.add_shape(
        type="rect",
        x0=robot_x - gripper_width/2, y0=arm_y - 15,
        x1=robot_x + gripper_width/2, y1=arm_y - 5,
        line=dict(color="black", width=2),
        fillcolor="rgba(128, 128, 128, 0.9)"
    )
    
    # Dita della pinza (aperte/chiuse in base alla fase)
    gripper_open = 15 if current_phase in ["idle", "moving"] else 5
    
    # Dito sinistro
    fig.add_shape(
        type="rect",
        x0=robot_x - gripper_width/2 - gripper_open, y0=arm_y - 25,
        x1=robot_x - gripper_width/2, y1=arm_y - 5,
        line=dict(color="black", width=1),
        fillcolor="rgba(100, 100, 100, 0.9)"
    )
    
    # Dito destro
    fig.add_shape(
        type="rect",
        x0=robot_x + gripper_width/2, y0=arm_y - 25,
        x1=robot_x + gripper_width/2 + gripper_open, y1=arm_y - 5,
        line=dict(color="black", width=1),
        fillcolor="rgba(100, 100, 100, 0.9)"
    )
    
    # === CARICO (se in fase di sollevamento) ===
    if current_phase in ["lifting", "moving", "lowering"] and task_data is not None:
        load_y = arm_y - 35 if current_phase == "lifting" else arm_y - 30
        
        fig.add_shape(
            type="rect",
            x0=robot_x - 20, y0=load_y,
            x1=robot_x + 20, y1=load_y + 25,
            line=dict(color="brown", width=2),
            fillcolor="rgba(139, 69, 19, 0.7)"
        )
        
        # Etichetta prodotto
        if 'product_code' in task_data:
            product_code = str(task_data['product_code'])[-4:] if task_data['product_code'] else "XXXX"
            fig.add_annotation(
                x=robot_x, y=load_y + 12,
                text=product_code,
                showarrow=False,
                font=dict(size=8, color="white", family="Courier New")
            )
    
    # === INDICATORI DI STATO ===
    status_y = robot_y - arm_height - 50
    
    # Fase corrente
    phase_colors = {
        "idle": "🟢",
        "lifting": "🟡",
        "moving": "🔵",
        "lowering": "🟠",
        "completed": "✅"
    }
    
    phase_icon = phase_colors.get(current_phase, "⚪")
    
    fig.add_trace(go.Scatter(
        x=[robot_x],
        y=[status_y],
        mode='text',
        text=[phase_icon],
        textfont=dict(size=20),
        showlegend=False,
        hovertemplate=f'<b>Phase: {current_phase.upper()}</b><extra></extra>'
    ))
    
    # Label robot
    fig.add_annotation(
        x=robot_x, y=robot_y + base_size + 15,
        text=f"🤖 {lifting_info.get('robot_name', 'Robot')}",
        showarrow=False,
        font=dict(size=11, color="darkslategray", family="Arial Black"),
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="darkslategray",
        borderwidth=1
    )
    
    # === TRAIETTORIA (se in movimento) ===
    if current_phase == "moving" and task_data is not None:
        # Disegna linea tratteggiata dalla loading zone alla destinazione
        start_x, start_y = width_px * 0.175, height_px * 0.5
        
        fig.add_shape(
            type="line",
            x0=start_x, y0=start_y,
            x1=robot_x, y1=robot_y,
            line=dict(color="rgba(0, 0, 255, 0.5)", width=2, dash="dash")
        )
    
    # Layout
    fig.update_layout(
        width=config['image_width'],
        height=config['image_height'],
        xaxis=dict(
            range=[0, config['image_width']],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            range=[0, config['image_height']],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='rgba(240, 240, 240, 1)',
        margin=dict(l=0, r=0, t=0, b=0),
        hovermode='closest'
    )
    
    return fig


def robot_industrial_lifting():
    """Funzione principale per il monitoring del robot industriale di sollevamento."""
    st.title("🏭 Robot Industrial Lifting Monitor")
    st.markdown("---")
    
    # Inizializza session state
    if 'lifting_tasks' not in st.session_state:
        st.session_state.lifting_tasks = None
    if 'lifting_idx' not in st.session_state:
        st.session_state.lifting_idx = 0
    if 'lifting_data_loaded' not in st.session_state:
        st.session_state.lifting_data_loaded = False
    if 'lifting_info' not in st.session_state:
        st.session_state.lifting_info = None
    
    # Sidebar controls
    st.sidebar.header("⚙️ Controls")
    
    # Carica dati
    if st.sidebar.button("🔄 Load Data", type="primary"):
        with st.spinner("Loading lifting tasks from database..."):
            # Carica task di sollevamento
            df = load_lifting_data()
            if not df.empty:
                st.session_state.lifting_tasks = df
                st.session_state.lifting_data_loaded = True
                st.session_state.lifting_idx = 0
                
                # Genera info area dinamicamente
                lifting_info = generate_lifting_info(df)
                st.session_state.lifting_info = lifting_info
                
                st.sidebar.success(f"✅ Loaded {len(df)} lifting tasks!")
                st.sidebar.info(f"🤖 Robot: {lifting_info['robot_name']}")
            else:
                st.sidebar.warning(f"⚠️ No lifting tasks found in database")
    
    if not st.session_state.lifting_data_loaded or st.session_state.lifting_tasks is None:
        st.info("👆 Click 'Load Data' in the sidebar to start")
        
        # Show preview
        st.markdown("""
        ### 🏭 About Robot Industrial Lifting Monitor
        
        This dashboard visualizes industrial robot lifting operations in real-time from the database.
        
        **Features:**
        - 🏭 **Industrial warehouse floor plan** with realistic layout
        - 🤖 **Robotic arm visualization** with lifting animation
        - 📦 **Load tracking** and product identification
        - ⏱️ **Duration monitoring** for each lifting task
        - 📊 **Real-time status** with phase indicators
        - 🎯 **Destination tracking** (racks, loading/unloading zones)
        
        **Load data to monitor automated lifting operations!**
        """)
        
        # Try to show available data
        try:
            with psycopg.connect(PG_DSN) as conn:
                preview_df = pd.read_sql_query(
                    "SELECT robot_name, COUNT(*) as task_count, SUM(cur_duration) as total_duration FROM robot_industrial_lifting_task GROUP BY robot_name",
                    conn
                )
                if not preview_df.empty:
                    st.markdown("### 📋 Available Robots")
                    st.dataframe(preview_df, use_container_width=True)
        except:
            pass
        
        return
    
    # === LIFTING INFO DISPLAY ===
    lifting_info = st.session_state.lifting_info
    
    # CSS Style
    st.markdown("""
    <style>
    .area-header {
        background: linear-gradient(135deg, #434343 0%, #000000 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .area-title {
        color: white;
        font-size: 28px;
        font-weight: bold;
        margin: 0;
    }
    .area-subtitle {
        color: rgba(255, 255, 255, 0.8);
        font-size: 14px;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Area header
    st.markdown(f"""
    <div class="area-header">
        <h1 class="area-title">🏭 {lifting_info.get('shop_name', 'Industrial Warehouse')} - Lifting Operations</h1>
        <p class="area-subtitle">Automated lifting robot monitoring • Robot: {lifting_info['robot_name']} • Shop ID: {lifting_info['shop_id']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar controls
    st.sidebar.markdown("---")
    
    # Animation control
    animation_speed = st.sidebar.slider("Animation Speed", 1, 10, 5)
    
    # Progress info
    total_tasks = len(st.session_state.lifting_tasks)
    st.sidebar.markdown("---")
    st.sidebar.metric("Total Tasks", total_tasks)
    st.sidebar.metric("Current Task", st.session_state.lifting_idx + 1)
    
    # Progress bar
    progress_percent = (st.session_state.lifting_idx + 1) / total_tasks
    st.sidebar.progress(progress_percent, text=f"Progress: {progress_percent*100:.1f}%")
    
    # Timeline slider
    st.sidebar.markdown("---")
    new_idx = st.sidebar.slider(
        "Task Timeline",
        min_value=0,
        max_value=total_tasks - 1,
        value=st.session_state.lifting_idx,
        key="lifting_timeline_slider"
    )
    
    if new_idx != st.session_state.lifting_idx:
        st.session_state.lifting_idx = new_idx
    
    # Main content
    df = st.session_state.lifting_tasks
    current_idx = st.session_state.lifting_idx
    
    # Get current task data
    current_task = df.iloc[current_idx]
    
    # Determina la fase corrente in base alla durata
    # Simuliamo le fasi: idle -> lifting -> moving -> lowering -> completed
    if pd.isna(current_task.get('cur_duration')) or current_task.get('cur_duration') == 0:
        current_phase = "idle"
    elif current_task.get('cur_duration') < 5:
        current_phase = "lifting"
    elif current_task.get('cur_duration') < 10:
        current_phase = "moving"
    elif current_task.get('cur_duration') < 13:
        current_phase = "lowering"
    else:
        current_phase = "completed"
    
    # Create and display warehouse visualization
    config = MAP_CONFIG["default"].copy()
    config['image_width'] = 800
    config['image_height'] = 450
    fig = create_lifting_visualization(
        current_task, 
        lifting_info, 
        config,
        current_phase
    )
    st.plotly_chart(fig, use_container_width=True, key=f"lifting_viz_{current_idx}")
    
    # Legend
    st.caption("**Legend:** 🏭 Warehouse | 📦 Loading Zone | 🚚 Unloading | 🤖 Robot | 🟫 Pallets | ⚠️ Safety Zone")
    
    # Metrics banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(5, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🏋️</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Total Lifts</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{lifting_info['total_lifts']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">⏱️</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Total Duration</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{lifting_info['total_duration']:.1f}s</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📏</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Total Mileage</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{lifting_info['total_mileage']:.1f}m</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🤖</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Robot Name</div>
                <div style="color: white; font-size: 20px; font-weight: bold;">{lifting_info['robot_name']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🏪</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Shop Name</div>
                <div style="color: white; font-size: 18px; font-weight: bold;">{lifting_info.get('shop_name', 'N/A')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Current task banner
    arrival_time = current_task['arrival_time']
    begin_time = current_task.get('begin_time')
    task_time = current_task.get('task_time')
    
    if isinstance(arrival_time, pd.Timestamp):
        arrival_time = arrival_time.strftime("%H:%M:%S")
    elif pd.isna(arrival_time):
        arrival_time = "N/A"
    
    if isinstance(begin_time, pd.Timestamp):
        begin_time = begin_time.strftime("%H:%M:%S")
    elif pd.isna(begin_time):
        begin_time = "N/A"
        
    if isinstance(task_time, pd.Timestamp):
        task_time = task_time.strftime("%H:%M:%S")
    elif pd.isna(task_time):
        task_time = "N/A"
    
    # Phase badge
    phase_badges = {
        "idle": "🟢 IDLE",
        "lifting": "🟡 LIFTING",
        "moving": "🔵 MOVING",
        "lowering": "🟠 LOWERING",
        "completed": "✅ COMPLETED"
    }
    phase_display = phase_badges.get(current_phase, "⚪ UNKNOWN")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(5, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🆔</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Task ID</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_task.get('id', 'N/A')}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📍</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Destination</div>
                <div style="color: #2c3e50; font-size: 20px; font-weight: bold;">{current_task.get('destination', 'N/A')}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📦</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Product Code</div>
                <div style="color: #2c3e50; font-size: 18px; font-weight: bold;">{current_task.get('product_code', 'N/A')}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🔄</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Phase</div>
                <div style="color: #2c3e50; font-size: 16px; font-weight: bold;">{phase_display}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
	                <div style="font-size: 24px; margin-bottom: 5px;"><3E></div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Serial Number</div>
                <div style="color: #2c3e50; font-size: 14px; font-weight: bold;">{current_task.get('sn', 'N/A')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Timing details banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">⏰</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Arrival Time</div>
                <div style="color: #2c3e50; font-size: 20px; font-weight: bold;">{arrival_time if arrival_time else 'N/A'}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
	                <div style="font-size: 24px; margin-bottom: 5px;"><3E></div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Robot Name</div>
                <div style="color: #2c3e50; font-size: 18px; font-weight: bold;">{current_task.get('robot_name', 'N/A')}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">⏳</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">TUR Duration</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_task.get('tur_duration', 0):.2f}s</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📊</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">CUR Duration</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_task.get('cur_duration', 0):.2f}s</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Debug info
    if st.sidebar.checkbox("Show Debug Info", value=False):
        st.sidebar.json({
            "current_idx": current_idx,
            "total_tasks": total_tasks,
            "current_phase": current_phase,
            "task_data": {
                "destination": str(current_task.get('destination')),
                "product_code": str(current_task.get('product_code')),
                "cur_duration": float(current_task.get('cur_duration', 0)),
                "tur_duration": float(current_task.get('tur_duration', 0))
            },
            "lifting_info": lifting_info
        })


# Entry point
def render():
    """Entry point for the page when called from main app."""
    robot_industrial_lifting()


if __name__ == "__main__":
    robot_industrial_lifting()