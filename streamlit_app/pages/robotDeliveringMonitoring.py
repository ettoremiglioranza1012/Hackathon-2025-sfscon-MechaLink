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


def load_movement_data(limit=None):
    """Carica i dati di movimento dal database."""
    with psycopg.connect(PG_DSN) as conn:
        query = """
            SELECT trace_id, message, code, point_name, point_id, 
                   floor, position_x, position_y, position_z, inserted_at
            FROM robot_movement
            WHERE message = 'SUCCESS'
            ORDER BY inserted_at ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn)
        return df


def generate_area_info(df):
    """Genera dinamicamente le informazioni dell'area dai dati di movimento."""
    if df.empty:
        return {
            'area_id': 'N/A',
            'area_name': 'restaurant',
            'area_size': 150.0,
            'delivery_count': 0,
            'area_type': 'Restaurant',
            'code': 'N/A',
            'task_id': 'N/A'
        }
    
    # Calcola l'area approssimativa dai dati
    x_range = df['position_x'].max() - df['position_x'].min()
    y_range = df['position_y'].max() - df['position_y'].min()
    area_size = max(x_range * y_range, 100.0)  # Minimo 100 m²
    
    # Conta i punti unici come numero di consegne
    delivery_count = df['point_name'].nunique()
    
    # Prendi il code dal primo record
    code_value = df.iloc[0]['code'] if 'code' in df.columns and not df.empty else 'N/A'
    
    return {
        'area_id': f"auto-{code_value}-{hash(str(code_value)) % 100000:05d}",
        'area_name': 'restaurant',
        'area_size': round(area_size, 1),
        'delivery_count': delivery_count,
        'area_type': 'Restaurant',
        'code': code_value,
        'task_id': f"task-{df.iloc[0]['trace_id']}" if 'trace_id' in df.columns else 'N/A'
    }


def calculate_map_bounds(df):
    """Calcola i limiti della mappa dai dati."""
    if df.empty:
        return 0, 10, 0, 10
    
    x_min = df['position_x'].min()
    x_max = df['position_x'].max()
    y_min = df['position_y'].min()
    y_max = df['position_y'].max()
    
    # Aggiungi un po' di padding (10%)
    x_padding = (x_max - x_min) * 0.1
    y_padding = (y_max - y_min) * 0.1
    
    return (
        x_min - x_padding,
        x_max + x_padding,
        y_min - y_padding,
        y_max + y_padding
    )


def normalize_coordinates(x, y, config):
    """Normalizza le coordinate logiche in coordinate pixel."""
    x_min, x_max = config['x_min'], config['x_max']
    y_min, y_max = config['y_min'], config['y_max']
    width = config['image_width']
    height = config['image_height']
    
    # Normalizza 0-1
    x_norm = (x - x_min) / (x_max - x_min) if (x_max - x_min) > 0 else 0.5
    y_norm = (y - y_min) / (y_max - y_min) if (y_max - y_min) > 0 else 0.5
    
    # Converti in pixel (invertendo Y perché le immagini hanno origine in alto)
    x_px = x_norm * width
    y_px = (1 - y_norm) * height
    
    return x_px, y_px


