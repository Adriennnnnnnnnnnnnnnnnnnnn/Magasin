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
if 'df_master' not in st.session_state:
    st.session_state.df_master = pd.DataFrame()
if 'last_update' not in st.session_state:
    st.session_state.last_update = "Aucune donnée"

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

# --- FONCTIONS DE TRAITEMENT ---
def filter_locators(loc):
    if pd.isna(loc): return False
    loc = str(loc)
    match = re.match(r'^([A-M])(0[1-9]|1[0-9]|2[0-5])', loc)
    return bool(match)

def parse_file(file):
    """Fonction robuste pour lire aussi bien du CSV (séparé par , ou ;) que du Excel"""
    if file.name.endswith('.csv'):
        # Détection du séparateur en lisant la première ligne
        content = file.getvalue().decode('utf-8', errors='ignore')
        delimiter = ';' if ';' in content.split('\n')[0] else ','
        file.seek(0) # On remet le curseur au début pour la lecture Pandas
        return pd.read_csv(file, sep=delimiter, encoding='utf-8', on_bad_lines='skip')
    else:
        return pd.read_excel(file, engine='openpyxl')

# ==========================================
# FENÊTRE POP-UP D'IMPORTATION (DIALOG)
# ==========================================
@st.dialog("📥 Importation et Fusion des données")
def import_data_modal():
    st.write("Veuillez importer les deux extractions pour mettre à jour le magasin.")
    
    file_mtd = st.file_uploader("1️⃣ Fichier MTD_INVENTORY (Emplacements)", type=["xlsx", "csv"], help="Doit contenir les colonnes PART et LOCATOR")
    file_omm = st.file_uploader("2️⃣ Fichier OneMMTool (Ancienneté & Valeur)", type=["xlsx", "csv"], help="Doit contenir Logistic Ref, Days Since Last Consumption, Unit Price € et Current Stock Qty")
    
    if st.button("Fusionner et Mettre à jour", type="primary", use_container_width=True):
        if file_mtd and file_omm:
            with st.spinner("Fusion des fichiers en cours..."):
                try:
                    df_mtd = parse_file(file_mtd)
                    df_omm = parse_file(file_omm)
                    
                    # Détection souple des colonnes pour éviter les plantages dus à un espace
                    col_part = [c for c in df_mtd.columns if 'part' in str(c).lower()][0]
                    col_loc = [c for c in df_mtd.columns if 'locator' in str(c).lower()][0]
                    
                    col_log_ref = [c for c in df_omm.columns if 'logistic ref' in str(c).lower()][0]
                    col_days = [c for c in df_omm.columns if 'last consumption' in str(c).lower()][0]
                    col_price = [c for c in df_omm.columns if 'price' in str(c).lower()][0]
                    col_qty = [c for c in df_omm.columns if 'stock qty' in str(c).lower() or 'quantit' in str(c).lower()][0]
                    
                    # 1. Fusion des deux fichiers (Liaison sur la Référence)
                    df_merged = pd.merge(df_mtd, df_omm, left_on=col_part, right_on=col_log_ref, how='left')
                    
                    # 2. Renommage des colonnes pour correspondre au code existant
                    df_merged = df_merged.rename(columns={
                        col_part: 'PART',
                        col_loc: 'LOCATOR',
                        col_days: 'Last consumption',
                        col_price: 'Prix Unitaire',
                        col_qty: 'Quantité'
                    })
                    
                    # 3. Nettoyage et formatage
                    df_merged['Last consumption'] = pd.to_numeric(df_merged['Last consumption'], errors='coerce')
                    df_merged = df_merged.dropna(subset=['Last consumption'])
                    df_merged = df_merged.drop_duplicates(subset=['PART', 'LOCATOR']) # Eviter les doublons
                    df_merged = df_merged[df_merged['LOCATOR'].apply(filter_locators)]
                    
                    df_merged['Rangée'] = df_merged['LOCATOR'].str[0]
                    df_merged['Meuble'] = df_merged['LOCATOR'].str[1:3]
                    df_merged['Colonne'] = df_merged['LOCATOR'].str[3:4]
                    df_merged['Niveau'] = df_merged['LOCATOR'].str[4:7]
                        
                    df_merged['Prix Unitaire'] = pd.to_numeric(
                        df_merged['Prix Unitaire'].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), 
                        errors='coerce'
                    ).fillna(0)
                    
                    df_merged['Quantité'] = pd.to_numeric(df_merged['Quantité'], errors='coerce').fillna(0)
                    df_merged['Valeur Totale'] = df_merged['Quantité'] * df_merged['Prix Unitaire']
                    
                    # 4. Sauvegarde dans la session et rafraichissement
                    st.session_state.df_master = df_merged
                    st.session_state.last_update = datetime.now().strftime('%d/%m/%Y à %H:%M')
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erreur lors de la fusion. Vérifiez que les fichiers contiennent les bonnes colonnes. (Détail: {e})")
        else:
            st.warning("⚠️ Veuillez importer les DEUX fichiers avant de fusionner.")

# ==========================================
# PANNEAU LATÉRAL (GESTION DU FICHIER ET PARAMÈTRES)
# ==========================================
st.sidebar.header("📂 Gestion des données")

