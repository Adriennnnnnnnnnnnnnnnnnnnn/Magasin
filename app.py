import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# Configuration de la page
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

# --- INITIALISATION DES VARIABLES DE SESSION ---
if 'exclusions' not in st.session_state:
    st.session_state.exclusions = {} # Format { 'REFERENCE': 'Commentaire' }

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .metric-card {
        background-color: #2b2b2b; border-radius: 8px; padding: 15px;
        text-align: center; border-left: 5px solid #00a8e8; margin-bottom: 20px;
    }
    .metric-card-red { border-left-color: #ff4b4b; }
    .metric-value { font-size: 28px; font-weight: bold; color: white; }
    .metric-label { font-size: 14px; color: #aaaaaa; }
    
    /* Style Matrice Détail Meuble */
    table.meuble-grid {
        width: 100%; border-collapse: collapse; text-align: center; color: #333; font-size: 12px;
    }
    table.meuble-grid th { background-color: #2c3e50; color: white; padding: 10px; border: 1px solid #ddd; }
    table.meuble-grid td { border: 1px solid #ddd; padding: 10px; width: 14%; vertical-align: middle; font-weight: bold; }
    .cell-vide { background-color: #dcdde1; color: #7f8fa6; }
    .cell-actif { background-color: #74b9ff; color: #000; }
    .cell-dormant { background-color: #ff7675; color: #000; }
    .cell-niveau { background-color: #bdc3c7; color: #2c3e50; font-weight: bold; }

    /* Forcer les couleurs des boutons de la grille interactive */
    button[kind="primary"] {
        background-color: #ff4b4b !important; /* Rouge pour dormants */
        border-color: #ff4b4b !important; color: white !important; padding: 0 !important;
    }
    button[kind="secondary"] {
        background-color: #0078ff !important; /* Bleu pour actifs */
        border-color: #0078ff !important; color: white !important; padding: 0 !important;
    }
    /* Les boutons désactivés (vides) restent gris par défaut dans Streamlit */
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE TRAITEMENT ---
def filter_locators(loc):
    if pd.isna(loc): return False
    loc = str(loc)
    match = re.match(r'^([A-M])(0[1-9]|1[0-9]|2[0-1])', loc)
    return bool(match)

@st.cache_data
def load_and_clean_data():
    df = pd.read_excel("Rangement magasin.xlsx", sheet_name="Bilan")
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    df = df.dropna(subset=['Last consumption'])
    df = df.drop_duplicates()
    df = df[df['LOCATOR'].apply(filter_locators)]
    
    df['Rangée'] = df['LOCATOR'].str[0]
    df['Meuble'] = df['LOCATOR'].str[1:3]
    df['Colonne'] = df['LOCATOR'].str[3:4]
    df['Niveau'] = df['LOCATOR'].str[4:7]
    return df

df = load_and_clean_data()

# --- INITIALISATION DE L'ÉTAT DU MEUBLE ---
list_rangees = sorted(df['Rangée'].dropna().unique())
list_meubles_all = [f"{i:02d}" for i in range(1, 22)]

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = list_rangees[0] if list_rangees else 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'


# ==========================================
# GESTION DES EXCLUSIONS (PANNEAU LATÉRAL)
# ==========================================
st.sidebar.header("⚙️ Paramètres & Règles")

seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)
st.sidebar.divider()

st.sidebar.subheader("🚫 Dérogations (Exclusions)")
st.sidebar.caption("Les références ajoutées ici ne seront pas considérées comme dormantes.")

with st.sidebar.expander("Gérer la liste d'exclusions"):
    new_excl = st.text_input("Référence à exclure (PART) :")
    new_comm = st.text_input("Motif / Justification :")
    if st.button("➕ Ajouter l'exclusion"):
        if new_excl:
            st.session_state.exclusions[new_excl] = new_comm
            st.rerun()
            
    if st.session_state.exclusions:
        st.markdown("**Liste actuelle :**")
        for excl, comm in list(st.session_state.exclusions.items()):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"<span style='font-size:12px;'><b>{excl}</b><br><i>{comm}</i></span>", unsafe_allow_html=True)
            if c2.button("❌", key=f"del_{excl}", help="Supprimer cette exclusion"):
                del st.session_state.exclusions[excl]
                st.rerun()

# ==========================================
# EN-TÊTE ET KPIs
# ==========================================
st.title("📦 Vue d'Ensemble Magasin")

# Calcul des KPIs en tenant compte des exclusions
total_refs = df['PART'].nunique()
total_locs = df['LOCATOR'].nunique()

# Filtrer les dormants (plus anciens que le seuil ET ne faisant pas partie des exclusions)
list_exclus = list(st.session_state.exclusions.keys())
df_dormants = df[(df['Last consumption'] > seuil_dormant) & (~df['PART'].isin(list_exclus))]

nb_refs_dormantes = df_dormants['PART'].nunique()
nb_locs_dormants = df_dormants['LOCATOR'].nunique()

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
with col_kpi1: st.markdown(f"""<div class="metric-card"><div class="metric-label">Références Totales</div><div class="metric-value">{total_refs}</div></div>""", unsafe_allow_html=True)
with col_kpi2: st.markdown(f"""<div class="metric-card"><div class="metric-label">Emplacements Utilisés</div><div class="metric-value">{total_locs}</div></div>""", unsafe_allow_html=True)
with col_kpi3: st.markdown(f"""<div class="metric-card metric-card-red"><div class="metric-label">Références Dormantes</div><div class="metric-value">{nb_refs_dormantes}</div></div>""", unsafe_allow_html=True)
with col_kpi4: st.markdown(f"""<div class="metric-card metric-card-red"><div class="metric-label">Emplacements avec Dormants</div><div class="metric-value">{nb_locs_dormants}</div></div>""", unsafe_allow_html=True)


# ==========================================
# VUES (ONGLETS)
# ==========================================
tab1, tab2 = st.tabs(["📊 Vue Analytique (Recherche & Pareto)", "🗺️ Vue Visuelle (Plan Interactif)"])

with tab1:
    # Ligne 1 : Les deux graphiques d'analyse 5S
    col_pareto, col_top15 = st.columns(2)
    
    with col_pareto:
        st.markdown("**Pareto des stocks dormants par Rangée (Chantiers prioritaires)**")
        # Préparation des données pour le Pareto
        pareto_data = df_dormants.groupby('Rangée').size().reset_index(name='Nb_Dormants')
        pareto_data = pareto_data.sort_values(by='Nb_Dormants', ascending=False)
        if not pareto_data.empty:
            pareto_data['Cumul_Pct'] = pareto_data['Nb_Dormants'].cumsum() / pareto_data['Nb_Dormants'].sum() * 100
            
            fig_pareto = go.Figure()
            fig_pareto.add_trace(go.Bar(x=pareto_data['Rangée'], y=pareto_data['Nb_Dormants'], name='Occurrences', marker_color='#ff4b4b'))
            fig_pareto.add_trace(go.Scatter(x=pareto_data['Rangée'], y=pareto_data['Cumul_Pct'], name='Cumul (%)', mode='lines+markers', yaxis='y2', marker_color='#00a8e8'))
            
            fig_pareto.update_layout(
                yaxis=dict(title='Nb Occurrences dormantes'),
                yaxis2=dict(title='Cumul (%)', overlaying='y', side='right', range=[0, 105]),
                legend=dict(x=0.01, y=0.99),
                margin=dict(l=0, r=0, t=20, b=0), height=350
            )
            st.plotly_chart(fig_pareto, use_container_width=True)
        else:
            st.success("Aucun stock dormant détecté !")

    with col_top15:
        st.markdown("**Top 15 des emplacements avec le plus de dormants**")
        top_loc = df_dormants.groupby('LOCATOR').size().reset_index(name='Nb_Dormants')
        top_loc = top_loc.sort_values(by='Nb_Dormants', ascending=False).head(15)
        if not top_loc.empty:
            fig = px.bar(top_loc, x='LOCATOR', y='Nb_Dormants', color_discrete_sequence=["#ff4b4b"])
            fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)
            
    st.divider()
    
    # Ligne 2 : Base de données et Recherche
    col_search1, col_search2 = st.columns(2)
    with col_search1: search_part = st.text_input("🔍 Rechercher une Référence (PART) :", "")
    with col_search2: search_loc = st.text_input("📍 Rechercher un Emplacement (LOCATOR) :", "")
        
    df_tab1 = df.copy()
    if search_part: df_tab1 = df_tab1[df_tab1['PART'].str.contains(search_part, case=False, na=False)]
    if search_loc: df_tab1 = df_tab1[df_tab1['LOCATOR'].str.contains(search_loc, case=False, na=False)]
    
    st.dataframe(df_tab1[['PART', 'LOCATOR', 'Last consumption']], height=300, use_container_width=True)


with tab2:
    st.subheader("Plan Interactif du Magasin")
    st.caption("Cliquez sur un numéro de meuble pour voir son détail. (🔴 Rouge = Présence de stocks dormants | 🔵 Bleu = Actif | ⚪ Gris = Vide/Inexistant)")
    
    # 1. Construction de la carte interactive
    header_cols = st.columns([1] + [1]*21, gap="small")
    for i in range(1, 22):
        header_cols[i].markdown(f"<div style='text-align:center; font-size:12px; color:#aaa; margin-bottom:5px;'>{i:02d}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols = st.columns([1] + [1]*21, gap="small")
        cols[0].markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px;'>{r}</div>", unsafe_allow_html=True)
        
        for i, m in enumerate(list_meubles_all):
            df_m = df[(df['Rangée'] == r) & (df['Meuble'] == m)]
            
            if df_m.empty:
                cols[i+1].button(m, key=f"btn_{r}_{m}_empty", disabled=True)
            else:
                # Appliquer la logique d'exclusion sur l'affichage visuel
                df_m_dormants = df_m[(df_m['Last consumption'] > seuil_dormant) & (~df_m['PART'].isin(list_exclus))]
                has_dormant = not df_m_dormants.empty
                
                btn_type = "primary" if has_dormant else "secondary"
                if cols[i+1].button(m, key=f"btn_{r}_{m}", type=btn_type):
                    st.session_state.sel_rangee = r
                    st.session_state.sel_meuble = m

    st.divider()

    # 2. Affichage du détail du meuble sélectionné
    r_sel = st.session_state.sel_rangee
    m_sel = st.session_state.sel_meuble
    
    st.markdown(f"### Détail : Rangée <span style='color:#00a8e8;'>{r_sel}</span> - Meuble <span style='color:#00a8e8;'>{m_sel}</span>", unsafe_allow_html=True)
    
    df_meuble = df[(df['Rangée'] == r_sel) & (df['Meuble'] == m_sel)]
    
    niveaux = ['050', '040', '030', '020', '010', '000']
    colonnes = ['F', 'E', 'D', 'C', 'B', 'A']
    
    html_grid = "<table class='meuble-grid'><tr><th>NIVEAU / EMPLACEMENT</th>"
    for col in colonnes: html_grid += f"<th>{col}</th>"
    html_grid += "</tr>"
    
    for niv in niveaux:
        html_grid += f"<tr><td class='cell-niveau'>{niv}</td>"
        for col in colonnes:
            items = df_meuble[(df_meuble['Colonne'] == col) & (df_meuble['Niveau'] == niv)]
            if items.empty:
                html_grid += "<td class='cell-vide'>Vide</td>"
            else:
                # CORRECTION DU BUG ICI : Conversion explicite en String pour la jointure
                parts = items['PART'].dropna().unique()
                parts_str = "<br>".join([str(p) for p in parts])
                
                # Vérification de dormance (hors exclusions)
                items_dormants = items[(items['Last consumption'] > seuil_dormant) & (~items['PART'].isin(list_exclus))]
                is_dormant = not items_dormants.empty
                
                if is_dormant:
                    html_grid += f"<td class='cell-dormant'>{parts_str}</td>"
                else:
                    html_grid += f"<td class='cell-actif'>{parts_str}</td>"
        html_grid += "</tr>"
        
    html_grid += "</table>"
    st.markdown(html_grid, unsafe_allow_html=True)
