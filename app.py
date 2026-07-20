import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ===== IMPORTS DES FONCTIONS =====
from analytics import load_entrophy_data, load_learning_center_data

# Configuration de la page
st.set_page_config(page_title="Adoption Dashboard - UM6P", layout="wide")

# ===== SIDEBAR - NAVIGATION =====
st.sidebar.title("📊 Adoption Dashboard")

# Sélecteur de source de données
data_source = st.sidebar.radio(
    "📂 Source de données",
    ["Learning Center", "ENTROPHY", "Toutes les sources"],
    index=0
)

# ===== CHARGEMENT DES DONNÉES =====
@st.cache_data
def load_data(source):
    if source == "Learning Center":
        users, logs = load_learning_center_data()
        if users is None:
            st.error("❌ Données Learning Center non trouvées")
            st.stop()
        st.sidebar.success(f"✅ Learning Center : {len(users)} utilisateurs, {len(logs)} logs")
        return users, logs
    
    elif source == "ENTROPHY":
        users, logs = load_entrophy_data()
        if users is None:
            st.error("❌ Données ENTROPHY non trouvées")
            st.stop()
        st.sidebar.success(f"✅ ENTROPHY : {len(users)} utilisateurs, {len(logs)} logs")
        return users, logs
    
    else:  # Toutes les sources
        users1, logs1 = load_learning_center_data()
        users2, logs2 = load_entrophy_data()
        
        if users1 is None or users2 is None:
            st.error("❌ Une des sources est introuvable")
            st.stop()
        
        logs = pd.concat([logs1, logs2], ignore_index=True)
        users = logs[['user_id']].drop_duplicates().reset_index(drop=True)
        users['department'] = 'Unknown'
        
        st.sidebar.success(f"✅ Fusion : {len(users)} utilisateurs, {len(logs)} logs")
        return users, logs

# Charger les données
users, logs = load_data(data_source)

# ===== NAVIGATION =====
page = st.sidebar.selectbox(
    "📄 Navigation",
    ["Vue globale", "Évolution", "Classements", "Assistant IA"]
)

# ===== FONCTIONS D'ANALYSE =====
def calculate_mau(service=None, year=None, month=None):
    """Calcule le MAU pour un service et une période donnés"""
    if year is None or month is None:
        latest_date = logs['date'].max()
        year = latest_date.year
        month = latest_date.month
    
    mask = (logs['date'].dt.year == year) & (logs['date'].dt.month == month)
    if service:
        mask &= (logs['service'] == service)
    return logs[mask]['user_id'].nunique()

def get_latest_period():
    """Retourne la dernière période disponible"""
    latest_date = logs['date'].max()
    return latest_date.year, latest_date.month

# Variables globales
services = logs['service'].unique()
total_users = len(users)
current_year, current_month = get_latest_period()

# ===================== PAGE 1 : VUE GLOBALE =====================
if page == "Vue globale":
    st.title("📈 Vue globale de l'adoption")
    st.caption(f"📅 Période : {logs['date'].min().date()} → {logs['date'].max().date()}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI
    mau_total = calculate_mau()
    mau_lc = calculate_mau('learning-center')
    
    col1.metric("👥 Total utilisateurs", f"{total_users:,}")
    col2.metric("📊 MAU Total", f"{mau_total:,}")
    col3.metric("📚 MAU Learning Center", f"{mau_lc:,}")
    col4.metric("🏷️ Services", f"{len(services)}")
    
    # Services sous-utilisés
    st.subheader("⚠️ Services sous-utilisés")
    underused = []
    for service in services:
        mau = calculate_mau(service)
        rate = (mau / total_users) * 100 if total_users > 0 else 0
        if rate < 30:
            underused.append(f"{service} : {rate:.1f}%")
    
    if underused:
        for item in underused:
            st.warning(item)
    else:
        st.success("✅ Tous les services ont un bon taux d'adoption")

# ===================== PAGE 2 : ÉVOLUTION =====================
elif page == "Évolution":
    st.title("📉 Évolution temporelle")
    
    # Agrégation par mois
    logs['month'] = logs['date'].dt.to_period('M')
    monthly = logs.groupby(['month', 'service'])['user_id'].nunique().reset_index()
    monthly['month'] = monthly['month'].astype(str)
    
    fig = px.line(
        monthly,
        x='month',
        y='user_id',
        color='service',
        title="Évolution du MAU par service",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

# ===================== PAGE 3 : CLASSEMENTS =====================
elif page == "Classements":
    st.title("🏆 Classements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top services (MAU)")
        services_mau = []
        for service in services:
            mau = calculate_mau(service)
            services_mau.append({'service': service, 'mau': mau})
        top_services = pd.DataFrame(services_mau).sort_values('mau', ascending=False)
        st.dataframe(top_services, use_container_width=True)
    
    with col2:
        st.subheader("Top pages visitées")
        if 'page' in logs.columns:
            top_pages = logs['page'].value_counts().head(10).reset_index()
            top_pages.columns = ['Page', 'Visites']
            st.dataframe(top_pages, use_container_width=True)
        else:
            st.info("Colonne 'page' non disponible")

# ===================== PAGE 4 : ASSISTANT IA =====================
elif page == "Assistant IA":
    st.title("💬 Assistant IA")
    
    from assistant import ask_question
    
    st.markdown("""
    **Questions que vous pouvez poser :**
    - Quel est le MAU du Learning Center ?
    - Combien d'utilisateurs uniques ?
    - Quelles sont les pages les plus visitées ?
    - Donne-moi un résumé de l'adoption
    """)
    
    # Historique du chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    user_question = st.chat_input("Posez votre question...")
    
    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)
        
        with st.chat_message("assistant"):
            with st.spinner("Réflexion en cours..."):
                response = ask_question(user_question)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})