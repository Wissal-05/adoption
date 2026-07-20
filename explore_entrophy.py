import json
import os

# Chemin des fichiers avec le bon nom de dossier
base_path = "data/real/archive (8)"  # ← Attention à l'espace !

files = ['finance.json', 'hr.json', 'legal.json']

for file in files:
    file_path = os.path.join(base_path, file)
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé : {file_path}")
        continue
    
    print(f"\n{'='*50}")
    print(f"📄 Fichier : {file}")
    print('='*50)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Type de données : {type(data)}")
    
    if isinstance(data, list):
        print(f"Nombre d'éléments : {len(data)}")
        if len(data) > 0:
            print(f"Premier élément :")
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
    elif isinstance(data, dict):
        print(f"Clés : {list(data.keys())}")
        for key in list(data.keys())[:3]:
            print(f"  {key} : {type(data[key])}")
            if isinstance(data[key], list) and len(data[key]) > 0:
                print(f"    Premier élément : {data[key][0] if not isinstance(data[key][0], dict) else list(data[key][0].keys())}")