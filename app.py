import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuration de la page
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .metric-card {
        background-color: #2b2b2b;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        border-left: 5px solid #00a8e8;
        margin-bottom: 20px;
    }
    .metric-card-red {
        border-left-color: #ff4b4b;
    }
    .metric-value { font-size: 28px; font-weight: bold; color: white; }
    .metric-label { font-size: 14px; color: #aaaaaa; }
    
    /* Style pour la matrice du meuble */
    table.meuble-grid {
        width: 100%;
        border-collapse: collapse;
        text-align: center;
        color: #333;
        font-size: 12px;
    }
    table.meuble-grid th {
        background-color: #2c3e50;
        color: white;
        padding: 10px;
        border: 1px solid #ddd;
    }
    table.meuble-grid td {
        border: 1px solid #ddd;
        padding: 10px;
        width: 14%;
        vertical-align: middle;
        font-weight: bold;
    }
    .cell-vide { background-color: #dcdde1; color: #7f8fa6; }
    .cell-actif { background-color: #74b9ff; color: #000; }
    .cell-dormant { background-color: #ff7675; color: #000; }
    .cell-niveau { background-color: #bdc3c7; color: #2c3e50; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE TRAITEMENT ---
def filter_locators(loc):
    """ Filtre les emplacements de A01 à M21. """
    if pd.isna(loc):
        return False
    loc = str(loc)
    match = re.match(r'^([A-M])(0[1-9]|1[0-9]|2[0-1])', loc)
    if match:
        return True
    return False

@st.cache_data
def load_and_clean_data():
    df = pd.read_excel("Rangement magasin.xlsx", sheet_name="Bilan")
    
    # Conversion en numérique, ce qui transforme "Abs" en NaN (Not a Number)
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    
    # SUPPRESSION de toutes les lignes "Abs" (NaN)
    df = df.dropna(subset=['Last consumption'])
    
    df = df.drop_duplicates()
    df = df[df['LOCATOR'].apply(filter_locators)]
    
    # Extraction des coordonnées pour la Vue Magasin (ex: A01A010)
    # Rangée (A), Meuble (01), Colonne (A), Niveau (010)
    df['Rangée'] = df['LOCATOR'].str[0]
    df['Meuble'] = df['LOCATOR'].str[1:3]
    df['Colonne'] = df['LOCATOR'].str[3:4]
    df['Niveau'] = df['LOCATOR'].str[4:7]
    
    return df

df = load_and_clean_data()

# --- EN-TÊTE ET KPIs (Visibles sur toutes les vues) ---
st.title("📦 Vue d'Ensemble Magasin")

col_input, col_kpi1, col_kpi2 = st.columns([1, 1, 1])

with col_input:
    # Modification : Champ de saisie numérique au lieu d'un curseur
    seuil_dormant = st.number_input(
        "Seuil Stock Dormant (jours) :", 
        min_value=1, 
        value=365, 
        step=1,
        help="Saisissez la valeur à partir de laquelle une référence est considérée dormante."
    )

# Calculs globaux
total_refs = df['PART'].nunique()
df_dormants = df[df['Last consumption'] > seuil_dormant]
nb_dormants = df_dormants['PART'].nunique()

with col_kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Références Totales (A01 - M21)</div>
        <div class="metric-value">{total_refs}</div>
    </div>
    """, unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f"""
    <div class="metric-card metric-card-red">
        <div class="metric-label">Stocks Dormants (> {seuil_dormant}j)</div>
        <div class="metric-value">{nb_dormants}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- GESTION DES VUES (ONGLETS) ---
tab1, tab2 = st.tabs(["📊 Vue Analytique (Recherche & Priorités)", "🏢 Vue Visuelle (Plan du Magasin)"])

# ==========================================
# ONGLET 1 : VUE ANALYTIQUE (Tableau & Graphique)
# ==========================================
with tab1:
    st.subheader("Recherche ciblée et Chantiers 5S")
    
    # Filtres de recherche
    col_search1, col_search2 = st.columns(2)
    with col_search1:
        search_part = st.text_input("🔍 Rechercher une Référence (PART) :", "")
    with col_search2:
        search_loc = st.text_input("📍 Rechercher un Emplacement (LOCATOR) :", "")
        
    df_tab1 = df.copy()
    
    if search_part:
        df_tab1 = df_tab1[df_tab1['PART'].str.contains(search_part, case=False, na=False)]
    if search_loc:
        df_tab1 = df_tab1[df_tab1['LOCATOR'].str.contains(search_loc, case=False, na=False)]
        
    col_chart, col_table = st.columns([1.2, 1])
    
    with col_chart:
        st.markdown("**Top 15 des emplacements à trier en priorité (Nb de Réf. Dormantes)**")
        # Graphique des pires emplacements
        dormants_par_loc = df_dormants.groupby('LOCATOR').size().reset_index(name='Nb_Dormants')
        dormants_par_loc = dormants_par_loc.sort_values(by='Nb_Dormants', ascending=False).head(15)
        
        if not dormants_par_loc.empty:
            fig = px.bar(
                dormants_par_loc, 
                x='LOCATOR', 
                y='Nb_Dormants',
                labels={"LOCATOR": "Emplacement", "Nb_Dormants": "Réf. Dormantes"},
                color_discrete_sequence=["#ff4b4b"]
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Aucun stock dormant détecté avec ce seuil !")

    with col_table:
        st.markdown("**Base de données filtrée**")
        df_display = df_tab1[['PART', 'LOCATOR', 'Last consumption']].rename(columns={
            'PART': 'Référence', 'LOCATOR': 'Emplacement', 'Last consumption': 'Ancienneté (jours)'
        })
        st.dataframe(df_display, height=400, use_container_width=True)


# ==========================================
# ONGLET 2 : VUE MAGASIN (Détail par Meuble)
# ==========================================
with tab2:
    st.subheader("Détail du Meuble")
    
    # Sélecteurs pour simuler la grille de la photo
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    
    list_rangees = sorted(df['Rangée'].dropna().unique())
    list_meubles = sorted(df['Meuble'].dropna().unique())
    
    with col_sel1:
        sel_rangee = st.selectbox("Ligne / Rangée (A-M) :", list_rangees)
    with col_sel2:
        sel_meuble = st.selectbox("Meuble (01-21) :", list_meubles)
    
    # Filtrer les données pour ce meuble précis
    df_meuble = df[(df['Rangée'] == sel_rangee) & (df['Meuble'] == sel_meuble)]
    
    st.markdown(f"**Vue de face : Rangée {sel_rangee} - Meuble {sel_meuble}**")
    
    # Construction de la matrice HTML
    niveaux = ['050', '040', '030', '020', '010', '000']
    colonnes = ['F', 'E', 'D', 'C', 'B', 'A']
    
    html_grid = "<table class='meuble-grid'><tr><th>NIVEAU / EMPLACEMENT</th>"
    for col in colonnes:
        html_grid += f"<th>{col}</th>"
    html_grid += "</tr>"
    
    for niv in niveaux:
        html_grid += f"<tr><td class='cell-niveau'>{niv}</td>"
        for col in colonnes:
            # Trouver les pièces à cet emplacement précis
            items = df_meuble[(df_meuble['Colonne'] == col) & (df_meuble['Niveau'] == niv)]
            
            if items.empty:
                html_grid += "<td class='cell-vide'>Vide</td>"
            else:
                parts = items['PART'].unique()
                parts_str = "<br>".join(parts)
                # Vérifier s'il y a un stock dormant dans cet emplacement
                is_dormant = any(items['Last consumption'] > seuil_dormant)
                
                if is_dormant:
                    html_grid += f"<td class='cell-dormant'>{parts_str}</td>"
                else:
                    html_grid += f"<td class='cell-actif'>{parts_str}</td>"
        html_grid += "</tr>"
        
    html_grid += "</table>"
    
    # Affichage de la matrice
    st.markdown(html_grid, unsafe_allow_html=True)
    
    # Légende pour la matrice
    st.markdown("""
    <br>
    <div style='display: flex; gap: 20px; font-size: 14px;'>
        <div><span style='background-color:#74b9ff; padding: 2px 10px; border:1px solid #333;'>&nbsp;</span> Stock Actif</div>
        <div><span style='background-color:#ff7675; padding: 2px 10px; border:1px solid #333;'>&nbsp;</span> Stock Dormant (Dépasse le seuil)</div>
        <div><span style='background-color:#dcdde1; padding: 2px 10px; border:1px solid #333;'>&nbsp;</span> Emplacement Vide (ou non existant)</div>
    </div>
    """, unsafe_allow_html=True)
