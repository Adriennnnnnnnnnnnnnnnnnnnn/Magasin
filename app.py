import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuration de la page
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

CONFIG_FILE = "config_magasin.json"
SERVER_XLSX = "data_stock_serveur.xlsx"
SERVER_CSV = "data_stock_serveur.csv"
DEFAULT_XLSX = "DATA STOCK.xlsx"
DEFAULT_CSV = "DATA STOCK.xlsx - Sheet1.csv"

# --- RÈGLES DE VALIDATION ARCHITECTURALE ---
def is_meuble_valid_for_row(r, m_int):
    if r == 'M': return 7 <= m_int <= 21 and m_int != 13
    elif r in ['G', 'H', 'J', 'K', 'L']: return 1 <= m_int <= 21
    elif r == 'F': return 1 <= m_int <= 25
    elif r == 'E': return 1 <= m_int <= 24
    elif r in ['D', 'C', 'B']: return 1 <= m_int <= 25
    elif r == 'A': return 1 <= m_int <= 21
    return False

def get_meuble_structure(r, m_str):
    key = f"{r}{m_str}"
    if key in st.session_state.custom_structures:
        return st.session_state.custom_structures[key]["cols"], st.session_state.custom_structures[key]["nivs"]
        
    if r == 'M':
        colonnes = ['C', 'B', 'A']
        niveaux = ['020', '010', '000'] if m_str in ['07', '08'] else ['040', '030', '020', '010', '000']
    else:
        niveaux = ['050', '040', '030', '020', '010', '000']
        colonnes = ['F', 'E', 'D', 'C', 'B', 'A']
    return colonnes, niveaux

# --- GESTION DE LA CONFIGURATION (PERSISTANCE) ---
def generate_theoretical_locations():
    locs = []
    rangees = ['A','B','C','D','E','F','G','H','J','K','L','M']
    for r in rangees:
        for m in range(1, 26):
            if is_meuble_valid_for_row(r, m):
                m_str = f"{m:02d}"
                colonnes, niveaux = get_meuble_structure(r, m_str)
                for c in colonnes:
                    for n in niveaux:
                        locs.append(f"{r}{m_str}{c}{n}")
    return locs

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                excl = data.get("exclusions", {})
                locs = set(data.get("master_locations", []))
                custom = data.get("custom_structures", {})
                return excl, locs, custom
        except:
            pass
    return {}, set(), {}

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "exclusions": st.session_state.exclusions,
            "master_locations": list(st.session_state.master_locations),
            "custom_structures": st.session_state.custom_structures
        }, f, indent=4)

# --- FONCTIONS DE MANIPULATION DU JUMEAU NUMÉRIQUE ---
def toggle_loc(loc_id):
    if loc_id in st.session_state.master_locations: st.session_state.master_locations.remove(loc_id)
    else: st.session_state.master_locations.add(loc_id)
    save_config()

def toggle_col(r, m, col, niveaux):
    locs = [f"{r}{m}{col}{n}" for n in niveaux]
    all_exist = all(l in st.session_state.master_locations for l in locs)
    if all_exist:
        for l in locs: st.session_state.master_locations.discard(l)
    else:
        for l in locs: st.session_state.master_locations.add(l)
    save_config()

def toggle_niv(r, m, niv, colonnes):
    locs = [f"{r}{m}{c}{niv}" for c in colonnes]
    all_exist = all(l in st.session_state.master_locations for l in locs)
    if all_exist:
        for l in locs: st.session_state.master_locations.discard(l)
    else:
        for l in locs: st.session_state.master_locations.add(l)
    save_config()

