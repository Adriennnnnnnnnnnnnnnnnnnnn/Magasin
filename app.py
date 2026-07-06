import streamlit as st
import pandas as pd
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Vue d'Ensemble Magasin", page_icon="📦", layout="wide")

st.title("📦 Tableau de Bord : Gestion et Rangement du Magasin")
st.markdown("Application interactive pour le suivi des stocks et l'optimisation des emplacements (démarche 5S).")

@st.cache_data
def load_data():
    # Chargement de la feuille 'Bilan'
    df = pd.read_excel("Rangement magasin.xlsx", sheet_name="Bilan")
    
    # Nettoyage : conversion de 'Last consumption' en numérique (les valeurs 'Abs' deviennent des NaN)
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    
    # Suppression des doublons potentiels
    df = df.drop_duplicates()
    return df

df = load_data()

# --- KPIs ---
st.header("📊 Indicateurs Clés de Performance")
col1, col2, col3, col4 = st.columns(4)

total_refs = df['PART'].nunique()
total_locs = df['LOCATOR'].nunique()

# Définition d'un stock dormant (ex: plus de 365 jours sans consommation)
seuil_dormant = 365
stocks_dormants = df[df['Last consumption'] > seuil_dormant]
nb_dormants = stocks_dormants['PART'].nunique()

# Comptage des références sans date de consommation (anciennes valeurs 'Abs')
nb_nan = df['Last consumption'].isna().sum()

col1.metric("Références Uniques", total_refs)
col2.metric("Emplacements Occupés", total_locs)
col3.metric(f"Stocks Dormants (> {seuil_dormant}j)", nb_dormants)
col4.metric("Consommation Inconnue", nb_nan)

st.divider()

# --- Panneau latéral (Filtres) ---
st.sidebar.header("⚙️ Filtres d'Analyse")
selected_loc = st.sidebar.multiselect(
    "Filtrer par emplacement :", 
    options=sorted(df['LOCATOR'].dropna().astype(str).unique())
)

if selected_loc:
    df_filtered = df[df['LOCATOR'].isin(selected_loc)]
else:
    df_filtered = df

# --- Visualisations ---
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Répartition de l'ancienneté des consommations")
    fig1 = px.histogram(
        df_filtered, 
        x="Last consumption", 
        nbins=40, 
        title="Jours écoulés depuis la dernière consommation",
        labels={"Last consumption": "Jours", "count": "Fréquence d'apparition"},
        color_discrete_sequence=["#1f77b4"]
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.subheader("Top 10 des emplacements avec stocks dormants")
    # Regrouper les stocks dormants par emplacement
    dormants_par_loc = stocks_dormants.groupby('LOCATOR').size().reset_index(name='Nombre de références')
    dormants_par_loc = dormants_par_loc.sort_values(by='Nombre de références', ascending=False).head(10)
    
    fig2 = px.bar(
        dormants_par_loc, 
        x='LOCATOR', 
        y='Nombre de références',
        title="Cibles prioritaires pour le tri",
        labels={"LOCATOR": "Emplacement", "Nombre de références": "Nb. de références dormantes"},
        color_discrete_sequence=["#d62728"]
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- Données Brutes ---
st.subheader("📋 Base de Données Détaillée")
st.dataframe(df_filtered, use_container_width=True)