def generate_restaurant_layout(area_size, width_px=800, height_px=600):
    """Genera layout SVG di un ristorante basato sull'area reale."""
    import plotly.graph_objects as go
    
    # Calcola dimensioni reali in metri (assumendo forma rettangolare con ratio 3:2)
    ratio = 1.5
    width_m = math.sqrt(area_size * ratio)
    height_m = math.sqrt(area_size / ratio)
    
    # Scala: pixel per metro
    scale_x = width_px / width_m
    scale_y = height_px / height_m
    
    fig = go.Figure()
    
    # === MURI PERIMETRALI ===
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=width_px, y1=height_px,
        line=dict(color="black", width=4),
        fillcolor="rgba(245, 240, 230, 0.5)"  # Colore crema per ristorante
    )
    
    # === PORTA D'INGRESSO PRINCIPALE ===
    door_width = 1.5 * scale_x  # Porta larga 1.5m
    door_x = width_px * 0.05
    fig.add_shape(
        type="rect",
        x0=door_x, y0=0, x1=door_x + door_width, y1=10,
        line=dict(color="brown", width=3),
        fillcolor="rgba(139, 69, 19, 0.5)"
    )
    fig.add_annotation(
        x=door_x + door_width/2, y=20,
        text="🚪 Ingresso",
        showarrow=False,
        font=dict(size=12)
    )
    
    # === CUCINA (Kitchen Area) ===
    kitchen_w = width_px * 0.3
    kitchen_h = height_px * 0.35
    kitchen_x = width_px * 0.65
    kitchen_y = height_px * 0.05
    
    fig.add_shape(
        type="rect",
        x0=kitchen_x, y0=kitchen_y,
        x1=kitchen_x + kitchen_w, y1=kitchen_y + kitchen_h,
        line=dict(color="darkred", width=3),
        fillcolor="rgba(255, 69, 0, 0.15)"
    )
    fig.add_annotation(
        x=kitchen_x + kitchen_w/2, y=kitchen_y + kitchen_h/2 - 20,
        text="👨‍🍳",
        showarrow=False,
        font=dict(size=30)
    )
    fig.add_annotation(
        x=kitchen_x + kitchen_w/2, y=kitchen_y + kitchen_h/2 + 20,
        text="CUCINA",
        showarrow=False,
        font=dict(size=14, color="darkred", family="Arial Black")
    )
    
    # === TAVOLI RISTORANTE ===
    # Dimensioni tavolo: 1.2m x 0.8m (tavolo per 4 persone)
    table_w = 1.2 * scale_x
    table_h = 0.8 * scale_y
    
    # Numero di tavoli basato sull'area
    num_tables = max(6, min(12, int(area_size / 20)))
    
    tables_per_row = 3
    rows = (num_tables + tables_per_row - 1) // tables_per_row
    
    table_positions = []
    
    for i in range(num_tables):
        row = i // tables_per_row
        col = i % tables_per_row
        
        # Distribuisci i tavoli nella parte sinistra/centrale
        table_x = width_px * (0.08 + col * 0.2)
        table_y = height_px * (0.15 + row * 0.28)
        
        table_positions.append((table_x, table_y))
        
        # Tavolo (legno marrone)
        fig.add_shape(
            type="rect",
            x0=table_x, y0=table_y,
            x1=table_x + table_w, y1=table_y + table_h,
            line=dict(color="saddlebrown", width=2),
            fillcolor="rgba(160, 82, 45, 0.6)"
        )
        
        # Numero tavolo
        fig.add_annotation(
            x=table_x + table_w/2,
            y=table_y + table_h/2,
            text=f"T{i+1}",
            showarrow=False,
            font=dict(size=10, color="white", family="Arial Black")
        )
        
        # Sedie intorno al tavolo (4 sedie)
        chair_size = 8
        # Sedia sopra
        fig.add_shape(
            type="circle",
            x0=table_x + table_w/2 - chair_size, y0=table_y - chair_size*2,
            x1=table_x + table_w/2 + chair_size, y1=table_y,
            fillcolor="rgba(101, 67, 33, 0.7)",
            line=dict(color="saddlebrown", width=1)
        )
        # Sedia sotto
        fig.add_shape(
            type="circle",
            x0=table_x + table_w/2 - chair_size, y0=table_y + table_h,
            x1=table_x + table_w/2 + chair_size, y1=table_y + table_h + chair_size*2,
            fillcolor="rgba(101, 67, 33, 0.7)",
            line=dict(color="saddlebrown", width=1)
        )
        # Sedia sinistra
        fig.add_shape(
            type="circle",
            x0=table_x - chair_size*2, y0=table_y + table_h/2 - chair_size,
            x1=table_x, y1=table_y + table_h/2 + chair_size,
            fillcolor="rgba(101, 67, 33, 0.7)",
            line=dict(color="saddlebrown", width=1)
        )
        # Sedia destra
        fig.add_shape(
            type="circle",
            x0=table_x + table_w, y0=table_y + table_h/2 - chair_size,
            x1=table_x + table_w + chair_size*2, y1=table_y + table_h/2 + chair_size,
            fillcolor="rgba(101, 67, 33, 0.7)",
            line=dict(color="saddlebrown", width=1)
        )
    
    # === BAR/BANCONE ===
    bar_w = width_px * 0.35
    bar_h = height_px * 0.12
    bar_x = width_px * 0.6
    bar_y = height_px * 0.65
    
    fig.add_shape(
        type="rect",
        x0=bar_x, y0=bar_y,
        x1=bar_x + bar_w, y1=bar_y + bar_h,
        line=dict(color="darkgoldenrod", width=3),
        fillcolor="rgba(184, 134, 11, 0.4)"
    )
    fig.add_annotation(
        x=bar_x + bar_w/2, y=bar_y + bar_h/2,
        text="🍷 BAR",
        showarrow=False,
        font=dict(size=14, color="white", family="Arial Black")
    )
    
    # === AREA CASSA ===
    cashier_size = 0.6 * scale_x
    cashier_x = width_px * 0.1
    cashier_y = height_px * 0.85
    
    fig.add_shape(
        type="rect",
        x0=cashier_x, y0=cashier_y,
        x1=cashier_x + cashier_size, y1=cashier_y + cashier_size * 0.6,
        line=dict(color="darkgreen", width=2),
        fillcolor="rgba(0, 100, 0, 0.3)"
    )
    fig.add_annotation(
        x=cashier_x + cashier_size/2, y=cashier_y + cashier_size * 0.3,
        text="💳",
        showarrow=False,
        font=dict(size=18)
    )
    
    # === PIANTE DECORATIVE ===
    plant_positions = [
        (width_px * 0.05, height_px * 0.5),
        (width_px * 0.05, height_px * 0.3),
        (width_px * 0.55, height_px * 0.15),
        (width_px * 0.55, height_px * 0.5),
    ]
    
    for plant_x, plant_y in plant_positions:
        fig.add_annotation(
            x=plant_x, y=plant_y,
            text="🪴",
            showarrow=False,
            font=dict(size=20)
        )
    
    # === PORTA CUCINA (passaggio staff) ===
    kitchen_door_w = 0.9 * scale_x
    kitchen_door_x = kitchen_x - 5
    kitchen_door_y = kitchen_y + kitchen_h * 0.4
    
    fig.add_shape(
        type="rect",
        x0=kitchen_door_x, y0=kitchen_door_y,
        x1=kitchen_door_x + 10, y1=kitchen_door_y + kitchen_door_w,
        line=dict(color="red", width=2, dash="dash"),
        fillcolor="rgba(255, 0, 0, 0.1)"
    )
    
    # === SCALA E LEGENDA ===
    # Scala metri
    scale_bar_length = 2 * scale_x  # 2 metri
    scale_y_pos = height_px - 30
    
    fig.add_shape(
        type="line",
        x0=20, y0=scale_y_pos,
        x1=20 + scale_bar_length, y1=scale_y_pos,
        line=dict(color="black", width=3)
    )
    fig.add_annotation(
        x=20 + scale_bar_length/2, y=scale_y_pos - 15,
        text="2m",
        showarrow=False,
        font=dict(size=10, color="black")
    )
    
    # Dimensioni sala
    fig.add_annotation(
        x=width_px - 80, y=30,
	        text=f"{width_m:.1f}m × {height_m:.1f}m<br>{area_size:.1f}m²",
        showarrow=False,
        font=dict(size=11, color="black"),
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="black",
        borderwidth=1
    )
    
    # Info ristorante
    fig.add_annotation(
        x=width_px/2, y=15,
        text="🍽️ RISTORANTE - ZONA SERVIZIO",
        showarrow=False,
        font=dict(size=14, color="darkred", family="Arial Black"),
        bgcolor="rgba(255, 255, 200, 0.8)",
        bordercolor="darkred",
        borderwidth=2,
        borderpad=8
    )
    
    return fig, width_m, height_m


