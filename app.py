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

# --- FONCTION DE GÉNÉRATION DU MAGASIN THÉORIQUE ---
def generate_theoretical_locations():
    locs = []
    rangees = ['A','B','C','D','E','F','G','H','J','K','L','M']
    for r in rangees:
        for m in range(1, 26):
            m_str = f"{m:02d}"
            if r == 'M':
                cols = ['A', 'B', 'C']
                nivs = ['000', '010', '020'] if m_str in ['07', '08'] else ['000', '010', '020', '030', '040']
            else:
                cols = ['A', 'B', 'C', 'D', 'E', 'F']
                nivs = ['000', '010', '020', '030', '040', '050']

            for c in cols:
                for n in nivs:
                    locs.append(f"{r}{m_str}{c}{n}")
    return locs

# --- GESTION DE LA SAUVEGARDE (PERSISTANCE) ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                excl = data.get("exclusions", {})
                locs = set(data.get("master_locations", []))
                if not locs: locs = set(generate_theoretical_locations())
                return excl, locs
        except:
            pass
    return {}, set(generate_theoretical_locations())

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "exclusions": st.session_state.exclusions,
            "master_locations": list(st.session_state.master_locations)
        }, f, indent=4)

# --- INITIALISATION DES VARIABLES DE SESSION ---
if 'config_loaded' not in st.session_state:
    excl, locs = load_config()
    st.session_state.exclusions = excl
    st.session_state.master_locations = locs
    st.session_state.config_loaded = True

def toggle_loc(loc_id):
    if loc_id in st.session_state.master_locations:
        st.session_state.master_locations.remove(loc_id)
    else:
        st.session_state.master_locations.add(loc_id)
    save_config()

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

# --- FONCTION DE TRAITEMENT ---
def parse_file(file):
    if file.name.endswith('.csv'):
        content = file.getvalue().decode('utf-8', errors='ignore')
        delimiter = ';' if ';' in content.split('\n')[0] else ','
        file.seek(0)
        return pd.read_csv(file, sep=delimiter, encoding='utf-8', on_bad_lines='skip')
    else:
        return pd.read_excel(file, engine='openpyxl')

@st.cache_data
def load_base_data(file_source):
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
    df = df.drop_duplicates()
        
    df['Prix Unitaire'] = pd.to_numeric(df[nom_colonne_prix].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), errors='coerce').fillna(0)
    df['Quantité'] = pd.to_numeric(df[nom_colonne_qte], errors='coerce').fillna(0)
    df['Valeur Totale'] = df['Quantité'] * df['Prix Unitaire']
    
    return df

# ==========================================
# PANNEAU LATÉRAL (GESTION DU FICHIER)
# ==========================================
st.sidebar.header("📂 Gestion des données")

uploaded_file = st.sidebar.file_uploader("Importer le fichier DATA STOCK :", type=["xlsx", "csv"])

file_path_default = "DATA STOCK.xlsx"
fallback_path = "DATA STOCK.xlsx - Sheet1.csv" 

if uploaded_file is not None:
    file_to_load = uploaded_file
    mod_time = "À l'instant (Fichier importé)"
    file_data_to_download = uploaded_file.getvalue()
    download_name = uploaded_file.name
else:
    if os.path.exists(file_path_default): file_to_load = file_path_default
    elif os.path.exists(fallback_path): file_to_load = fallback_path
    else: file_to_load = None

    if file_to_load:
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_to_load)).strftime('%d/%m/%Y à %H:%M')
        with open(file_to_load, "rb") as f: file_data_to_download = f.read()
        download_name = "DATA_STOCK_Extract.xlsx"
    else:
        st.title("📦 Tableau de Bord : Pilotage Magasin")
        st.info("👋 Bienvenue ! Aucun fichier trouvé.\n\nVeuillez importer votre fichier de stock (Excel ou CSV) depuis le menu de gauche.")
        st.stop()

st.sidebar.info(f"📅 **Date des données actives :**\n\n{mod_time}")

