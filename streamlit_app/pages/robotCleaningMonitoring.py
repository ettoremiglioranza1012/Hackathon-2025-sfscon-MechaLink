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
    "MainHall": {
        "name": "MainHall",
        "image_width": 1200,
        "image_height": 675,
        # These will be calculated from data
        "x_min": 0,
        "x_max": 10,
        "y_min": 0,
        "y_max": 10,
    }
}


def load_movement_data(map_name="MainHall", limit=None):
    """Carica i dati di movimento dal database."""
    with psycopg.connect(PG_DSN) as conn:
        query = """
            SELECT trace_id, message, code, map_name, point_name, point_id, 
                   floor, position_x, position_y, position_z, inserted_at
            FROM robot_movement
            WHERE message = 'SUCCESS' AND code = 0 AND map_name = %s
            ORDER BY inserted_at ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn, params=(map_name,))
        return df


def load_cleaning_area(area_name='biliardo'):
    """Carica i dati dell'area di pulizia dal database."""
    with psycopg.connect(PG_DSN) as conn:
        query = """
            SELECT area_id, area_name, area_size, clean_count, 
                   area_type, map_name, task_id
            FROM cleaning_area
            WHERE area_name = %s
            LIMIT 1
        """
        df = pd.read_sql_query(query, conn, params=(area_name,))
        if not df.empty:
            return df.iloc[0].to_dict()
        return None


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


