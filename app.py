import streamlit as st
import pandas as pd
import re

# Configuration de la page (mode large)
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

# --- STYLE CSS PERSONNALISÉ ---
# On injecte du CSS pour imiter le style "Dashboard moderne" de ta photo
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
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: white;
    }
    .metric-label {
        font-size: 14px;
        color: #aaaaaa;
    }
    .status-dot {
        height: 12px;
        width: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .status-red { background-color: #ff4b4b; }
    .status-green { background-color: #00cc96; }
    .status-gray { background-color: #888888; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE TRAITEMENT ---
def filter_locators(loc):
    """
    Filtre les emplacements pour ne garder que ceux de A01 à M21.
    Exclut tout le reste (MP, W06, etc.)
    """
    if pd.isna(loc):
        return False
    loc = str(loc)
    
    # Recherche un motif du type Lettre (A-M) suivie de deux chiffres
    match = re.match(r'^([A-M])(\d{2})', loc)
    if match:
        letter = match.group(1)
        number = int(match.group(2))
        
        # Si la lettre est M, le numéro ne doit pas dépasser 21
        if letter == 'M' and number > 21:
            return False
        return True
    return False

@st.cache_data
def load_and_clean_data():
    # Chargement
    df = pd.read_excel("Rangement magasin.xlsx", sheet_name="Bilan")
    
    # Conversion des jours (les 'Abs' ou erreurs deviennent NaN)
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    
    # Nettoyage des doublons
    df = df.drop_duplicates()
    
    # Application du filtre strict sur les emplacements (A01 -> M21)
    df = df[df['LOCATOR'].apply(filter_locators)]
    
    return df

# Chargement des données
df = load_and_clean_data()

# --- INTERFACE UTILISATEUR ---
st.title("📦 Vue d'Ensemble Magasin")

# --- FILTRES (Sidebar) ---
st.sidebar.header("⚙️ Paramètres")

# Filtre interactif pour définir le seuil de stock dormant
seuil_dormant = st.sidebar.slider(
    "Définir le seuil 'Stock Dormant' (jours) :", 
    min_value=30, 
    max_value=3000, 
    value=365, 
    step=30,
    help="Modifiez cette valeur pour voir en rouge les références qui n'ont pas été consommées depuis X jours."
)

st.sidebar.markdown("---")

# Filtre par emplacement (dynamique basé sur les données filtrées)
all_locators = sorted(df['LOCATOR'].dropna().astype(str).unique())
selected_locs = st.sidebar.multiselect(
    "Filtrer par Emplacement(s) :", 
    options=all_locators,
    placeholder="Ex: A01A010"
)

# Application du filtre de sélection
if selected_locs:
    df_display = df[df['LOCATOR'].isin(selected_locs)].copy()
else:
    df_display = df.copy()

# --- CALCUL DES KPIs ---
total_refs = df_display['PART'].nunique()
stocks_dormants = df_display[df_display['Last consumption'] > seuil_dormant]
nb_dormants = stocks_dormants['PART'].nunique()
nb_inconnus = df_display['Last consumption'].isna().sum()

# Affichage des KPIs façon cartes personnalisées
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Références Totales affichées</div>
        <div class="metric-value">{total_refs}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #ff4b4b;">
        <div class="metric-label">Stocks Dormants (> {seuil_dormant}j)</div>
        <div class="metric-value">{nb_dormants}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #888888;">
        <div class="metric-label">Consommation Inconnue (Abs)</div>
        <div class="metric-value">{nb_inconnus}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### Détail des Emplacements")

# --- FORMATAGE DU TABLEAU STYLE "DASHBOARD" ---
# On crée une nouvelle colonne pour le statut visuel
def get_status_html(days):
    if pd.isna(days):
        return '<span class="status-dot status-gray" title="Inconnu"></span> Inconnu'
    elif days > seuil_dormant:
        return f'<span class="status-dot status-red" title="Dormant"></span> {int(days)} jours'
    else:
        return f'<span class="status-dot status-green" title="Actif"></span> {int(days)} jours'

df_display['Statut (Dernière Cons.)'] = df_display['Last consumption'].apply(get_status_html)

# On réorganise et renomme pour l'affichage
df_final = df_display[['PART', 'LOCATOR', 'Statut (Dernière Cons.)']].rename(columns={
    'PART': 'Référence (Part)',
    'LOCATOR': 'Emplacement'
})

# Affichage du tableau en HTML pour permettre l'interprétation des pastilles de couleur
st.write(
    df_final.to_html(escape=False, index=False, classes="dataframe", border=0), 
    unsafe_allow_html=True
)

# Petit ajustement CSS pour le tableau HTML natif de Pandas dans Streamlit
st.markdown("""
<style>
    table.dataframe {
        width: 100%;
        color: white;
        text-align: left;
        border-collapse: collapse;
    }
    table.dataframe th {
        background-color: #1e1e1e;
        padding: 12px;
        border-bottom: 2px solid #333;
    }
    table.dataframe td {
        padding: 10px 12px;
        border-bottom: 1px solid #333;
    }
    table.dataframe tr:hover {
        background-color: #2b2b2b;
    }
</style>
""", unsafe_allow_html=True)
