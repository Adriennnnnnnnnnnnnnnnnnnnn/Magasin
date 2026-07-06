@st.cache_data
def load_and_clean_data():
    # Lecture du nouveau fichier
    df = pd.read_excel("Rangement magasin_2.xlsx", sheet_name="Bilan", engine="openpyxl")
    
    # --- NOMS EXACTS DES COLONNES SELON LE FICHIER ---
    nom_colonne_prix = "Unit Price €" 
    nom_colonne_qte = "Current Stock Qty"       
    
    # Vérification anti-plantage
    if nom_colonne_prix not in df.columns or nom_colonne_qte not in df.columns:
        st.error("🚨 **Erreur de lecture des colonnes financières**")
        st.warning(f"Impossible de trouver '{nom_colonne_prix}' ou '{nom_colonne_qte}'.")
        st.info(f"👉 **Colonnes détectées dans le fichier :** {', '.join(df.columns)}")
        st.stop() # Arrête l'exécution proprement
        
    df['Last consumption'] = pd.to_numeric(df['Last consumption'], errors='coerce')
    df = df.dropna(subset=['Last consumption'])
    df = df.drop_duplicates()
    df = df[df['LOCATOR'].apply(filter_locators)]
    
    df['Rangée'] = df['LOCATOR'].str[0]
    df['Meuble'] = df['LOCATOR'].str[1:3]
    df['Colonne'] = df['LOCATOR'].str[3:4]
    df['Niveau'] = df['LOCATOR'].str[4:7]
        
    # Nettoyage et conversion des prix (gestion des virgules et espaces)
    df['Prix Unitaire'] = pd.to_numeric(
        df[nom_colonne_prix].astype(str).str.replace(',', '.').str.replace('€', '').str.replace(' ', ''), 
        errors='coerce'
    ).fillna(0)
    
    # Conversion de la quantité en nombre
    df['Quantité'] = pd.to_numeric(df[nom_colonne_qte], errors='coerce').fillna(0)
    
    # Calcul de la valeur du stock par ligne
    df['Valeur Totale'] = df['Quantité'] * df['Prix Unitaire']
    
    return df
