# test_data.py
import pandas as pd

# Charger les 5 premières lignes
df = pd.read_csv('data/um6p/learning_center/nginx-events.csv', nrows=5)
print("📊 Colonnes disponibles :")
print(df.columns.tolist())
print("\n📊 Aperçu :")
print(df.head())