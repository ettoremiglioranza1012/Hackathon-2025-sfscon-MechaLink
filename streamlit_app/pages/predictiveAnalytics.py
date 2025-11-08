import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import psycopg

# Database connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mydb")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
PG_DSN = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"


def load_error_data():
    """Load robot error data from database."""
    try:
        with psycopg.connect(PG_DSN) as conn:
            query = """
                SELECT id, sn, shop_id, upload_time as created_at, 
                       task_time as occurred_at, soft_version as version, 
                       hard_version as app_version, error_level as type, 
                       error_type as error_code, error_source_id as trace_id, 
                       mac, product_code as robot_name
                FROM robot_error_log
                ORDER BY task_time DESC
            """
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'])
                df['occurred_at'] = pd.to_datetime(df['occurred_at'])
            
            return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def calculate_error_metrics(df):
    """Calculate key error metrics for prediction."""
    if df.empty:
        return {}
    
    metrics = {
        'error_frequency': df.groupby('error_code').size().to_dict(),
        'error_by_robot': df.groupby('robot_name').size().to_dict(),
        'error_timeline': df.groupby(df['occurred_at'].dt.date).size().to_dict(),
        'critical_robots': df[df['type'] == 'Error'].groupby('robot_name').size().sort_values(ascending=False).head(5).to_dict(),
        'time_between_errors': {}
    }
    
    # Calculate time between errors per robot
    for robot in df['robot_name'].unique():
        robot_errors = df[df['robot_name'] == robot].sort_values('occurred_at')
        if len(robot_errors) > 1:
            time_diffs = robot_errors['occurred_at'].diff().dt.total_seconds() / 3600  # hours
            metrics['time_between_errors'][robot] = time_diffs.mean()
    
    return metrics


def predict_next_failure(df, robot_name):
    """Simple prediction of next potential failure."""
    robot_errors = df[df['robot_name'] == robot_name].sort_values('occurred_at')
    
    if len(robot_errors) < 2:
        return None
    
    # Calculate average time between errors
    time_diffs = robot_errors['occurred_at'].diff().dropna()
    avg_time = time_diffs.mean()
    
    last_error = robot_errors.iloc[-1]['occurred_at']
    predicted_next = last_error + avg_time
    
    # Get most common error for this robot
    most_common_error = robot_errors['error_code'].mode()[0] if len(robot_errors['error_code'].mode()) > 0 else 'Unknown'
    
    return {
        'robot': robot_name,
        'last_error': last_error,
        'predicted_next_failure': predicted_next,
        'confidence': min(len(robot_errors) * 10, 95),  # Simple confidence score
        'likely_error': most_common_error,
        'error_pattern': robot_errors['error_code'].value_counts().to_dict()
    }


def generate_health_score(df, robot_name):
    """Generate a health score for a robot (0-100)."""
    robot_errors = df[df['robot_name'] == robot_name]
    
    if len(robot_errors) == 0:
        return 100
    
    # Factors affecting health score
    now = datetime.now()
    if robot_errors['occurred_at'].dtype == 'datetime64[ns, UTC]':
        now = pd.Timestamp.now(tz='UTC')
    
    recent_errors = len(robot_errors[robot_errors['occurred_at'] > now - timedelta(days=7)])
    total_errors = len(robot_errors)
    critical_errors = len(robot_errors[robot_errors['type'] == 'Error'])
    
    # Simple scoring formula
    health_score = 100
    health_score -= (recent_errors * 10)
    health_score -= (critical_errors * 5)
    health_score = max(0, min(100, health_score))
    
    return health_score