def create_map_with_area(step_data, area_info, config, show_trail=True, trail_data=None, all_movement_data=None):
    """Crea mappa con area ristorante e sovrappone movimento robot."""
    import plotly.graph_objects as go
    
    # Genera layout ristorante
    fig, width_m, height_m = generate_restaurant_layout(
        area_info['area_size'],
        config['image_width'],
        config['image_height']
    )
    
    # === CALCOLA I BOUNDS REALI DAI DATI ===
    if all_movement_data is not None and not all_movement_data.empty:
        x_min, x_max, y_min, y_max = calculate_map_bounds(all_movement_data)
    elif trail_data is not None and not trail_data.empty:
        x_min, x_max, y_min, y_max = calculate_map_bounds(trail_data)
    elif step_data is not None:
        x_min = step_data['position_x'] - 1
        x_max = step_data['position_x'] + 1
        y_min = step_data['position_y'] - 1
        y_max = step_data['position_y'] + 1
    else:
        x_min, x_max, y_min, y_max = 0, width_m, 0, height_m
    
    # Aggiorna config
    config['width_m'] = width_m
    config['height_m'] = height_m
    config['x_min'] = x_min
    config['x_max'] = x_max
    config['y_min'] = y_min
    config['y_max'] = y_max
    
    # === TRAIL DEL ROBOT ===
    if show_trail and trail_data is not None and len(trail_data) > 0:
        trail_x = []
        trail_y = []
        for _, row in trail_data.iterrows():
            x_px, y_px = normalize_coordinates(row['position_x'], row['position_y'], config)
            trail_x.append(x_px)
            trail_y.append(y_px)
        
        fig.add_trace(go.Scatter(
            x=trail_x,
            y=trail_y,
            mode='lines+markers',
            line=dict(color='rgba(255, 140, 0, 0.6)', width=3),
            marker=dict(size=4, color='rgba(255, 140, 0, 0.4)'),
            name='Trail',
            showlegend=False
        ))
    
    # === POSIZIONE ROBOT CORRENTE ===
    if step_data is not None:
        x_px, y_px = normalize_coordinates(
            step_data['position_x'],
            step_data['position_y'],
            config
        )
        
        # Calcola direzione
        import math
        direction_angle = 0
        
        if trail_data is not None and len(trail_data) > 1:
            prev_point = trail_data.iloc[-2]
            curr_point = trail_data.iloc[-1]
            
            dx = curr_point['position_x'] - prev_point['position_x']
            dy = curr_point['position_y'] - prev_point['position_y']
            
            if dx != 0 or dy != 0:
                direction_angle = math.degrees(math.atan2(-dy, dx))
        
        # Alone/campo di visione del robot
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px],
            mode='markers',
            marker=dict(size=35, color='rgba(255, 165, 0, 0.15)', symbol='circle'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Corpo del robot - colore arancione per delivery
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px],
            mode='markers',
            marker=dict(
                size=25,
                color='#FF8C00',
                symbol='circle',
                line=dict(color='#FF6600', width=3)
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Indicatore di direzione - freccia
        arrow_length = 18
        arrow_x = x_px + arrow_length * math.cos(math.radians(direction_angle))
        arrow_y = y_px - arrow_length * math.sin(math.radians(direction_angle))
        
        fig.add_shape(
            type="line",
            x0=x_px, y0=y_px,
            x1=arrow_x, y1=arrow_y,
            line=dict(color='white', width=4)
        )
        
        # Punta della freccia
        arrow_tip_size = 8
        angle_rad = math.radians(direction_angle)
        
        tip_x = arrow_x
        tip_y = arrow_y
        
        left_angle = angle_rad + math.radians(150)
        right_angle = angle_rad - math.radians(150)
        
        base_left_x = arrow_x + arrow_tip_size * math.cos(left_angle)
        base_left_y = arrow_y - arrow_tip_size * math.sin(left_angle)
        
        base_right_x = arrow_x + arrow_tip_size * math.cos(right_angle)
        base_right_y = arrow_y - arrow_tip_size * math.sin(right_angle)
        
        fig.add_trace(go.Scatter(
            x=[tip_x, base_left_x, base_right_x, tip_x],
            y=[tip_y, base_left_y, base_right_y, tip_y],
            fill='toself',
            fillcolor='white',
            line=dict(color='white', width=0),
            mode='lines',
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Emoji robot delivery
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px],
            mode='text',
            text=['🤖'],
            textposition='middle center',
            textfont=dict(size=14),
            name='Robot',
            showlegend=False,
            hovertemplate=f"<b>{step_data['point_name']}</b><br>" +
                         f"X: {step_data['position_x']:.2f}m<br>" +
                         f"Y: {step_data['position_y']:.2f}m<br>" +
                         f"Direction: {direction_angle:.1f}°<extra></extra>"
        ))
        
        # === INDICATORI DI STATO ===
        status_y_offset = 35
        
        # Icona consegna (🍕)
        fig.add_trace(go.Scatter(
            x=[x_px - 25],
            y=[y_px - status_y_offset],
            mode='text',
            text=['🍕'],
            textfont=dict(size=18),
            showlegend=False,
            hovertemplate='<b>Delivery Mode</b><extra></extra>'
        ))
        
        # Icona batteria
        battery_icon = '🔋'
        if trail_data is not None and all_movement_data is not None:
            progress = len(trail_data) / len(all_movement_data)
            if progress > 0.7:
                battery_icon = '🪫'
            elif progress > 0.4:
                battery_icon = '🔋'
        
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px - status_y_offset],
            mode='text',
            text=[battery_icon],
            textfont=dict(size=18),
            showlegend=False,
            hovertemplate='<b>Battery Status</b><extra></extra>'
        ))
        
        # Icona stato (consegna in corso / pausa)
        status_icon = '🚚'
        if trail_data is not None and all_movement_data is not None:
            progress = len(trail_data) / len(all_movement_data)
            if 0.48 <= progress <= 0.52:
                status_icon = '⏸️'
        
        fig.add_trace(go.Scatter(
            x=[x_px + 25],
            y=[y_px - status_y_offset],
            mode='text',
            text=[status_icon],
            textfont=dict(size=18),
            showlegend=False,
            hovertemplate='<b>Status</b><extra></extra>'
        ))
    
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
        plot_bgcolor='rgba(250, 248, 240, 1)',
        margin=dict(l=0, r=0, t=0, b=0),
        hovermode='closest'
    )
    
    return fig


