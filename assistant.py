import os
import json
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from analytics import load_learning_center_data

load_dotenv()

# ===== IMPORTER LES FONCTIONS D'ANALYSE =====
from analytics import load_learning_center_data, calculate_mau

# ===== CHARGER LES DONNÉES LEARNING CENTER =====
users, logs = load_learning_center_data()

if users is None or logs is None:
    print("❌ Erreur : Données Learning Center non chargées")
    users = pd.DataFrame()
    logs = pd.DataFrame()

print(f"✅ Assistant chargé avec {len(users)} utilisateurs et {len(logs)} logs")

# ===== FONCTION POUR OBTENIR LA DERNIÈRE DATE =====
def get_latest_date():
    """Retourne le dernier mois/année disponible dans les données"""
    if len(logs) == 0:
        return 7, 2026
    available_months = logs['date'].dt.to_period('M').unique()
    if len(available_months) > 0:
        latest = available_months[-1]
        return latest.month, latest.year
    return 7, 2026

# ===== FONCTIONS D'ANALYSE =====
def get_mau(service: str = "learning-center", month: int = None, year: int = None) -> str:
    """Retourne le MAU pour un service donné"""
    if len(logs) == 0:
        return "Aucune donnée disponible"
    
    if month is None or year is None:
        month, year = get_latest_date()
    
    mau = calculate_mau(logs, service, year, month)
    total_users = len(users)
    rate = (mau / total_users) * 100 if total_users > 0 else 0
    
    return f"Le MAU du {service} est de {mau} utilisateurs actifs sur {month}/{year} (Taux: {rate:.1f}%)"

def get_total_users() -> str:
    """Retourne le nombre total d'utilisateurs uniques"""
    return f"Nombre total d'utilisateurs uniques : {len(users)}"

def get_top_pages(limit: int = 10) -> str:
    """Retourne les pages les plus visitées"""
    if len(logs) == 0 or 'page' not in logs.columns:
        return "Aucune donnée de pages disponible"
    
    top_pages = logs['page'].value_counts().head(limit)
    result = f"🏆 Top {limit} pages les plus visitées :\n"
    for i, (page, count) in enumerate(top_pages.items(), 1):
        result += f"  {i}. {page} : {count} visites\n"
    return result

def get_summary(month: int = None, year: int = None) -> str:
    """Retourne un résumé complet de l'adoption"""
    if len(logs) == 0:
        return "Aucune donnée disponible"
    
    # ===== GESTION DES PARAMÈTRES =====
    # Si month ou year sont None ou ne sont pas des nombres, utiliser la dernière date
    try:
        if month is None or year is None or not isinstance(month, int) or not isinstance(year, int):
            month, year = get_latest_date()
    except:
        month, year = get_latest_date()
    
    # Fallback si encore None
    if month is None:
        month = 7
    if year is None:
        year = 2026
    
    services = logs['service'].unique()
    total_users = len(users)
    
    lines = [f"📊 RÉSUMÉ ADOPTION - {month}/{year}", "=" * 40]
    
    for service in services:
        mau = calculate_mau(logs, service, year, month)
        rate = (mau / total_users) * 100 if total_users > 0 else 0
        lines.append(f"• {service}: {mau} utilisateurs ({rate:.1f}%)")
    
    # Ajouter les top pages
    if 'page' in logs.columns:
        lines.append("")
        lines.append("🏆 Top 5 pages :")
        top_pages = logs['page'].value_counts().head(5)
        for page, count in top_pages.items():
            lines.append(f"  - {page}: {count} visites")
    
    # Période
    lines.append("")
    lines.append(f"📅 Période : {logs['date'].min().date()} → {logs['date'].max().date()}")
    lines.append(f"👥 Total utilisateurs : {total_users}")
    
    return "\n".join(lines)

def get_activity_trend() -> str:
    """Retourne la tendance d'activité (logs par jour)"""
    if len(logs) == 0:
        return "Aucune donnée disponible"
    
    daily_activity = logs.groupby(logs['date'].dt.date).size()
    avg_daily = daily_activity.mean()
    max_day = daily_activity.max()
    min_day = daily_activity.min()
    
    return f"""📊 Tendance d'activité :
    - Moyenne par jour : {avg_daily:.0f} logs
    - Jour le plus actif : {max_day} logs
    - Jour le moins actif : {min_day} logs
    - Nombre de jours : {len(daily_activity)}"""
    
# ===== MAPPING DES FONCTIONS =====
function_map = {
    "get_mau": get_mau,
    "get_total_users": get_total_users,
    "get_top_pages": get_top_pages,
    "get_summary": get_summary,
    "get_activity_trend": get_activity_trend
}

# ===== DÉFINITION DES FONCTIONS POUR GROQ =====
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_mau",
            "description": "Retourne le nombre d'utilisateurs actifs mensuels (MAU) pour le service Learning Center.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "default": "learning-center",
                        "description": "Le nom du service"
                    },
                    "month": {"type": "integer", "default": None},
                    "year": {"type": "integer", "default": None}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_users",
            "description": "Retourne le nombre total d'utilisateurs uniques du service.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_pages",
            "description": "Retourne les pages les plus visitées du service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10}
                }
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "get_summary",
        "description": "Retourne un résumé complet de l'adoption du service.",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "integer",
                    "description": "Le mois (1-12). Si non spécifié, utilise le dernier mois disponible."
                },
                "year": {
                    "type": "integer",
                    "description": "L'année. Si non spécifiée, utilise la dernière année disponible."
                }
            },
            "additionalProperties": False
        }
    }
},
    {
        "type": "function",
        "function": {
            "name": "get_activity_trend",
            "description": "Retourne la tendance d'activité (logs par jour).",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

# ===== CRÉER L'ASSISTANT AVEC GROQ =====
def create_assistant():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None, "❌ Clé API Groq manquante. Ajoute GROQ_API_KEY dans .env"
    
    try:
        client = Groq(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"❌ Erreur: {str(e)}"

# ===== FONCTION PRINCIPALE =====
def ask_question(question: str) -> str:
    """Pose une question à l'assistant Groq"""
    
    client, error = create_assistant()
    if error:
        return error
    
    # Vérifier si les données sont disponibles
    if len(logs) == 0:
        return "❌ Les données du Learning Center ne sont pas disponibles. Vérifie le fichier CSV."
    
    try:
        # Appel à Groq avec function calling
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Tu es un assistant IT expert en analyse d'adoption des services numériques pour l'UM6P.
Tu réponds en français, de manière claire et professionnelle.
Les données concernent le Learning Center.
Services disponibles : learning-center.
Utilise les fonctions disponibles pour répondre aux questions avec des données précises."""
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0
        )
        
        message = response.choices[0].message
        
        # Vérifier si Groq veut appeler une fonction
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            
            # Exécuter la fonction
            if function_name in function_map:
                if arguments is None:
                    result = function_map[function_name]()
                else:
                    result = function_map[function_name](**arguments)
                
                # Demander à Groq de formater la réponse
                final_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": "Tu es un assistant IT. Formate la réponse de manière claire et professionnelle en français."
                        },
                        {
                            "role": "user",
                            "content": f"Question: {question}\n\nRésultat: {result}\n\nRéponds à l'utilisateur avec ce résultat."
                        }
                    ],
                    temperature=0
                )
                return final_response.choices[0].message.content
        
        # Si Groq répond directement
        return message.content
        
    except Exception as e:
        return f"❌ Erreur: {str(e)}"