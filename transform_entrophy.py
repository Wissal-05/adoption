import json
import pandas as pd
import os
from datetime import datetime
import hashlib

def transform_entrophy_to_logs():
    """
    Transforme les fichiers ENTROPHY (finance, hr, legal) en logs d'utilisation
    Version améliorée avec les vrais champs
    """
    
    base_path = "data/real/archive (8)"
    files = ['finance.json', 'hr.json', 'legal.json']
    
    all_logs = []
    user_counter = {}
    
    for file in files:
        file_path = os.path.join(base_path, file)
        
        if not os.path.exists(file_path):
            print(f"❌ Fichier non trouvé : {file_path}")
            continue
        
        print(f"📂 Traitement de {file}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        department = file.replace('.json', '').capitalize()
        
        if isinstance(data, list):
            for item in data:
                # ===== USER_ID : Générer un ID unique à partir du process_instance_uuid =====
                process_uuid = item.get('process_instance_uuid', '')
                if process_uuid:
                    # Générer un ID utilisateur stable à partir du UUID
                    user_id = hashlib.md5(process_uuid.encode()).hexdigest()[:8]
                else:
                    user_id = f"user_{len(all_logs)}"
                
                # ===== DATE : Utiliser time_stamp =====
                date_str = item.get('time_stamp', '')
                if date_str:
                    try:
                        date = pd.to_datetime(date_str)
                    except:
                        date = datetime.now()
                else:
                    date = datetime.now()
                
                # ===== SERVICE : Utiliser application_name =====
                service = item.get('application_name', 'Unknown')
                if not service or service == '':
                    service = 'Unknown'
                
                # ===== SESSIONS =====
                sessions = 1
                
                # ===== INTERACTION TYPE =====
                interaction = item.get('interaction_type', 'Unknown')
                
                all_logs.append({
                    'user_id': user_id,
                    'department': department,
                    'service': service,
                    'date': date,
                    'sessions': sessions,
                    'interaction': interaction
                })
        
        print(f"  ✅ Traité : {len(data)} interactions")
    
    # Créer le DataFrame
    df = pd.DataFrame(all_logs)
    
    if len(df) == 0:
        print("❌ Aucune donnée transformée !")
        return None
    
    # Nettoyage
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['user_id', 'service'])
    
    # Agrégation par jour/utilisateur/service
    print("\n📊 Agrégation des données...")
    
    df_agg = df.groupby([
        df['user_id'],
        df['department'],
        df['service'],
        df['date'].dt.date
    ]).agg({
        'sessions': 'sum',
        'interaction': 'count'
    }).reset_index()
    
    df_agg.columns = ['user_id', 'department', 'service', 'date', 'sessions', 'interactions']
    
    # Sauvegarder
    os.makedirs('data/real', exist_ok=True)
    df_agg.to_parquet('data/real/logs_entrophy.parquet')
    
    print(f"\n{'='*50}")
    print("✅ TRANSFORMATION TERMINÉE !")
    print(f"{'='*50}")
    print(f"📊 Statistiques :")
    print(f"   - Total logs : {len(df)}")
    print(f"   - Après agrégation : {len(df_agg)}")
    print(f"   - Utilisateurs uniques : {df_agg['user_id'].nunique()}")
    print(f"   - Services uniques : {df_agg['service'].nunique()}")
    print(f"   - Services : {df_agg['service'].unique().tolist()[:10]}")
    print(f"   - Départements : {df_agg['department'].unique().tolist()}")
    print(f"   - Période : {df_agg['date'].min()} → {df_agg['date'].max()}")
    
    print(f"\n📊 Aperçu des données :")
    print(df_agg.head(10))
    
    return df_agg

if __name__ == "__main__":
    transform_entrophy_to_logs()