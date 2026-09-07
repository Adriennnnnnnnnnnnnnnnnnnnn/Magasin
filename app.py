st.markdown("""
<style>
    /* 1. CARTES KPIs - Style SaaS moderne (fond blanc, bordure subtile, ombre douce) */
    .metric-card { 
        background-color: #ffffff; 
        border: 1px solid #e5e7eb;
        border-radius: 8px; 
        padding: 24px 20px; 
        text-align: left; 
        margin-bottom: 20px; 
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); 
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .metric-label { 
        font-size: 13px; 
        color: #6b7280; 
        font-weight: 600;
        text-transform: uppercase; 
        letter-spacing: 0.05em; 
    }
    .metric-value { 
        font-size: 28px; 
        font-weight: 700; 
        color: #111827; 
        line-height: 1; 
    }
    .metric-subtext { 
        font-size: 13px; 
        color: #ef4444; 
        font-weight: 500; 
    }
    .metric-subtext-green { 
        font-size: 13px; 
        color: #10b981; 
        font-weight: 500; 
    }
    
    /* 2. GRILLE DU MEUBLE - Style Badge / Tag moderne */
    table.meuble-grid { 
        width: 100%; 
        border-collapse: separate; 
        border-spacing: 6px; 
        text-align: center; 
        font-size: 12px; 
        margin-top: 15px; 
    }
    table.meuble-grid th { 
        color: #6b7280; 
        padding: 8px; 
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }
    table.meuble-grid td { 
        padding: 10px; 
        vertical-align: middle; 
        font-weight: 500; 
        border-radius: 6px; 
        transition: all 0.2s ease;
    }
    
    /* Couleurs douces pour les statuts (Fond clair + Texte foncé) */
    .cell-vide { 
        background-color: #f9fafb; 
        color: #9ca3af; 
        border: 1px dashed #d1d5db !important; 
    }
    .cell-inexistant { 
        background-color: transparent; 
        color: transparent; 
        border: none !important; 
    }
    .cell-actif { 
        background-color: #e0f2fe; /* Bleu très clair */
        color: #0284c7; /* Texte bleu foncé */
        border: 1px solid #bae6fd !important;
    }
    .cell-dormant { 
        background-color: #fee2e2; /* Rouge très clair */
        color: #dc2626; /* Texte rouge foncé */
        border: 1px solid #fecaca !important;
    }
    .cell-inconnu { 
        background-color: #fef3c7; /* Jaune très clair */
        color: #d97706; /* Texte jaune foncé */
        border: 1px solid #fde68a !important;
    }
    .cell-niveau { 
        background-color: transparent; 
        color: #4b5563; 
        font-weight: 600; 
        width: 60px; 
        text-align: right;
        padding-right: 15px;
    }
</style>
""", unsafe_allow_html=True)