if 'file_data_to_download' in locals() and file_data_to_download:
    st.sidebar.download_button(label="📥 Télécharger la base actuelle", data=file_data_to_download, file_name=download_name, use_container_width=True)

st.sidebar.divider()
st.sidebar.header("⚙️ Paramètres d'analyse")
seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)

# Chargement sécurisé
df = load_base_data(file_to_load).copy()

# Extraction dynamique des adresses
pattern = r'^([A-Za-z])(\d{2})([A-Za-z])(\d{2,3})$'
extracted = df['LOCATOR'].astype(str).str.extract(pattern)
df['Rangée'] = extracted[0].str.upper()
df['Meuble'] = extracted[1]
df['Colonne'] = extracted[2].str.upper()
df['Niveau'] = extracted[3]

list_rangees = sorted(df['Rangée'].dropna().unique())
max_rack = 25 if df['Meuble'].dropna().empty else max(25, int(df['Meuble'].dropna().astype(int).max()))
list_meubles_all = [f"{i:02d}" for i in range(1, max_rack + 1)]

CAPACITE_MAX_MAGASIN = len(st.session_state.master_locations)

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = list_rangees[0] if list_rangees else 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'
if 'edit_rangee' not in st.session_state: st.session_state.edit_rangee = list_rangees[0] if list_rangees else 'A'
if 'edit_meuble' not in st.session_state: st.session_state.edit_meuble = '01'

# ==========================================
# EN-TÊTE ET KPIs
# ==========================================
st.title("📦 Tableau de Bord : Pilotage Magasin")

total_refs = df['PART'].nunique()
# On ne compte l'occupation que sur les emplacements valides existant dans le Jumeau Numérique
df_valide = df[df['LOCATOR'].isin(st.session_state.master_locations)]
total_locs_magasin = df_valide['LOCATOR'].nunique()

taux_occupation = (total_locs_magasin / CAPACITE_MAX_MAGASIN * 100) if CAPACITE_MAX_MAGASIN > 0 else 0

list_exclus = list(st.session_state.exclusions.keys())
df_dormants = df[(df['Last consumption'] > seuil_dormant) & (~df['PART'].isin(list_exclus))]

nb_refs_dormantes = df_dormants['PART'].nunique()
capital_dormant = df_dormants['Valeur Totale'].sum()
pct_refs = (nb_refs_dormantes / total_refs * 100) if total_refs > 0 else 0

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1: 
    st.markdown(f"""<div class="metric-card"><div class="metric-label">Taux d'Occupation</div><div class="metric-value">{taux_occupation:.1f}%</div><div class="metric-subtext-green">{total_locs_magasin} empl. occupés sur {CAPACITE_MAX_MAGASIN}</div></div>""", unsafe_allow_html=True)
with col_kpi2: 
    st.markdown(f"""<div class="metric-card"><div class="metric-label">Références Totales</div><div class="metric-value">{total_refs}</div></div>""", unsafe_allow_html=True)
with col_kpi3: 
    st.markdown(f"""<div class="metric-card metric-card-red"><div class="metric-label">Réf. Dormantes (> {seuil_dormant}j)</div><div class="metric-value">{nb_refs_dormantes}</div><div class="metric-subtext">({pct_refs:.1f}% du total)</div></div>""", unsafe_allow_html=True)
with col_kpi4: 
    capital_format = "{:,.0f} €".format(capital_dormant).replace(",", " ")
    st.markdown(f"""<div class="metric-card metric-card-gold"><div class="metric-label">Capital Immobilisé</div><div class="metric-value">{capital_format}</div><div class="metric-subtext">Dans les stocks dormants</div></div>""", unsafe_allow_html=True)

# ==========================================
# VUES (ONGLETS)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Vue Analytique", "🗺️ Vue Visuelle", "🚫 Dérogations", "🗄️ Éditeur d'Emplacements"])