def robot_delivering_monitor():
    """Funzione principale per il monitoring dei robot di consegna."""
    st.title("🍕 Robot Delivering Monitor")
    st.markdown("---")
    
    # Inizializza session state
    if 'delivery_steps' not in st.session_state:
        st.session_state.delivery_steps = None
    if 'delivery_idx' not in st.session_state:
        st.session_state.delivery_idx = 0
    if 'delivery_data_loaded' not in st.session_state:
        st.session_state.delivery_data_loaded = False
    if 'delivery_area_info' not in st.session_state:
        st.session_state.delivery_area_info = None
    
    # Sidebar controls
    st.sidebar.header("⚙️ Controls")
    
    # Carica dati
    if st.sidebar.button("🔄 Load Data", type="primary"):
        with st.spinner("Loading movement data from database..."):
            # Carica movimenti robot
            df = load_movement_data()
            if not df.empty:
                st.session_state.delivery_steps = df
                st.session_state.delivery_data_loaded = True
                st.session_state.delivery_idx = 0
                
                # Genera info area dinamicamente
                area_info = generate_area_info(df)
                st.session_state.delivery_area_info = area_info
                
                st.sidebar.success(f"✅ Loaded {len(df)} movement points!")
                st.sidebar.info(f"📍 Generated area info - Code: {area_info['code']}")
            else:
                st.sidebar.warning(f"⚠️ No movement data found in database")
    
    if not st.session_state.delivery_data_loaded or st.session_state.delivery_steps is None:
        st.info("👆 Click 'Load Data' in the sidebar to start")
        
        # Show preview
        st.markdown("""
        ### 🍽️ About Robot Delivering Monitor
        
        This dashboard visualizes robot delivery movements in real-time from the database.
        
        **Features:**
        - 🗺️ **Interactive restaurant floor plan** with realistic layout
        - 🍕 **Delivery tracking** between kitchen and tables
        - ▶️ **Play/Pause animation** with speed control
        - 🔄 **Timeline navigation** and trail visualization
        - 📊 **Real-time position tracking** with coordinates
        - 📐 **Automatic scaling** based on movement data
        - 🎯 **Dynamic area generation** from movement data
        
        **Select a map and click 'Load Data' to begin!**
        """)
        
        # Try to show available maps
        try:
            with psycopg.connect(PG_DSN) as conn:
                maps_df = pd.read_sql_query(
                    "SELECT DISTINCT code, COUNT(*) as point_count FROM robot_movement WHERE message = 'SUCCESS' GROUP BY code",
                    conn
                )
                if not maps_df.empty:
                    st.markdown("### 📋 Available Codes")
                    st.dataframe(maps_df, use_container_width=True)
        except:
            pass
        
        return
    
    # === AREA INFO DISPLAY ===
    area_info = st.session_state.delivery_area_info
    
    # CSS Style
    st.markdown("""
    <style>
    .area-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
        <h1 class="area-title">🍽️ {area_info['area_name'].title()} - Delivery Zone</h1>
        <p class="area-subtitle">Real-time delivery robot monitoring • Code: {area_info['code']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar controls
    st.sidebar.markdown("---")
    
    # Show trail toggle
    show_trail = st.sidebar.checkbox("Show Trail", value=True)
    
    # Progress info
    total_steps = len(st.session_state.delivery_steps)
    st.sidebar.markdown("---")
    st.sidebar.metric("Total Steps", total_steps)
    st.sidebar.metric("Current Step", st.session_state.delivery_idx + 1)
    
    # Progress bar
    progress_percent = (st.session_state.delivery_idx + 1) / total_steps
    st.sidebar.progress(progress_percent, text=f"Progress: {progress_percent*100:.1f}%")
    
    # Timeline slider
    st.sidebar.markdown("---")
    new_idx = st.sidebar.slider(
        "Timeline",
        min_value=0,
        max_value=total_steps - 1,
        value=st.session_state.delivery_idx,
        key="delivery_timeline_slider"
    )
    
    if new_idx != st.session_state.delivery_idx:
        st.session_state.delivery_idx = new_idx
    
    # Main content
    df = st.session_state.delivery_steps
    current_idx = st.session_state.delivery_idx
    
    # Get current step data
    current_step = df.iloc[current_idx]
    
    # Get trail data if enabled
    trail_data = None
    if show_trail and current_idx > 0:
        trail_data = df.iloc[:current_idx + 1]
    
    # Create and display map
    config = MAP_CONFIG["default"].copy()
    config['image_width'] = 800
    config['image_height'] = 450
    fig = create_map_with_area(
        current_step, 
        area_info, 
        config, 
        show_trail, 
        trail_data,
        all_movement_data=df
    )
    st.plotly_chart(fig, use_container_width=True, key=f"delivery_map_{current_idx}")
    
    # Legend
    st.caption("**Legend:** 🍽️ Tables | 👨‍🍳 Kitchen | 🍷 Bar | 💳 Cashier | 🪴 Plants | 🤖 Robot | 🟠 Trail")
    
    # Metrics banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📏</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Area Size</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{area_info['area_size']:.1f} m²</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🆔</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Area ID</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">...{area_info['area_id'][-8:]}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🍕</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Deliveries</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{area_info['delivery_count']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🗺️</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Code</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{area_info.get('code', 'N/A')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Current position banner
    timestamp = current_step['inserted_at']
    if isinstance(timestamp, pd.Timestamp):
        timestamp = timestamp.strftime("%H:%M:%S")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📍</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Point Name</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['point_name']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🔢</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Point ID</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['point_id']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🏢</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Floor</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['floor']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">⏰</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Time</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{timestamp}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Coordinates banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: grid; 
                    grid-template-columns: repeat(3, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📐</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">X Position</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['position_x']:.3f} m</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📐</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Y Position</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['position_y']:.3f} m</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.3); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">📐</div>
                <div style="color: #2c3e50; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Z Position</div>
                <div style="color: #2c3e50; font-size: 24px; font-weight: bold;">{current_step['position_z']:.3f} m</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Debug info
    if st.sidebar.checkbox("Show Debug Info", value=False):
        st.sidebar.json({
            "current_idx": current_idx,
            "total_steps": total_steps,
            "config_bounds": {
                "x": [config.get('x_min'), config.get('x_max')],
                "y": [config.get('y_min'), config.get('y_max')]
            },
            "current_position": {
                "x": float(current_step['position_x']),
                "y": float(current_step['position_y'])
            },
            "generated_area_info": area_info
        })


# Entry point
def render():
    """Entry point for the page when called from main app."""
    robot_delivering_monitor()


if __name__ == "__main__":
    robot_delivering_monitor()