def modify_structure(r, m, action, mod_type, val):
    key = f"{r}{m}"
    if key not in st.session_state.custom_structures:
        c, n = get_meuble_structure(r, m)
        st.session_state.custom_structures[key] = {"cols": c.copy(), "nivs": n.copy()}
        
    struct = st.session_state.custom_structures[key]
    
    if action == "add":
        if mod_type == "col" and val not in struct["cols"]:
            struct["cols"].append(val)
            struct["cols"].sort(reverse=True)
            for n in struct["nivs"]: st.session_state.master_locations.add(f"{r}{m}{val}{n}")
        elif mod_type == "niv" and val not in struct["nivs"]:
            struct["nivs"].append(val)
            struct["nivs"].sort(reverse=True)
            for c in struct["cols"]: st.session_state.master_locations.add(f"{r}{m}{c}{val}")
            
    elif action == "remove":
        if mod_type == "col" and val in struct["cols"]:
            struct["cols"].remove(val)
            for n in struct["nivs"]: st.session_state.master_locations.discard(f"{r}{m}{val}{n}")
        elif mod_type == "niv" and val in struct["nivs"]:
            struct["nivs"].remove(val)
            for c in struct["cols"]: st.session_state.master_locations.discard(f"{r}{m}{c}{val}")
            
    save_config()