# ------------------------------------------
# ONGLET 1 : VUE ANALYTIQUE
# ------------------------------------------
with tab1:
    col_pareto, col_top15 = st.columns(2)
    with col_pareto:
        st.markdown("**Répartition des stocks dormants par Rangée**")
        df_dormants_pareto = df_dormants.copy()
        df_dormants_pareto['Rangée'] = df_dormants_pareto['Rangée'].fillna('Hors Standard')
        pareto_data = df_dormants_pareto.groupby('Rangée').size().reset_index(name='Nb_Dormants')
        pareto_data = pareto_data.sort_values(by='Nb_Dormants', ascending=False)
        if not pareto_data.empty:
            fig_pareto = px.bar(pareto_data, x='Rangée', y='Nb_Dormants', text_auto=True, labels={'Nb_Dormants': 'Nb. Réf. Dormantes'}, color_discrete_sequence=["#ff4b4b"])
            fig_pareto.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=350)
            st.plotly_chart(fig_pareto, use_container_width=True)
            
    with col_top15:
        st.markdown("**Top 15 des emplacements avec le plus de dormants**")
        top_loc = df_dormants.groupby('LOCATOR').size().reset_index(name='Nb_Dormants')
        top_loc = top_loc.sort_values(by='Nb_Dormants', ascending=False).head(15)
        if not top_loc.empty:
            fig = px.bar(top_loc, x='LOCATOR', y='Nb_Dormants', text_auto=True, labels={'Nb_Dormants': 'Nb. Réf. Dormantes'}, color_discrete_sequence=["#ff4b4b"])
            fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)
            
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
    df_display = df_display.rename(columns={'Last consumption': 'Dernière consommation (jours)'})
    st.dataframe(df_display, height=350, use_container_width=True)