def generate_billiard_room_layout(area_size, width_px=800, height_px=600):
    """Genera layout SVG di una sala biliardo basato sull'area reale."""
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
        fillcolor="rgba(240, 240, 240, 0.3)"
    )
    
    # === PORTA D'INGRESSO ===
    door_width = 1.2 * scale_x  # Porta larga 1.2m
    door_x = width_px * 0.1
    fig.add_shape(
        type="rect",
        x0=door_x, y0=0, x1=door_x + door_width, y1=10,
        line=dict(color="brown", width=3),
        fillcolor="rgba(139, 69, 19, 0.5)"
    )
    fig.add_annotation(
        x=door_x + door_width/2, y=20,
        text="🚪",
        showarrow=False,
        font=dict(size=20)
    )
    
    # === TAVOLI DA BILIARDO ===
    # Dimensioni standard tavolo: 2.84m x 1.42m
    table_w = 2.84 * scale_x
    table_h = 1.42 * scale_y
    
    # Numero di tavoli basato sull'area
    num_tables = max(2, min(4, int(area_size / 30)))
    
    for i in range(num_tables):
        if num_tables == 2:
            table_x = width_px * (0.2 + i * 0.45)
            table_y = height_px * 0.3
        elif num_tables == 3:
            row = i // 2
            col = i % 2
            table_x = width_px * (0.15 + col * 0.5)
            table_y = height_px * (0.25 + row * 0.45)
        else:
            row = i // 2
            col = i % 2
            table_x = width_px * (0.15 + col * 0.45)
            table_y = height_px * (0.2 + row * 0.4)
        
        # Tavolo (feltro verde)
        fig.add_shape(
            type="rect",
            x0=table_x, y0=table_y,
            x1=table_x + table_w, y1=table_y + table_h,
            line=dict(color="darkgreen", width=3),
            fillcolor="rgba(0, 128, 0, 0.7)"
        )
        
        # Bordo tavolo (legno scuro)
        fig.add_shape(
            type="rect",
            x0=table_x - 5, y0=table_y - 5,
            x1=table_x + table_w + 5, y1=table_y + table_h + 5,
            line=dict(color="saddlebrown", width=2),
            fillcolor="rgba(139, 69, 19, 0.3)"
        )
        
        # Label tavolo
        fig.add_annotation(
            x=table_x + table_w/2,
            y=table_y + table_h/2,
            text=f"🎱 Table {i+1}",
            showarrow=False,
            font=dict(size=10, color="white")
        )
    
    # === AREA BAR/RISTORO ===
    bar_w = width_px * 0.25
    bar_h = height_px * 0.15
    bar_x = width_px * 0.7
    bar_y = height_px * 0.75
    
    fig.add_shape(
        type="rect",
        x0=bar_x, y0=bar_y,
        x1=bar_x + bar_w, y1=bar_y + bar_h,
        line=dict(color="darkslategray", width=2),
        fillcolor="rgba(70, 130, 180, 0.4)"
    )
    fig.add_annotation(
        x=bar_x + bar_w/2, y=bar_y + bar_h/2,
        text="☕ Bar",
        showarrow=False,
        font=dict(size=12, color="white")
    )
    
    # === SEDIE/PANCHE ===
    chair_positions = [
        (width_px * 0.1, height_px * 0.7),
        (width_px * 0.15, height_px * 0.7),
        (width_px * 0.2, height_px * 0.7),
        (width_px * 0.1, height_px * 0.8),
        (width_px * 0.15, height_px * 0.8),
    ]
    
    for chair_x, chair_y in chair_positions:
        fig.add_shape(
            type="circle",
            x0=chair_x - 10, y0=chair_y - 10,
            x1=chair_x + 10, y1=chair_y + 10,
            line=dict(color="gray", width=1),
            fillcolor="rgba(128, 128, 128, 0.5)"
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
    
    return fig, width_m, height_m


def create_map_with_area(step_data, area_info, config, show_trail=True, trail_data=None, all_movement_data=None):
    """Crea mappa con area biliardo e sovrappone movimento robot."""
    import plotly.graph_objects as go
    
    # Genera layout sala biliardo
    fig, width_m, height_m = generate_billiard_room_layout(
        area_info['area_size'],
        config['image_width'],
        config['image_height']
    )
    
    # === CALCOLA I BOUNDS REALI DAI DATI ===
    # Usa TUTTI i dati di movimento per calcolare i bounds corretti
    if all_movement_data is not None and not all_movement_data.empty:
        x_min, x_max, y_min, y_max = calculate_map_bounds(all_movement_data)
    elif trail_data is not None and not trail_data.empty:
        x_min, x_max, y_min, y_max = calculate_map_bounds(trail_data)
    elif step_data is not None:
        # Fallback: usa solo il punto corrente con padding
        x_min = step_data['position_x'] - 1
        x_max = step_data['position_x'] + 1
        y_min = step_data['position_y'] - 1
        y_max = step_data['position_y'] + 1
    else:
        # Default fallback
        x_min, x_max, y_min, y_max = 0, width_m, 0, height_m
    
    # Aggiorna config con dimensioni reali DAI DATI (non dall'area)
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
            line=dict(color='rgba(50, 100, 255, 0.6)', width=3),
            marker=dict(size=4, color='rgba(50, 100, 255, 0.4)'),
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
        
        # Calcola direzione del movimento
        import math
        direction_angle = 0  # Default: verso destra
        
        if trail_data is not None and len(trail_data) > 1:
            # Prendi gli ultimi 2 punti per calcolare la direzione
            prev_point = trail_data.iloc[-2]
            curr_point = trail_data.iloc[-1]
            
            dx = curr_point['position_x'] - prev_point['position_x']
            dy = curr_point['position_y'] - prev_point['position_y']
            
            if dx != 0 or dy != 0:
                # Calcola angolo in gradi (correggi per sistema coordinate immagine)
                direction_angle = math.degrees(math.atan2(-dy, dx))  # -dy perché Y è invertito
        
        # Alone/campo di visione del robot
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px],
            mode='markers',
            marker=dict(size=35, color='rgba(100, 150, 255, 0.15)', symbol='circle'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Corpo del robot - forma personalizzata (cerchio con bordo spesso)
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px],
            mode='markers',
            marker=dict(
                size=25,
                color='#FF4444',
                symbol='circle',
                line=dict(color='#CC0000', width=3)
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Indicatore di direzione - freccia direzionale
        arrow_length = 18
        arrow_x = x_px + arrow_length * math.cos(math.radians(direction_angle))
        arrow_y = y_px - arrow_length * math.sin(math.radians(direction_angle))  # -sin per Y invertito
        
        # Linea freccia (corpo)
        fig.add_shape(
            type="line",
            x0=x_px, y0=y_px,
            x1=arrow_x, y1=arrow_y,
            line=dict(color='white', width=4)
        )
        
        # Punta della freccia (triangolo)
        arrow_tip_size = 8
        angle_rad = math.radians(direction_angle)
        
        # Vertici del triangolo della freccia
        tip_x = arrow_x
        tip_y = arrow_y
        
        # Punti base del triangolo (angoli di 150° rispetto alla direzione)
        left_angle = angle_rad + math.radians(150)
        right_angle = angle_rad - math.radians(150)
        
        base_left_x = arrow_x + arrow_tip_size * math.cos(left_angle)
        base_left_y = arrow_y - arrow_tip_size * math.sin(left_angle)
        
        base_right_x = arrow_x + arrow_tip_size * math.cos(right_angle)
        base_right_y = arrow_y - arrow_tip_size * math.sin(right_angle)
        
        # Triangolo freccia
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
        
        # Emoji robot al centro
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
        
        # === INDICATORI DI STATO SOPRA IL ROBOT ===
        # Offset verticale per posizionare le icone sopra il robot
        status_y_offset = 35
        
        # Icona di pulizia attiva (🧹)
        fig.add_trace(go.Scatter(
            x=[x_px - 25],
            y=[y_px - status_y_offset],
            mode='text',
            text=['🧹'],
            textfont=dict(size=18),
            showlegend=False,
            hovertemplate='<b>Cleaning Mode</b><extra></extra>'
        ))
        
        # Icona batteria (🔋)
        # Simula livello batteria in base al progresso (solo per visualizzazione)
        battery_icon = '🔋'  # Piena
        if trail_data is not None:
            progress = len(trail_data) / len(all_movement_data) if all_movement_data is not None else 0
            if progress > 0.7:
                battery_icon = '🪫'  # Scarica
            elif progress > 0.4:
                battery_icon = '🔋'  # Media
        
        fig.add_trace(go.Scatter(
            x=[x_px],
            y=[y_px - status_y_offset],
            mode='text',
            text=[battery_icon],
            textfont=dict(size=18),
            showlegend=False,
            hovertemplate='<b>Battery Status</b><extra></extra>'
        ))
        
        # Icona stato operativo (cambia in base alla posizione nel percorso)
        # Se siamo a metà percorso, mostra pausa, altrimenti cleaning
        status_icon = '🧹'
        if trail_data is not None and all_movement_data is not None:
            progress = len(trail_data) / len(all_movement_data)
            # Simula una pausa a metà percorso (solo estetico)
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
        plot_bgcolor='rgba(250, 250, 245, 1)',
        margin=dict(l=0, r=0, t=0, b=0),
        hovermode='closest'
    )
    
    return fig


