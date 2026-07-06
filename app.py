import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
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

# --- FONCTIONS DE TRAITEMENT ---
def filter_locators(loc):
    if pd.isna(loc): return False
    loc = str(loc)
    match = re.match(r'^([A-M])(0[1-9]|1[0-9]|2[0-1])', loc)
    return bool(match)

@st.cache_data
def load_and_clean_data():
    # Lecture du nouveau fichier
    df = pd.read_excel("Rangement magasin_2.xlsx", sheet_name="Bilan")
    
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    df = df.dropna(subset=['Last consumption'])
    df = df.drop_duplicates()
    df = df[df['LOCATOR'].apply(filter_locators)]
    
    df['Rangée'] = df['LOCATOR'].str[0]
    df['Meuble'] = df['LOCATOR'].str[1:3]
    df['Colonne'] = df['LOCATOR'].str[3:4]
    df['Niveau'] = df['LOCATOR'].str[4:7]
    
    # --- INTÉGRATION DES VRAIES DONNÉES FINANCIÈRES ---
    # Recherche souple des colonnes ajoutées pour éviter les erreurs de frappe (espaces, majuscules)
    nom_colonne_prix = [c for c in df.columns if 'prix' in str(c).lower()][0]
    nom_colonne_qte = [c for c in df.columns if 'quantit' in str(c).lower() or 'stock' in str(c).lower()][0]
    
    # Nettoyage et conversion des prix (gestion des virgules, symboles € ou cellules vides)
    df['Prix Unitaire'] = pd.to_numeric(
        df[nom_colonne_prix].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), 
        errors='coerce'
    ).fillna(0)
    
    # Conversion de la quantité en nombre
    df['Quantité'] = pd.to_numeric(df[nom_colonne_qte], errors='coerce').fillna(0)
    
    # Calcul de la valeur du stock par ligne
    df['Valeur Totale'] = df['Quantité'] * df['Prix Unitaire']
    
    return df

df = load_and_clean_data()

list_rangees = sorted(df['Rangée'].dropna().unique())
list_meubles_all = [f"{i:02d}" for i in range(1, 22)]
CAPACITE_MAX_MAGASIN = len(list_rangees) * len(list_meubles_all) * 6 * 6

if 'sel_rangee' not in st.session_state: st.session_state.sel_rangee = list_rangees[0] if list_rangees else 'A'
if 'sel_meuble' not in st.session_state: st.session_state.sel_meuble = '01'

# ==========================================
# PARAMÈTRES (PANNEAU LATÉRAL)
# ==========================================
st.sidebar.header("⚙️ Paramètres")
seuil_dormant = st.sidebar.number_input("Seuil Stock Dormant (jours) :", min_value=1, value=365, step=1)

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
            <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #00a8e8; border-radius: 3px;'></div> <b>Actif</b></div>
            <div style='display: flex; align-items: center; gap: 5px;'><div style='width: 12px; height: 12px; background-color: #ffffff; border: 1px dashed #aaa; border-radius: 3px;'></div> <b>Vide / Inexistant</b></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = total_locs,
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
        fig_gauge.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=150)
        st.plotly_chart(fig_gauge, use_container_width=True)

    header_cols = st.columns([1] + [1]*21, gap="small")
    for i in range(1, 22):
        header_cols[i].markdown(f"<div style='text-align:center; font-size:11px; color:#888; margin-bottom:2px;'>{i:02d}</div>", unsafe_allow_html=True)
        
    for r in list_rangees:
        cols = st.columns([1] + [1]*21, gap="small")
        cols[0].markdown(f"<div style='text-align:center; font-weight:900; font-size: 16px; margin-top:3px; color:#31333F;'>{r}</div>", unsafe_allow_html=True)
        
        for i, m in enumerate(list_meubles_all):
            df_m = df[(df['Rangée'] == r) & (df['Meuble'] == m)]
            
            if df_m.empty:
                cols[i+1].button(m, key=f"btn_{r}_{m}_empty", disabled=True)
            else:
                df_m_dormants = df_m[(df_m['Last consumption'] > seuil_dormant) & (~df_m['PART'].isin(list_exclus))]
                has_dormant = not df_m_dormants.empty
                
                btn_type = "primary" if has_dormant else "secondary"
                if cols[i+1].button(m, key=f"btn_{r}_{m}", type=btn_type):
                    st.session_state.sel_rangee = r
                    st.session_state.sel_meuble = m

    st.divider()

    r_sel = st.session_state.sel_rangee
    m_sel = st.session_state.sel_meuble
    
    st.markdown(f"### Détail : Rangée <span style='color:#00a8e8;'>{r_sel}</span> - Meuble <span style='color:#00a8e8;'>{m_sel}</span>", unsafe_allow_html=True)
    
    df_meuble = df[(df['Rangée'] == r_sel) & (df['Meuble'] == m_sel)]
    
    niveaux = ['050', '040', '030', '020', '010', '000']
    colonnes = ['F', 'E', 'D', 'C', 'B', 'A']
    
    html_grid = "<table class='meuble-grid'><tr><th>NIV / COL</th>"
    for col in colonnes: html_grid += f"<th>{col}</th>"
    html_grid += "</tr>"
    
    for niv in niveaux:
        html_grid += f"<tr><td class='cell-niveau'>{niv}</td>"
        for col in colonnes:
            items = df_meuble[(df_meuble['Colonne'] == col) & (df_meuble['Niveau'] == niv)]
            if items.empty:
                html_grid += "<td class='cell-vide'>-</td>"
            else:
                parts = items['PART'].dropna().unique()
                parts_str = "<br>".join([str(p) for p in parts])
                
                items_dormants = items[(items['Last consumption'] > seuil_dormant) & (~items['PART'].isin(list_exclus))]
                is_dormant = not items_dormants.empty
                
                if is_dormant:
                    html_grid += f"<td class='cell-dormant'>{parts_str}</td>"
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
                    st.rerun()
    else:
        st.success("Aucune exclusion active pour le moment.")