# ------------------------------------------
# ONGLET 2 : VUE VISUELLE
# ------------------------------------------
with tab2:
    col_title, col_gauge = st.columns([3, 1])
    with col_title:
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
    
    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = total_locs_magasin,
            domain = {'x': [0, 1], 'y': [0, 1]}, title = {'text': "Occupation", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [None, CAPACITE_MAX_MAGASIN]},
                'bar': {'color': "#00a8e8"},
                'steps': [
                    {'range': [0, CAPACITE_MAX_MAGASIN*0.7], 'color': "#e0e4e8"},
                    {'range': [CAPACITE_MAX_MAGASIN*0.7, CAPACITE_MAX_MAGASIN*0.9], 'color': "#f1c40f"},
                    {'range': [CAPACITE_MAX_MAGASIN*0.9, CAPACITE_MAX_MAGASIN], 'color': "#ff4b4b"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': CAPACITE_MAX_MAGASIN}
            }
        ))
        fig_gauge.update_layout(margin=dict(l=10, r=60, t=60, b=10), height=200)
        st.plotly_chart(fig_gauge, use_container_width=True)

    header_cols = st.columns([1] + [1]*max_rack, gap="small")
    for i, m in enumerate(list_meubles_all):
        header_cols[i+1].markdown(f"<div style='text-align:center; font-size:11px; color:#888; margin-bottom:2px;'>{m}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols = st.columns([1] + [1]*max_rack, gap="small")
        cols[0].markdown(f"<div style='text-align:center; font-weight:900; font-size: 16px; margin-top:3px; color:#31333F;'>{r}</div>", unsafe_allow_html=True)
        
        for i, m in enumerate(list_meubles_all):
            df_m = df[(df['Rangée'] == r) & (df['Meuble'] == m)]
            
            # Filtre visuel : on regarde si ce meuble contient encore au moins un emplacement dans le jumeau numérique
            meuble_locs_theoriques = [loc for loc in st.session_state.master_locations if loc.startswith(f"{r}{m}")]
            
            if not meuble_locs_theoriques:
                cols[i+1].button(m, key=f"btn_{r}_{m}_empty", disabled=True)
            else:
                df_m_dormants = df_m[(df_m['Last consumption'] > seuil_dormant) & (~df_m['PART'].isin(list_exclus))]
                has_dormant = not df_m_dormants.empty
                has_unknown = df_m['Last consumption'].isna().any()
                
                if has_dormant: btn_type = "primary"
                elif has_unknown: btn_type = "tertiary"
                else: btn_type = "secondary"
                    
                if cols[i+1].button(m, key=f"btn_{r}_{m}", type=btn_type):
                    st.session_state.sel_rangee = r
                    st.session_state.sel_meuble = m

    st.divider()

    r_sel = st.session_state.sel_rangee
    m_sel = st.session_state.sel_meuble
    
    st.markdown(f"### Détail : Rangée <span style='color:#00a8e8;'>{r_sel}</span> - Meuble <span style='color:#00a8e8;'>{m_sel}</span>", unsafe_allow_html=True)
    
    df_meuble = df[(df['Rangée'] == r_sel) & (df['Meuble'] == m_sel)]
    
    if r_sel == 'M':
        colonnes = ['C', 'B', 'A']
        niveaux = ['020', '010', '000'] if m_sel in ['07', '08'] else ['040', '030', '020', '010', '000']
    else:
        niveaux = ['050', '040', '030', '020', '010', '000']
        colonnes = ['F', 'E', 'D', 'C', 'B', 'A']
    
    html_grid = "<table class='meuble-grid'><tr><th>NIV / COL</th>"
    for col in colonnes: html_grid += f"<th>{col}</th>"
    html_grid += "</tr>"
    
    for niv in niveaux:
        html_grid += f"<tr><td class='cell-niveau'>{niv}</td>"
        for col in colonnes:
            expected_loc = f"{r_sel}{m_sel}{col}{niv}"
            
            # Vérification dans la base maître
            if expected_loc not in st.session_state.master_locations:
                html_grid += "<td class='cell-inexistant'>Inexistant</td>"
            else:
                items = df_meuble[(df_meuble['Colonne'] == col) & (df_meuble['Niveau'] == niv)]
                if items.empty:
                    html_grid += "<td class='cell-vide'>Vide</td>"
                else:
                    parts = items['PART'].dropna().unique()
                    parts_str = "<br>".join([str(p) for p in parts])
                    
                    items_dormants = items[(items['Last consumption'] > seuil_dormant) & (~items['PART'].isin(list_exclus))]
                    has_dormant = not items_dormants.empty
                    has_unknown = items['Last consumption'].isna().any()
                    
                    if has_dormant:
                        html_grid += f"<td class='cell-dormant'>{parts_str}</td>"
                    elif has_unknown:
                        html_grid += f"<td class='cell-inconnu'>{parts_str}</td>"
                    else:
                        html_grid += f"<td class='cell-actif'>{parts_str}</td>"
        html_grid += "</tr>"
        
    html_grid += "</table>"
    st.markdown(html_grid, unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 3 : EXCLUSIONS
# ------------------------------------------
with tab3:
    st.markdown("### 🚫 Registre des dérogations")
    st.info("Les références ajoutées dans cette liste seront totalement exclues du calcul des stocks dormants.")
    
    with st.form("form_exclusion", clear_on_submit=True):
        col_form1, col_form2, col_form3 = st.columns([2, 3, 1])
        with col_form1: new_excl = st.text_input("Référence à exclure (PART) :")
        with col_form2: new_comm = st.text_input("Motif / Justification :")
        with col_form3: 
            st.markdown("<br>", unsafe_allow_html=True)
            submit_excl = st.form_submit_button("➕ Ajouter")
            
        if submit_excl and new_excl:
            st.session_state.exclusions[new_excl] = new_comm
            save_config()
            st.rerun()

    st.divider()

    if st.session_state.exclusions:
        st.markdown("**Liste des exclusions actives :**")
        for excl, comm in list(st.session_state.exclusions.items()):
            col_list1, col_list2, col_list3 = st.columns([2, 5, 1])
            with col_list1: st.markdown(f"**{excl}**")
            with col_list2: st.markdown(f"*{comm}*")
            with col_list3:
                if st.button("❌ Retirer", key=f"del_{excl}"):
                    del st.session_state.exclusions[excl]
                    save_config()
                    st.rerun()
    else:
        st.success("Aucune exclusion active pour le moment.")

# ------------------------------------------
# ONGLET 4 : ÉDITEUR D'EMPLACEMENTS (JUMEAU NUMÉRIQUE)
# ------------------------------------------
with tab4:
    st.markdown("### 🗄️ Éditeur Visuel du Jumeau Numérique")
    st.info("Cliquez sur un meuble pour afficher sa grille, puis cliquez sur chaque case pour définir si l'emplacement existe physiquement (ex: désactivez une case si le bac d'à côté prend deux places). Ces modifications sont **sauvegardées de façon permanente**.")

    # 1. Sélection du meuble à éditer
    header_cols_edit = st.columns([1] + [1]*max_rack, gap="small")
    for i, m in enumerate(list_meubles_all):
        header_cols_edit[i+1].markdown(f"<div style='text-align:center; font-size:11px; color:#888; margin-bottom:2px;'>{m}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols_edit = st.columns([1] + [1]*max_rack, gap="small")
        cols_edit[0].markdown(f"<div style='text-align:center; font-weight:900; font-size: 16px; margin-top:3px; color:#31333F;'>{r}</div>", unsafe_allow_html=True)
        
        for i, m in enumerate(list_meubles_all):
            if cols_edit[i+1].button(m, key=f"btn_edit_{r}_{m}"):
                st.session_state.edit_rangee = r
                st.session_state.edit_meuble = m

    st.divider()
    
    # 2. Affichage de la grille éditable
    r_edit = st.session_state.edit_rangee
    m_edit = st.session_state.edit_meuble
    
    st.markdown(f"### Édition : Rangée <span style='color:#00a8e8;'>{r_edit}</span> - Meuble <span style='color:#00a8e8;'>{m_edit}</span>", unsafe_allow_html=True)
    
    if r_edit == 'M':
        colonnes_edit = ['C', 'B', 'A']
        niveaux_edit = ['020', '010', '000'] if m_edit in ['07', '08'] else ['040', '030', '020', '010', '000']
    else:
        niveaux_edit = ['050', '040', '030', '020', '010', '000']
        colonnes_edit = ['F', 'E', 'D', 'C', 'B', 'A']
        
    # En-tête des colonnes pour la grille d'édition
    cols_header = st.columns([1] + [1]*len(colonnes_edit))
    cols_header[0].markdown("<div style='text-align:center; color:#31333F;'><b>NIV / COL</b></div>", unsafe_allow_html=True)
    for j, col in enumerate(colonnes_edit):
        cols_header[j+1].markdown(f"<div style='text-align:center; background-color:#f0f2f6; padding:10px; border-radius:4px;'><b>{col}</b></div>", unsafe_allow_html=True)
        
    st.write("") # Petit espace
    
    # Boutons d'édition par niveau
    for niv in niveaux_edit:
        cols_grid = st.columns([1] + [1]*len(colonnes_edit))
        cols_grid[0].markdown(f"<div style='text-align:center; background-color:#e0e4e8; padding:8px; border-radius:4px; margin-top:5px;'><b>{niv}</b></div>", unsafe_allow_html=True)
        
        for j, col in enumerate(colonnes_edit):
            loc_id = f"{r_edit}{m_edit}{col}{niv}"
            exists = loc_id in st.session_state.master_locations
            
            btn_label = "🟢 Existant" if exists else "⬛ Inexistant"
            
            # Un clic sur le bouton appellera la fonction toggle_loc pour ajouter ou retirer l'emplacement
            cols_grid[j+1].button(
                btn_label, 
                key=f"edit_btn_loc_{loc_id}", 
                on_click=toggle_loc, 
                args=(loc_id,),
                use_container_width=True
            )