def robot_cleaning_monitoring():
    """Funzione principale per il monitoring dei robot di pulizia."""
    st.title("🤖 Robot Cleaning Monitoring")
    st.markdown("---")
    
    # Inizializza session state
    if 'steps' not in st.session_state:
        st.session_state.steps = None
    if 'idx' not in st.session_state:
        st.session_state.idx = 0
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'area_info' not in st.session_state:
        st.session_state.area_info = None
    
    # Sidebar controls
    st.sidebar.header("⚙️ Controls")
    
    # Area selection
    area_name = st.sidebar.selectbox(
        "Select Cleaning Area",
        ["biliardo"],
        index=0
    )
    
    # Carica dati
    if st.sidebar.button("🔄 Load Data", type="primary"):
        with st.spinner("Loading area and movement data..."):
            # Carica info area
            area_info = load_cleaning_area(area_name)
            if area_info:
                st.session_state.area_info = area_info
                st.sidebar.success(f"✅ Area '{area_name}' loaded!")
                
                # Carica movimenti robot - prova prima con la mappa specifica, poi con MainHall come fallback
                map_name = area_info.get('map_name', 'MainHall')
                df = load_movement_data(map_name=map_name)
                
                # Se non ci sono dati per questa mappa, prova con MainHall
                if df.empty and map_name != 'MainHall':
                    st.sidebar.info(f"No data for map '{map_name}', trying MainHall...")
                    df = load_movement_data(map_name='MainHall')
                
                if not df.empty:
                    st.session_state.steps = df
                    st.session_state.data_loaded = True
                    st.session_state.idx = 0
                    
                    st.sidebar.success(f"✅ Loaded {len(df)} movement points!")
                else:
                    st.sidebar.warning("⚠️ No movement data found for this area")
            else:
                st.sidebar.error(f"❌ Area '{area_name}' not found in database!")
    
    if not st.session_state.data_loaded or st.session_state.steps is None or st.session_state.area_info is None:
        st.info("👆 Click 'Load Data' in the sidebar to start")
        
        # Show preview of available areas
        st.markdown("""
        ### 🏢 About Robot Cleaning Monitoring
        
        This dashboard visualizes robot cleaning movements in real-time from the database.
        
        **Features:**
        - 🗺️ **Interactive floor plan** with realistic billiard room layout
        - 🎱 **Furniture and objects** (pool tables, bar, chairs)
        - ▶️ **Play/Pause animation** with speed control
        - 🔄 **Timeline navigation** and trail visualization
        - 📊 **Real-time position tracking** with coordinates
        - 📐 **Automatic scaling** based on actual area size
        
        **Select an area and click 'Load Data' to begin!**
        """)
        
        # Try to show available areas
        try:
            with psycopg.connect(PG_DSN) as conn:
                areas_df = pd.read_sql_query(
                    "SELECT area_name, area_size, map_name, clean_count FROM cleaning_area LIMIT 10",
                    conn
                )
                if not areas_df.empty:
                    st.markdown("### 📋 Available Cleaning Areas")
                    st.dataframe(areas_df, use_container_width=True)
        except:
            pass
        
        return
    
    # === AREA INFO DISPLAY ===
    area_info = st.session_state.area_info
    
    # Header con stile
    st.markdown("""
    <style>
    .area-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
    }
    .metric-label {
        font-size: 12px;
        color: #7f8c8d;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Area header
    st.markdown(f"""
    <div class="area-header">
        <h1 class="area-title">🎱 {area_info['area_name'].title()} Room</h1>
        <p class="area-subtitle">Real-time cleaning robot monitoring • Map: {area_info['map_name']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Dati caricati - mostra controlli
    st.sidebar.markdown("---")
    
    # Show trail toggle
    show_trail = st.sidebar.checkbox("Show Trail", value=True)
    
    # Progress info
    total_steps = len(st.session_state.steps)
    st.sidebar.markdown("---")
    st.sidebar.metric("Total Steps", total_steps)
    st.sidebar.metric("Current Step", st.session_state.idx + 1)
    
    # Progress bar
    progress_percent = (st.session_state.idx + 1) / total_steps
    st.sidebar.progress(progress_percent, text=f"Progress: {progress_percent*100:.1f}%")
    
    # Timeline slider
    st.sidebar.markdown("---")
    new_idx = st.sidebar.slider(
        "Timeline",
        min_value=0,
        max_value=total_steps - 1,
        value=st.session_state.idx,
        key="timeline_slider"
    )
    
    if new_idx != st.session_state.idx:
        st.session_state.idx = new_idx
    
    # Main content
    df = st.session_state.steps
    current_idx = st.session_state.idx
    
    # Get current step data
    current_step = df.iloc[current_idx]
    
    # Map visualization - SUBITO DOPO IL BANNER
    # Get trail data if enabled
    trail_data = None
    if show_trail and current_idx > 0:
        trail_data = df.iloc[:current_idx + 1]
    
    # Create and display map with area (passa TUTTI i dati per calcolare bounds corretti)
    config = MAP_CONFIG["MainHall"].copy()
    config['image_width'] = 800  # Dimensione originale
    config['image_height'] = 450  # Dimensione originale
    fig = create_map_with_area(
        current_step, 
        area_info, 
        config, 
        show_trail, 
        trail_data,
        all_movement_data=df  # Passa tutti i dati per calcolare bounds
    )
    st.plotly_chart(fig, use_container_width=True, key=f"map_{current_idx}")  # Key unica per forzare re-render
    
    # Legend - più compatta
    st.caption("**Legend:** 🎱 Pool Tables | ☕ Bar | ⚫ Chairs | 🤖 Robot | 🔵 Trail")
    
    # Metrics banner sotto la mappa
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
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
                <div style="font-size: 24px; margin-bottom: 5px;">🧹</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Clean Count</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{area_info['clean_count']}</div>
            </div>
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); border-radius: 8px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🗺️</div>
                <div style="color: white; font-size: 12px; text-transform: uppercase; margin-bottom: 8px;">Map Type</div>
                <div style="color: white; font-size: 24px; font-weight: bold;">{area_info.get('area_type', 'Standard')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Current position banner
    timestamp = current_step['inserted_at']
    if isinstance(timestamp, pd.Timestamp):
        timestamp = timestamp.strftime("%H:%M:%S")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
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
    <div style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
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
    
    # Debug info (opzionale, rimuovi in produzione)
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
            }
        })


# Run the monitoring function
def render():
    """Entry point for the page when called from main app."""
    robot_cleaning_monitoring()


if __name__ == "__main__":
    robot_cleaning_monitoring()