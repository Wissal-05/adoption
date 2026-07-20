from analytics import load_learning_center_data

users, logs = load_learning_center_data()

if users is not None:
    print("\n" + "="*40)
    print("📊 RÉSULTATS")
    print("="*40)
    print(f"👥 Utilisateurs uniques : {len(users)}")
    print(f"📝 Logs : {len(logs)}")
    print(f"📅 Période : {logs['date'].min()} → {logs['date'].max()}")
    print(f"🏷️ Services : {logs['service'].unique().tolist()}")