def predictive_analytics():
    """Main function for predictive analytics page."""
    st.set_page_config(page_title="Predictive Analytics", page_icon="🔮", layout="wide")
    
    st.title("Predictive Error Analytics")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading error data from database..."):
        df = load_error_data()
    
    if df.empty:
        st.warning("⚠️ No error data found in database. Please check your database connection and table structure.")
        st.info("""
        **Expected table structure:**
        - Table name: `robot_error_log`
        - Required columns: id, sn, shop_id, upload_time, task_time, soft_version, hard_version, error_level, error_type, error_source_id, mac, product_code
        """)
        return
    
    # Metrics overview - Cool Banner
    total_errors = len(df)
    critical_errors = len(df[df['type'] == 'Error'])
    unique_robots = df['robot_name'].nunique()
    avg_errors = total_errors / max(unique_robots, 1)
    high_risk_robots = df[df['type'] == 'Error'].groupby('robot_name').size()
    high_risk = len(high_risk_robots[high_risk_robots > 2])
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 30px;
                border-radius: 15px;
                margin: 20px 0;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <h2 style="color: white; text-align: center; margin-bottom: 30px; font-size: 32px;">
            📊 Fleet Health Overview
        </h2>
        <div style="display: grid; 
                    grid-template-columns: repeat(4, 1fr); 
                    gap: 20px;">
            <div style="text-align: center; 
                        padding: 25px; 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">⚠️</div>
                <div style="color: rgba(255,255,255,0.9); 
                            font-size: 14px; 
                            text-transform: uppercase; 
                            letter-spacing: 1px;
                            margin-bottom: 12px;">Total Errors</div>
                <div style="color: white; font-size: 42px; font-weight: bold; margin-bottom: 8px;">{total_errors}</div>
                <div style="color: #ff6b6b; 
                            font-size: 16px; 
                            background: rgba(255,107,107,0.2);
                            padding: 5px 10px;
                            border-radius: 20px;
                            display: inline-block;">
                    {critical_errors} Critical
                </div>
            </div>
            <div style="text-align: center; 
                        padding: 25px; 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">🤖</div>
                <div style="color: rgba(255,255,255,0.9); 
                            font-size: 14px; 
                            text-transform: uppercase; 
                            letter-spacing: 1px;
                            margin-bottom: 12px;">Robots Monitored</div>
                <div style="color: white; font-size: 42px; font-weight: bold;">{unique_robots}</div>
            </div>
            <div style="text-align: center; 
                        padding: 25px; 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">📈</div>
                <div style="color: rgba(255,255,255,0.9); 
                            font-size: 14px; 
                            text-transform: uppercase; 
                            letter-spacing: 1px;
                            margin-bottom: 12px;">Avg Errors/Robot</div>
                <div style="color: white; font-size: 42px; font-weight: bold;">{avg_errors:.1f}</div>
            </div>
            <div style="text-align: center; 
                        padding: 25px; 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">{'🔴' if high_risk > 0 else '🟢'}</div>
                <div style="color: rgba(255,255,255,0.9); 
                            font-size: 14px; 
                            text-transform: uppercase; 
                            letter-spacing: 1px;
                            margin-bottom: 12px;">High Risk Robots</div>
                <div style="color: white; font-size: 42px; font-weight: bold; margin-bottom: 8px;">{high_risk}</div>
                <div style="color: {'#ff6b6b' if high_risk > 0 else '#51cf66'}; 
                            font-size: 16px;">
                    {'⚠️ Attention' if high_risk > 0 else '✅ All Good'}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Predictive Dashboard
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 20px;
                border-radius: 15px;
                margin: 30px 0 20px 0;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);">
        <h2 style="color: white; text-align: center; margin: 0; font-size: 28px;">
            🎯 Failure Prediction Dashboard
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Robot Health Scores
        st.markdown("### 💚 Robot Health Scores")
        health_data = []
        for robot in df['robot_name'].unique():
            score = generate_health_score(df, robot)
            prediction = predict_next_failure(df, robot)
            health_data.append({
                'Robot': robot,
                'Health Score': score,
                'Status': '🟢 Healthy' if score > 70 else '🟡 Warning' if score > 40 else '🔴 Critical'
            })
        
        health_df = pd.DataFrame(health_data).sort_values('Health Score', ascending=True)
        
        # Color-coded display
        st.dataframe(
            health_df.style.background_gradient(subset=['Health Score'], cmap='RdYlGn', vmin=0, vmax=100),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        # Failure Predictions
        st.markdown("### Next Predicted Failures")
        predictions = []
        for robot in df['robot_name'].unique():
            pred = predict_next_failure(df, robot)
            if pred:
                # Check if prediction is in the future
                now = datetime.now()
                if pred['predicted_next_failure'].tzinfo is not None:
                    now = pd.Timestamp.now(tz='UTC')
                
                time_until = pred['predicted_next_failure'] - now
                hours_until = time_until.total_seconds() / 3600
                
                predictions.append({
                    'Robot': pred['robot'],
                    'Next Failure': pred['predicted_next_failure'].strftime('%Y-%m-%d %H:%M'),
                    'In Hours': f"{hours_until:.1f}h",
                    'Confidence': f"{pred['confidence']}%",
                    'Likely Error': pred['likely_error']
                })
        
        if predictions:
            pred_df = pd.DataFrame(predictions).sort_values('In Hours')
            st.dataframe(pred_df, use_container_width=True, hide_index=True)
        else:
            st.info("Not enough data for predictions. Need at least 2 errors per robot.")
    
    st.markdown("---")
    
    # Maintenance Recommendations
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 15px;
                margin: 30px 0 20px 0;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);">
        <h2 style="color: white; text-align: center; margin: 0; font-size: 28px;">
            🛠️ Automated Maintenance Recommendations
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    recommendations = []
    for robot in df['robot_name'].unique():
        health = generate_health_score(df, robot)
        robot_errors = df[df['robot_name'] == robot]
        
        if health < 50:
            priority = '🔴 High'
            action = 'Immediate inspection required'
            downtime = '2-4 hours'
            cost = 'High'
        elif health < 70:
            priority = '🟡 Medium'
            action = 'Schedule maintenance check'
            downtime = '1-2 hours'
            cost = 'Medium'
        else:
            priority = '🟢 Low'
            action = 'Routine inspection'
            downtime = '30 minutes'
            cost = 'Low'
        
        recommendations.append({
            'Robot': robot,
            'Health': f"{health}%",
            'Priority': priority,
            'Recommended Action': action,
            'Estimated Downtime': downtime,
            'Cost Impact': cost
        })
    
    rec_df = pd.DataFrame(recommendations).sort_values('Health')
    st.dataframe(rec_df, use_container_width=True, hide_index=True)


def render():
    """Entry point for the page when called from main app."""
    predictive_analytics()


if __name__ == "__main__":
    predictive_analytics()