# Nouveau bouton pour ouvrir la fenêtre pop-up
if st.sidebar.button("📥 Importer des données", type="primary", use_container_width=True):
    import_data_modal()

st.sidebar.info(f"📅 **Données actives du :**\n\n{st.session_state.last_update}")

# Option de téléchargement de la base fusionnée
if not st.session_state.df_master.empty:
    csv_merged = st.session_state.df_master.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    st.sidebar.download_button(
        label="📥 Télécharger la base fusionnée",
        data=csv_merged,
        file_name="Base_Magasin_Fusionnee.csv",
        mime="text/csv",
        use_container_width=True
    )

st.sidebar.divider()
st.sidebar.header("⚙️ Paramètres")
seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)

# ==========================================
# VERIFICATION DES DONNEES AVANT AFFICHAGE
# ==========================================
df = st.session_state.df_master

# Si aucune donnée n'est chargée, on affiche un écran d'accueil
if df.empty:
    st.title("📦 Tableau de Bord : Pilotage Magasin")
    st.info("👋 Bienvenue ! Le tableau de bord est actuellement vide.\n\nVeuillez cliquer sur le bouton **'📥 Importer des données'** dans le menu de gauche pour fusionner vos fichiers MTD_INVENTORY et OneMMTool.")
    st.stop() # On arrête l'exécution du code ici tant qu'il n'y a pas de données

# ---------------------------------------------------------
# LA SUITE DU CODE RESTE INCHANGÉE (CALCULS ET ONGLETS)
# ---------------------------------------------------------
list_rangees = sorted(df['Rangée'].dropna().unique())
list_meubles_all = [f"{i:02d}" for i in range(1, 26)]
CAPACITE_MAX_MAGASIN = len(list_rangees) * len(list_meubles_all) * 6 * 6

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = list_rangees[0] if list_rangees else 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'

# ==========================================
# EN-TÊTE ET KPIs
# ==========================================
st.title("📦 Tableau de Bord : Pilotage Magasin")

total_refs = df['PART'].nunique()
total_locs = df['LOCATOR'].nunique()
taux_occupation = (total_locs / CAPACITE_MAX_MAGASIN) * 100

list_exclus = list(st.session_state.exclusions.keys())
df_dormants = df[(df['Last consumption'] > seuil_dormant) & (~df['PART'].isin(list_exclus))]

nb_refs_dormantes = df_dormants['PART'].nunique()
capital_dormant = df_dormants['Valeur Totale'].sum()
pct_refs = (nb_refs_dormantes / total_refs * 100) if total_refs > 0 else 0

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1: 
    st.markdown(f"""<div class="metric-card"><div class="metric-label">Taux d'Occupation</div><div class="metric-value">{taux_occupation:.1f}%</div><div class="metric-subtext-green">{total_locs} emplacements pris</div></div>""", unsafe_allow_html=True)
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
tab1, tab2, tab3 = st.tabs(["📊 Vue Analytique & 5S", "🗺️ Vue Visuelle", "🚫 Dérogations & Exclusions"])

# ------------------------------------------
# ONGLET 1 : VUE ANALYTIQUE & 5S
# ------------------------------------------
with tab1:
    st.markdown("### 🛠️ Outils de terrain et Suivi")
    col_export, col_trend = st.columns([1, 2])
    
    with col_export:
        st.markdown("**Plan d'action de tri (5S)**")
        st.write("Générez la liste des emplacements prioritaires à traiter sur le terrain pour libérer de l'espace.")
        
        df_export = df_dormants[['LOCATOR', 'PART', 'Quantité', 'Prix Unitaire', 'Valeur Totale', 'Last consumption']].copy()
        df_export = df_export.rename(columns={'LOCATOR': 'Emplacement', 'PART': 'Référence', 'Last consumption': 'Jours inactifs'})
        df_export = df_export.sort_values(by='Valeur Totale', ascending=False)
        df_export['Action (Jeter/Déplacer/Garder)'] = ""
        df_export['Commentaires Opérateur'] = ""
        
        csv_export = df_export.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        
        st.download_button(label="📥 Exporter le plan d'action (CSV)", data=csv_export, file_name="Plan_Action_5S_Magasin.csv", mime="text/csv")

    with col_trend:
        st.markdown("**Évolution du capital immobilisé (Simulation 6 derniers mois)**")
        mois_labels = [(datetime.today() - relativedelta(months=i)).strftime('%b %Y') for i in range(5, -1, -1)]
        valeurs_historiques = [capital_dormant * (1 + (i*0.05)) for i in range(5, -1, -1)]
        
        df_hist = pd.DataFrame({'Mois': mois_labels, 'Capital': valeurs_historiques})
        fig_hist = px.line(df_hist, x='Mois', y='Capital', markers=True, color_discrete_sequence=["#f1c40f"])
        fig_hist.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=200, yaxis_title="Euros (€)")
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    col_pareto, col_top15 = st.columns(2)
    with col_pareto:
        st.markdown("**Répartition des stocks dormants par Rangée**")
        pareto_data = df_dormants.groupby('Rangée').size().reset_index(name='Nb_Dormants')
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
    if search_loc: df_tab1 = df_tab1[df_tab1['LOCATOR'].astype(str).str.contains(
