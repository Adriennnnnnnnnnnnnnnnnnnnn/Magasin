import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuration de la page
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

# --- INITIALISATION DES VARIABLES DE SESSION ---
if 'exclusions' not in st.session_state:
    st.session_state.exclusions = {} 

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .metric-card { background-color: #262730; border-radius: 10px; padding: 20px 15px; text-align: center; border-left: 5px solid #00a8e8; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
    .metric-card-red { border-left-color: #ff4b4b; }
    .metric-card-gold { border-left-color: #f1c40f; }
    .metric-value { font-size: 32px; font-weight: 800; color: white; line-height: 1.2; }
    .metric-label { font-size: 13px; color: #cccccc; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-subtext { font-size: 13px; color: #ff8a8a; margin-top: 5px; font-weight: bold; }
    .metric-subtext-green { font-size: 13px; color: #2ecc71; margin-top: 5px; font-weight: bold; }
    
    table.meuble-grid { width: 100%; border-collapse: separate; border-spacing: 2px; text-align: center; color: #333; font-size: 12px; margin-top: 10px; }
    table.meuble-grid th { background-color: #f0f2f6; color: #31333F; padding: 12px; border-radius: 4px; border: none; }
    table.meuble-grid td { padding: 12px; width: 14%; vertical-align: middle; font-weight: bold; border-radius: 4px; border: 1px solid #f0f2f6; }
    .cell-vide { background-color: #ffffff; color: #aaa; border: 1px dashed #eee; }
    .cell-actif { background-color: #00a8e8; color: white; box-shadow: inset 0 0 5px rgba(0,0,0,0.1); }
    .cell-dormant { background-color: #ff4b4b; color: white; box-shadow: inset 0 0 5px rgba(0,0,0,0.2); }
    .cell-niveau { background-color: #e0e4e8; color: #31333F; font-weight: bold; }

    button[kind="primary"] { background-color: #ff4b4b !important; border: none !important; border-radius: 8px !important; color: white !important; padding: 0 !important; box-shadow: 0 3px 5px rgba(255, 75, 75, 0.3) !important; transition: all 0.2s ease !important; }
    button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 5px 8px rgba(255, 75, 75, 0.5) !important; }
    button[kind="secondary"] { background-color: #00a8e8 !important; border: none !important; border-radius: 8px !important; color: white !important; padding: 0 !important; box-shadow: 0 3px 5px rgba(0, 168, 232, 0.3) !important; transition: all 0.2s ease !important; }
    button[kind="secondary"]:hover { transform: translateY(-2px); box-shadow: 0 5px 8px rgba(0, 168, 232, 0.5) !important; }
    button:disabled { background-color: #ffffff !important; color: #aaa !important; border: 1px dashed #ccc !important; box-shadow: none !important; }
</style>
""", unsafe_allow_html=True)

# --- FONCTION DE TRAITEMENT ---
def parse_file(file):
    """Lecture souple CSV ou Excel"""
    if file.name.endswith('.csv'):
        content = file.getvalue().decode('utf-8', errors='ignore')
        delimiter = ';' if ';' in content.split('\n')[0] else ','
        file.seek(0)
        return pd.read_csv(file, sep=delimiter, encoding='utf-8', on_bad_lines='skip')
    else:
        return pd.read_excel(file, engine='openpyxl')

@st.cache_data
def load_and_clean_data(file_source):
    if isinstance(file_source, str):
        if file_source.endswith('.csv'):
            df = pd.read_csv(file_source, sep=None, engine='python')
        else:
            df = pd.read_excel(file_source, engine="openpyxl")
    else:
        df = parse_file(file_source)
    
    nom_colonne_prix = "Unit Price €" 
    nom_colonne_qte = "Current Stock Qty"
    nom_colonne_jours = "Last consumption"
    
    if nom_colonne_prix not in df.columns or nom_colonne_qte not in df.columns or nom_colonne_jours not in df.columns:
        st.error("🚨 **Erreur de lecture des colonnes**")
        st.info(f"👉 **Colonnes détectées dans le fichier :** {', '.join(df.columns)}")
        st.stop()
        
    df[nom_colonne_jours] = pd.to_numeric(df[nom_colonne_jours], errors='coerce')
    df = df.dropna(subset=[nom_colonne_jours])
    df = df.drop_duplicates()
    
    # Plus de filtre strict ! On extrait juste intelligemment pour le plan 2D.
    # Pattern cible: Lettre + 2 Chiffres + Lettre + Chiffres (ex: A01A010)
    pattern = r'^([A-Za-z])(\d{2})([A-Za-z])(\d{2,3})$'
    extracted = df['LOCATOR'].astype(str).str.extract(pattern)
    df['Rangée'] = extracted[0].str.upper()
    df['Meuble'] = extracted[1]
    df['Colonne'] = extracted[2].str.upper()
    df['Niveau'] = extracted[3]
        
    df['Prix Unitaire'] = pd.to_numeric(df[nom_colonne_prix].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), errors='coerce').fillna(0)
    df['Quantité'] = pd.to_numeric(df[nom_colonne_qte], errors='coerce').fillna(0)
    df['Valeur Totale'] = df['Quantité'] * df['Prix Unitaire']
    
    return df

# ==========================================
# PANNEAU LATÉRAL (GESTION DU FICHIER)
# ==========================================
st.sidebar.header("📂 Gestion des données")

uploaded_file = st.sidebar.file_uploader("Importer le fichier DATA STOCK :", type=["xlsx", "csv"])

# Gestion du fichier par défaut
file_path_default = "DATA STOCK.xlsx"
fallback_path = "DATA STOCK.xlsx - Sheet1.csv" # Pour le cloud s'il est au format CSV

if uploaded_file is not None:
    file_to_load = uploaded_file
    mod_time = "À l'instant (Fichier importé)"
    file_data_to_download = uploaded_file.getvalue()
    download_name = uploaded_file.name
else:
    # Recherche du fichier par défaut
    if os.path.exists(file_path_default):
        file_to_load = file_path_default
    elif os.path.exists(fallback_path):
        file_to_load = fallback_path
    else:
        file_to_load = None

    if file_to_load:
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_to_load)).strftime('%d/%m/%Y à %H:%M')
        with open(file_to_load, "rb") as f:
            file_data_to_download = f.read()
        download_name = "DATA_STOCK_Extract.xlsx"
    else:
        st.title("📦 Tableau de Bord : Pilotage Magasin")
        st.info("👋 Bienvenue ! Aucun fichier trouvé.\n\nVeuillez importer votre fichier de stock (Excel ou CSV) depuis le menu de gauche.")
        st.stop()

st.sidebar.info(f"📅 **Date des données actives :**\n\n{mod_time}")

if 'file_data_to_download' in locals() and file_data_to_download:
    st.sidebar.download_button(
        label="📥 Télécharger la base actuelle",
        data=file_data_to_download,
        file_name=download_name,
        use_container_width=True
    )

st.sidebar.divider()
st.sidebar.header("⚙️ Paramètres d'analyse")
seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)

# Chargement
df = load_and_clean_data(file_to_load)

# Détermination dynamique de la taille du magasin pour la grille
list_rangees = sorted(df['Rangée'].dropna().unique())
if df['Meuble'].dropna().empty:
    max_rack = 25
else:
    max_rack = max(25, int(df['Meuble'].dropna().astype(int).max()))
list_meubles_all = [f"{i:02d}" for i in range(1, max_rack + 1)]

CAPACITE_MAX_MAGASIN = len(list_rangees) * len(list_meubles_all) * 6 * 6

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = list_rangees[0] if list_rangees else 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'

# ==========================================
# EN-TÊTE ET KPIs
# ==========================================
st.title("📦 Tableau de Bord : Pilotage Magasin")

total_refs = df['PART'].nunique()
total_locs = df['LOCATOR'].nunique()

# Calcul de l'occupation uniquement sur les emplacements valides du magasin (qui ont une Rangée)
total_locs_magasin = df.dropna(subset=['Rangée'])['LOCATOR'].nunique()
taux_occupation = (total_locs_magasin / CAPACITE_MAX_MAGASIN * 100) if CAPACITE_MAX_MAGASIN > 0 else 0