# --- INITIALISATION DES VARIABLES DE SESSION ---
if 'config_loaded' not in st.session_state:
    excl, locs, custom = load_config()
    st.session_state.exclusions = excl
    st.session_state.master_locations = locs
    st.session_state.custom_structures = custom
    st.session_state.config_loaded = True

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
    
    table.meuble-grid { width: 100%; border-collapse: separate; border-spacing: 3px; text-align: center; color: #333; font-size: 12px; margin-top: 10px; }
    table.meuble-grid th { background-color: #f0f2f6; color: #31333F; padding: 12px; border-radius: 4px; border: none; }
    table.meuble-grid td { padding: 12px; vertical-align: middle; font-weight: bold; border-radius: 4px; border: 1px solid #e0e4e8; }
    .cell-vide { background-color: #ffffff; color: #555; border: 1px dashed #a5b1c2 !important; }
    .cell-inexistant { background-color: #d1d8e0; color: #7f8fa6; border: 1px solid #d1d8e0 !important; opacity: 0.6; }
    .cell-actif { background-color: #00a8e8; color: white; box-shadow: inset 0 0 5px rgba(0,0,0,0.1); }
    .cell-dormant { background-color: #ff4b4b; color: white; box-shadow: inset 0 0 5px rgba(0,0,0,0.2); }
    .cell-inconnu { background-color: #f39c12; color: white; box-shadow: inset 0 0 5px rgba(0,0,0,0.1); }
    .cell-niveau { background-color: #e0e4e8; color: #31333F; font-weight: bold; width: 80px; }

    button[kind="primary"] { background-color: #ff4b4b !important; border: none !important; border-radius: 8px !important; color: white !important; padding: 0 !important; box-shadow: 0 3px 5px rgba(255, 75, 75, 0.3) !important; transition: all 0.2s ease !important; }
    button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 5px 8px rgba(255, 75, 75, 0.5) !important; }
    button[kind="secondary"] { background-color: #00a8e8 !important; border: none !important; border-radius: 8px !important; color: white !important; padding: 0 !important; box-shadow: 0 3px 5px rgba(0, 168, 232, 0.3) !important; transition: all 0.2s ease !important; }
    button[kind="secondary"]:hover { transform: translateY(-2px); box-shadow: 0 5px 8px rgba(0, 168, 232, 0.5) !important; }
    button[kind="tertiary"] { background-color: #f39c12 !important; border: none !important; border-radius: 8px !important; color: white !important; padding: 0 !important; box-shadow: 0 3px 5px rgba(243, 156, 18, 0.3) !important; transition: all 0.2s ease !important; }
    button[kind="tertiary"]:hover { transform: translateY(-2px); box-shadow: 0 5px 8px rgba(243, 156, 18, 0.5) !important; }
    button:disabled { background-color: #ffffff !important; color: #aaa !important; border: 1px dashed #ccc !important; box-shadow: none !important; }
</style>
""", unsafe_allow_html=True)

# --- FONCTION DE LECTURE ---
def parse_file(file):
    if isinstance(file, str):
        if file.endswith('.csv'): return pd.read_csv(file, sep=';', encoding='utf-8', on_bad_lines='skip')
        return pd.read_excel(file, engine='openpyxl')
    if file.name.endswith('.csv'):
        content = file.getvalue().decode('utf-8', errors='ignore')
        delimiter = ';' if ';' in content.split('\n')[0] else ','
        file.seek(0)
        return pd.read_csv(file, sep=delimiter, encoding='utf-8', on_bad_lines='skip')
    return pd.read_excel(file, engine='openpyxl')

@st.cache_data
def load_base_data(file_source):
    df = parse_file(file_source)
    nom_colonne_prix, nom_colonne_qte, nom_colonne_jours = "Unit Price €", "Current Stock Qty", "Last consumption"
    
    if nom_colonne_prix not in df.columns or nom_colonne_qte not in df.columns or nom_colonne_jours not in df.columns:
        st.error("🚨 **Erreur de lecture des colonnes nécessaires**")
        st.stop()
        
    df[nom_colonne_jours] = pd.to_numeric(df[nom_colonne_jours], errors='coerce')
    df = df.drop_duplicates()
    df['Prix Unitaire'] = pd.to_numeric(df[nom_colonne_prix].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), errors='coerce').fillna(0)
    df['Quantité'] = pd.to_numeric(df[nom_colonne_qte], errors='coerce').fillna(0)
    df['Valeur Totale'] = df['Quantité'] * df['Prix Unitaire']
    return df

# ==========================================
# PANNEAU LATÉRAL (DÉTECTION & ENREGISTREMENT)
# ==========================================
st.sidebar.header("📂 Gestion des données")

file_to_load = None
mod_time = "Aucune donnée active"

# Détection automatisée du fichier persistant sur le serveur
if os.path.exists(SERVER_XLSX):
    file_to_load = SERVER_XLSX
    mod_time = datetime.fromtimestamp(os.path.getmtime(SERVER_XLSX)).strftime('%d/%m/%Y à %H:%M')
elif os.path.exists(SERVER_CSV):
    file_to_load = SERVER_CSV
    mod_time = datetime.fromtimestamp(os.path.getmtime(SERVER_CSV)).strftime('%d/%m/%Y à %H:%M')
elif os.path.exists(DEFAULT_XLSX):
    file_to_load = DEFAULT_XLSX
    mod_time = datetime.fromtimestamp(os.path.getmtime(DEFAULT_XLSX)).strftime('%d/%m/%Y à %H:%M')
elif os.path.exists(DEFAULT_CSV):
    file_to_load = DEFAULT_CSV
    mod_time = datetime.fromtimestamp(os.path.getmtime(DEFAULT_CSV)).strftime('%d/%m/%Y à %H:%M')

uploaded_file = st.sidebar.file_uploader("Mettre à jour le fichier DATA STOCK :", type=["xlsx", "csv"])

# Si un nouveau fichier est déposé, on l'écrit en dur sur le serveur pour le mémoriser
if uploaded_file is not None:
    if os.path.exists(SERVER_XLSX): os.remove(SERVER_XLSX)
    if os.path.exists(SERVER_CSV): os.remove(SERVER_CSV)
    
    target_path = SERVER_CSV if uploaded_file.name.endswith('.csv') else SERVER_XLSX
    with open(target_path, "wb") as f:
        f.write(uploaded_file.getvalue())
        
    st.sidebar.success("Fichier mémorisé sur le serveur !")
    st.cache_data.clear()
    st.rerun()

# Blocage de sécurité si aucun fichier n'existe nulle part
if file_to_load is None:
    st.title("📦 Tableau de Bord : Pilotage Magasin")
    st.info("👋 Bienvenue ! Aucun fichier n'est mémorisé.\n\nVeuillez glisser votre fichier de stock (Excel ou CSV) une première fois dans le menu latéral gauche.")
    st.stop()

st.sidebar.info(f"📅 **Date des données actives :**\n\n{mod_time}")

with open(file_to_load, "rb") as f: file_data_to_download = f.read()
download_name = "DATA_STOCK_Actuel.csv" if file_to_load.endswith('.csv') else "DATA_STOCK_Actuel.xlsx"
st.sidebar.download_button("📥 Télécharger la base actuelle", data=file_data_to_download, file_name=download_name, use_container_width=True)

st.sidebar.divider()
st.sidebar.header("⚙️ Paramètres d'analyse")
seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)

# Traitement des données chargées automatiquement
df = load_base_data(file_to_load).copy()
pattern = r'^([A-Za-z])(\d{2})([A-Za-z])(\d{2,3})$'
extracted = df['LOCATOR'].astype(str).str.extract(pattern)
df['Rangée'], df['Meuble'], df['Colonne'], df['Niveau'] = extracted[0].str.upper(), extracted[1], extracted[2].str.upper(), extracted[3]

# Synchronisation initiale du Jumeau numérique
df_valid_entries = df.dropna(subset=['Rangée'])
if not st.session_state.master_locations:
    st.session_state.master_locations = set(df_valid_entries['LOCATOR'].unique())
    save_config()
else:
    st.session_state.master_locations.update(df_valid_entries['LOCATOR'].unique())

list_rangees = ['A','B','C','D','E','F','G','H','J','K','L','M']
max_rack = 25 
CAPACITE_MAX_MAGASIN = len(st.session_state.master_locations)

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'
if 'edit_rangee' not in st.session_state: st.session_state.edit_rangee = 'A'
if 'edit_meuble' not in st.session_state: st.session_state.edit_meuble = '01'

# ==========================================
# EN-TÊTE ET KPIs
# ==========================================
total_refs = df['PART'].nunique()
df_valide = df[df['LOCATOR'].isin(st.session_state.master_locations)]
total_locs_magasin = df_valide['LOCATOR'].nunique()
taux_occupation = (total_locs_magasin / CAPACITE_MAX_MAGASIN * 100) if CAPACITE_MAX_MAGASIN > 0 else 0

list_exclus = list(st.session_state.exclusions.keys())
df_dormants = df[(df['Last consumption'] > seuil_dormant) & (~df['PART'].isin(list_exclus))]
nb_refs_dormantes = df_dormants['PART'].nunique()
capital_dormant = df_dormants['Valeur Totale'].sum()
pct_refs = (nb_refs_dormantes / total_refs * 100) if total_refs > 0 else 0

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1: st.markdown(f"""<div class="metric-card"><div class="metric-label">Taux d'Occupation</div><div class="metric-value">{taux_occupation:.1f}%</div><div class="metric-subtext-green">{total_locs_magasin} empl. occupés sur {CAPACITE_MAX_MAGASIN}</div></div>""", unsafe_allow_html=True)
with col_kpi2: st.markdown(f"""<div class="metric-card"><div class="metric-label">Références Totales</div><div class="metric-value">{total_refs}</div></div>""", unsafe_allow_html=True)
with col_kpi3: st.markdown(f"""<div class="metric-card metric-card-red"><div class="metric-label">Réf. Dormantes (> {seuil_dormant}j)</div><div class="metric-value">{nb_refs_dormantes}</div><div class="metric-subtext">({pct_refs:.1f}% du total)</div></div>""", unsafe_allow_html=True)
with col_kpi4: 
    capital_format = "{:,.0f} €".format(capital_dormant).replace(",", " ")
    st.markdown(f"""<div class="metric-card metric-card-gold"><div class="metric-label">Capital Immobilisé</div><div class="metric-value">{capital_format}</div><div class="metric-subtext">Dans les stocks dormants</div></div>""", unsafe_allow_html=True)

# ==========================================
# VUES (ONGLETS)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Vue Analytique", "🗺️ Vue Visuelle", "🚫 Dérogations", "🗄️ Éditeur du Jumeau Numérique"])

# ------------------------------------------
# ONGLET 1 : VUE ANALYTIQUE
# ------------------------------------------
with tab1:
    col_pareto, col_top15 = st.columns(2)
    with col_pareto:
        st.markdown("**Répartition des stocks dormants par Rangée**")
        df_dormants_pareto = df_dormants.copy()
        df_dormants_pareto['Rangée'] = df_dormants_pareto['Rangée'].fillna('Hors Standard')
        pareto_data = df_dormants_pareto.groupby('Rangée').size().reset_index(name='Nb_Dormants').sort_values(by='Nb_Dormants', ascending=False)
        if not pareto_data.empty:
            st.plotly_chart(px.bar(pareto_data, x='Rangée', y='Nb_Dormants', text_auto=True, labels={'Nb_Dormants': 'Nb. Réf. Dormantes'}, color_discrete_sequence=["#ff4b4b"]).update_layout(margin=dict(l=0, r=0, t=20, b=0), height=350), use_container_width=True)
            
    with col_top15:
        st.markdown("**Top 15 des emplacements avec le plus de dormants**")
        top_loc = df_dormants.groupby('LOCATOR').size().reset_index(name='Nb_Dormants').sort_values(by='Nb_Dormants', ascending=False).head(15)
        if not top_loc.empty:
            st.plotly_chart(px.bar(top_loc, x='LOCATOR', y='Nb_Dormants', text_auto=True, labels={'Nb_Dormants': 'Nb. Réf. Dormantes'}, color_discrete_sequence=["#ff4b4b"]).update_layout(margin=dict(l=0, r=0, t=20, b=0), height=350), use_container_width=True)
            
    st.divider()
    st.markdown("### 🔎 Base de données & Recherche")
    col_search1, col_search2 = st.columns(2)
    with col_search1: search_part = st.text_input("🔍 Rechercher une Référence (PART) :", "")
    with col_search2: search_loc = st.text_input("📍 Rechercher un Emplacement (LOCATOR) :", "")
        
    df_tab1 = df.copy()
    if search_part: df_tab1 = df_tab1[df_tab1['PART'].astype(str).str.contains(search_part, case=False, na=False)]
    if search_loc: df_tab1 = df_tab1[df_tab1['LOCATOR'].astype(str).str.contains(search_loc, case=False, na=False)]
    
    df_display = df_tab1[['PART', 'LOCATOR', 'Last consumption', 'Quantité', 'Valeur Totale']].copy()
    df_display['Last consumption'] = df_display['Last consumption'].fillna("Pas de données")
    st.dataframe(df_display.rename(columns={'Last consumption': 'Dernière consommation (jours)'}), height=350, use_container_width=True)

# ------------------------------------------
# ONGLET 2 : VUE VISUELLE
# ------------------------------------------
with tab2:
    st.markdown("### Plan Interactif du Magasin")
    st.markdown("""
    <div style='display: flex; gap: 15px; font-size: 13px; margin-bottom: 20px; padding: 10px; background-color: #f8f9fa; border: 1px solid #eaeaea; border-radius: 8px; color: #333;'>
        <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #ff4b4b; border-radius: 3px;'></div> <b>Stock Dormant</b></div>
        <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #f39c12; border-radius: 3px;'></div> <b>Pas de données</b></div>
        <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #00a8e8; border-radius: 3px;'></div> <b>Actif</b></div>
        <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #ffffff; border: 1px dashed #ccc; border-radius: 3px;'></div> <b>Vide (Sans stock)</b></div>
        <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #d1d8e0; border-radius: 3px;'></div> <b>Inexistant</b></div>
    </div>
    """, unsafe_allow_html=True)

    header_cols = st.columns([1] + [1]*max_rack, gap="small")
    for i in range(1, max_rack + 1): header_cols[i].markdown(f"<div style='text-align:center; font-size:11px; color:#888;'>{i:02d}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols = st.columns([1] + [1]*max_rack, gap="small")
        cols[0].markdown(f"<div style='text-align:center; font-weight:900; font-size: 16px; margin-top:3px;'>{r}</div>", unsafe_allow_html=True)
        
        for m in range(1, max_rack + 1):
            m_str = f"{m:02d}"
            if is_meuble_valid_for_row(r, m):
                df_m = df[(df['Rangée'] == r) & (df['Meuble'] == m_str)]
                meuble_locs_actifs = [loc for loc in st.session_state.master_locations if loc.startswith(f"{r}{m_str}")]
                
                if not meuble_locs_actifs: cols[m].button(m_str, key=f"btn_{r}_{m_str}_empty", disabled=True)
                else:
                    df_m_dormants = df_m[(df_m['Last consumption'] > seuil_dormant) & (~df_m['PART'].isin(list_exclus))]
                    has_dormant, has_unknown = not df_m_dormants.empty, df_m['Last consumption'].isna().any()
                    btn_type = "primary" if has_dormant else "tertiary" if has_unknown else "secondary"
                        
                    if cols[m].button(m_str, key=f"btn_{r}_{m_str}", type=btn_type):
                        st.session_state.sel_rangee, st.session_state.sel_meuble = r, m_str
            else: cols[m].write("")

    st.divider()
    r_sel, m_sel = st.session_state.sel_rangee, st.session_state.sel_meuble
    st.markdown(f"### Détail : Rangée <span style='color:#00a8e8;'>{r_sel}</span> - Meuble <span style='color:#00a8e8;'>{m_sel}</span>", unsafe_allow_html=True)
    
    df_meuble = df[(df['Rangée'] == r_sel) & (df['Meuble'] == m_sel)]
    colonnes, niveaux = get_meuble_structure(r_sel, m_sel)
    
    html_grid = "<table class='meuble-grid'><tr><th>NIV / COL</th>"
    for col in colonnes: html_grid += f"<th>{col}</th>"
    html_grid += "</tr>"
    
    for niv in niveaux:
        html_grid += f"<tr><td class='cell-niveau'>{niv}</td>"
        for col in colonnes:
            expected_loc = f"{r_sel}{m_sel}{col}{niv}"
            if expected_loc not in st.session_state.master_locations:
                html_grid += "<td class='cell-inexistant'>Inexistant</td>"
            else:
                items = df_meuble[(df_meuble['Colonne'] == col) & (df_meuble['Niveau'] == niv)]
                if items.empty: html_grid += "<td class='cell-vide'>Vide</td>"
                else:
                    parts_str = "<br>".join([str(p) for p in items['PART'].dropna().unique()])
                    has_dormant = not items[(items['Last consumption'] > seuil_dormant) & (~items['PART'].isin(list_exclus))].empty
                    has_unknown = items['Last consumption'].isna().any()
                    if has_dormant: html_grid += f"<td class='cell-dormant'>{parts_str}</td>"
                    elif has_unknown: html_grid += f"<td class='cell-inconnu'>{parts_str}</td>"
                    else: html_grid += f"<td class='cell-actif'>{parts_str}</td>"
        html_grid += "</tr>"
    st.markdown(html_grid + "</table>", unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 3 : EXCLUSIONS
# ------------------------------------------
with tab3:
    st.markdown("### 🚫 Registre des dérogations")
    with st.form("form_exclusion", clear_on_submit=True):
        col_form1, col_form2, col_form3 = st.columns([2, 3, 1])
        with col_form1: new_excl = st.text_input("Référence à exclure (PART) :")
        with col_form2: new_comm = st.text_input("Motif / Justification :")
        with col_form3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("➕ Ajouter") and new_excl:
                st.session_state.exclusions[new_excl] = new_comm
                save_config()
                st.rerun()

    st.divider()
    if st.session_state.exclusions:
        for excl, comm in list(st.session_state.exclusions.items()):
            col_list1, col_list2, col_list3 = st.columns([2, 5, 1])
            with col_list1: st.markdown(f"**{excl}**")
            with col_list2: st.markdown(f"*{comm}*")
            with col_list3:
                if st.button("❌ Retirer", key=f"del_{excl}"):
                    del st.session_state.exclusions[excl]
                    save_config()
                    st.rerun()
    else: st.success("Aucune exclusion active pour le moment.")

# ------------------------------------------
# ONGLET 4 : ÉDITEUR DU JUMEAU NUMÉRIQUE
# ------------------------------------------
with tab4:
    st.markdown("### 🗄️ Éditeur Interactif du Jumeau Numérique")
    header_cols_edit = st.columns([1] + [1]*max_rack, gap="small")
    for i in range(1, max_rack + 1): header_cols_edit[i].markdown(f"<div style='text-align:center; font-size:11px; color:#888;'>{i:02d}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols_edit = st.columns([1] + [1]*max_rack, gap="small")
        cols_edit[0].markdown(f"<div style='text-align:center; font-weight:900; font-size: 16px; margin-top:3px;'>{r}</div>", unsafe_allow_html=True)
        for m in range(1, max_rack + 1):
            m_str = f"{m:02d}"
            if is_meuble_valid_for_row(r, m):
                is_selected = (st.session_state.edit_rangee == r and st.session_state.edit_meuble == m_str)
                if cols_edit[m].button(m_str, key=f"btn_edit_{r}_{m_str}", type="primary" if is_selected else "secondary"):
                    st.session_state.edit_rangee, st.session_state.edit_meuble = r, m_str
            else: cols_edit[m].write("")

    st.divider()
    r_edit, m_edit = st.session_state.edit_rangee, st.session_state.edit_meuble
    st.markdown(f"### Modification : Rangée <span style='color:#00a8e8;'>{r_edit}</span> - Meuble <span style='color:#00a8e8;'>{m_edit}</span>", unsafe_allow_html=True)
    colonnes_edit, niveaux_edit = get_meuble_structure(r_edit, m_edit)
        
    cols_header = st.columns([1] + [1]*len(colonnes_edit))
    cols_header[0].markdown("<div style='text-align:center; color:#31333F; margin-top:10px;'><b>NIV / COL</b></div>", unsafe_allow_html=True)
    for j, col in enumerate(colonnes_edit):
        cols_header[j+1].button(f"↕️ {col}", key=f"tog_col_{r_edit}_{m_edit}_{col}", on_click=toggle_col, args=(r_edit, m_edit, col, niveaux_edit), use_container_width=True)
        
    st.write("") 
    for niv in niveaux_edit:
        cols_grid = st.columns([1] + [1]*len(colonnes_edit))
        cols_grid[0].button(f"↔️ {niv}", key=f"tog_niv_{r_edit}_{m_edit}_{niv}", on_click=toggle_niv, args=(r_edit, m_edit, niv, colonnes_edit), use_container_width=True)
        for j, col in enumerate(colonnes_edit):
            loc_id = f"{r_edit}{m_edit}{col}{niv}"
            exists = loc_id in st.session_state.master_locations
            cols_grid[j+1].button("🟢" if exists else "⬛", key=f"edit_btn_{loc_id}", on_click=toggle_loc, args=(loc_id,), use_container_width=True)

    st.write("")
    with st.expander("🛠️ Ajouter ou Retirer des Lignes / Colonnes"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Colonnes**")
            new_col = st.text_input("Nouvelle Colonne (ex: G) :", max_chars=1).upper()
            if st.button("➕ Ajouter Colonne") and new_col:
                modify_structure(r_edit, m_edit, "add", "col", new_col)
                st.rerun()
            del_col = st.selectbox("Supprimer complètement la colonne :", colonnes_edit)
            if st.button("🗑️ Supprimer Colonne"):
                modify_structure(r_edit, m_edit, "remove", "col", del_col)
                st.rerun()
        with c2:
            st.markdown("**Lignes (Niveaux)**")
            new_niv = st.text_input("Nouveau Niveau (ex: 060) :", max_chars=3)
            if st.button("➕ Ajouter Ligne") and new_niv:
                modify_structure(r_edit, m_edit, "add", "niv", new_niv)
                st.rerun()
            del_niv = st.selectbox("Supprimer complètement la ligne :", niveaux_edit)
            if st.button("🗑️ Supprimer Ligne"):
                modify_structure(r_edit, m_edit, "remove", "niv", del_niv)
                st.rerun()

    st.divider()
    with st.expander("⚠️ Options de Réinitialisation"):
        if st.button("🔄 Forcer la grille théorique complète", type="primary"):
            st.session_state.master_locations = set(generate_theoretical_locations())
            st.session_state.custom_structures = {}
            save_config()
            st.rerun()
