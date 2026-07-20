import pandas as pd
import numpy as np

def load_data():
    """
    Charge les données ENTROPHY par défaut.
    (Les données simulées ont été supprimées)
    """
    return load_entrophy_data()

def load_entrophy_data():
    try:
        logs = pd.read_parquet('data/real/logs_entrophy.parquet')
        
        # ===== CONVERTIR LA DATE =====
        logs['date'] = pd.to_datetime(logs['date'])
        
        # ===== AFFICHER LA PÉRIODE POUR VÉRIFIER =====
        print(f"📅 Période des données : {logs['date'].min()} → {logs['date'].max()}")
        
        users = logs[['user_id', 'department']].drop_duplicates().reset_index(drop=True)
        print(f"✅ ENTROPHY : {len(logs)} logs, {len(users)} utilisateurs")
        return users, logs
    except FileNotFoundError:
        print("❌ Fichier ENTROPHY non trouvé !")
        return None, None

# Le reste des fonctions reste identique
def calculate_mau(logs, service=None, year=2026, month=6):
    mask = (logs['date'].dt.year == year) & (logs['date'].dt.month == month)
    if service:
        mask &= (logs['service'] == service)
    return logs[mask]['user_id'].nunique()

def calculate_adoption_rate(users, logs, service, year=2026, month=6):
    total = len(users)
    mau = calculate_mau(logs, service, year, month)
    return round((mau / total) * 100, 2)

def get_underused_services(logs, users, threshold=30, year=2026, month=6):
    results = []
    for service in logs['service'].unique():
        rate = calculate_adoption_rate(users, logs, service, year, month)
        if rate < threshold:
            results.append({'service': service, 'adoption_rate': rate})
    return pd.DataFrame(results).sort_values('adoption_rate')

def get_department_ranking(logs_with_dept, service='Teams', year=2026, month=6):
    mask = (logs_with_dept['date'].dt.year == year) & (logs_with_dept['date'].dt.month == month) & (logs_with_dept['service'] == service)
    return logs_with_dept[mask].groupby('department')['user_id'].nunique().sort_values(ascending=False)

def get_evolution(logs, service=None):
    logs['month'] = logs['date'].dt.to_period('M')
    monthly = logs.groupby(['month', 'service'])['user_id'].nunique().reset_index()
    monthly['month'] = monthly['month'].astype(str)
    return monthly

def load_learning_center_data():
    """Charge et nettoie les données du Learning Center (UM6P)"""
    try:
        df = pd.read_csv('data/um6p/learning_center/nginx-events.csv')
        print(f"📊 Learning Center : {len(df)} lignes brutes")
        
        # ===== 1. EXCLURE LES BOTS =====
        if 'is_bot' in df.columns:
            df = df[df['is_bot'] == False]
            print(f"   Après exclusion bots : {len(df)} lignes")
        
        # ===== 2. EXCLURE LES FICHIERS STATIQUES =====
        if 'is_static' in df.columns:
            df = df[df['is_static'] == False]
            print(f"   Après exclusion statiques : {len(df)} lignes")
        
        # ===== 3. GARDER SEULEMENT LES ÉVÉNEMENTS ANALYTICS =====
        if 'analytics_eligible' in df.columns:
            df = df[df['analytics_eligible'] == True]
            print(f"   Après filtrage analytics : {len(df)} lignes")
        
        # ===== 4. SUPPRIMER LES REQUÊTES INTERNES =====
        if 'is_internal_backend' in df.columns:
            df = df[df['is_internal_backend'] == False]
            print(f"   Après exclusion interne : {len(df)} lignes")
        
        # ===== 5. EXCLURE LES APPELS API (si besoin) =====
        if 'is_api' in df.columns:
            df = df[df['is_api'] == False]
            print(f"   Après exclusion API : {len(df)} lignes")
        
        # ===== 6. SUPPRIMER LES DOUBLONS =====
        df = df.drop_duplicates()
        print(f"   Après suppression doublons : {len(df)} lignes")
        
        # ===== 7. STANDARDISER =====
        df = df.rename(columns={
            'visitor_id_approx': 'user_id',
            'event_time_local': 'date',
            'path': 'page'
        })
        
        # Convertir la date
        df['date'] = pd.to_datetime(df['date'])
        
        # Ajouter les colonnes nécessaires
        df['service'] = 'learning-center'
        df['sessions'] = 1
        
        # Supprimer les user_id vides
        df = df.dropna(subset=['user_id'])
        df = df[df['user_id'] != '']
        
        # Créer la table users
        users = df[['user_id']].drop_duplicates().reset_index(drop=True)
        users['department'] = 'Unknown'
        
        # Afficher les statistiques finales
        print(f"\n✅ Learning Center : {len(df)} logs, {len(users)} utilisateurs")
        print(f"   Période : {df['date'].min()} → {df['date'].max()}")
        
        return users, df
        
    except FileNotFoundError:
        print("❌ Fichier data/um6p/learning_center/nginx-events.csv non trouvé")
        return None, None
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        return None, None