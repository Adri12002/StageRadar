import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import sys
from selenium_stealth import stealth

# Configuration du driver Selenium
def setup_driver():
    chrome_options = Options()
    
    # Options for macOS
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1200,900")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # For local development on macOS, you might not need headless
    chrome_options.add_argument("--headless")  # Uncomment if you want headless
    
    try:
        # Use ChromeDriverManager with specific version
        service = Service(ChromeDriverManager().install())
        
        # Initialize driver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Apply stealth settings
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="MacIntel",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        
        return driver
        
    except Exception as e:
        print(f"Failed to initialize ChromeDriver: {str(e)}")
        return None

    # Fonction de scraping avec Selenium
def scrape_wttj(search_term):
    driver = setup_driver()
    if not driver:
        print("Erreur lors de l'initialisation du driver")
        return []

    current_page = 1  # Commence à partir de la première page
    jobs = []
    previous_results_count = 0  # Pour suivre le nombre de résultats sur la page précédente

    try:
        while True:  # Boucle infinie qui s'arrête lorsqu'il n'y a plus de résultats
            # Construction de l'URL avec le terme de recherche
            url = f"https://www.welcometothejungle.com/fr/jobs?refinementList%5Boffices.country_code%5D%5B%5D=FR&refinementList%5Bcontract_type%5D%5B%5D=internship&query={search_term}&page={current_page}"
            print(f"🌐 Loading page {current_page}: {url}")
            driver.get(url)

            # Attendre que la page charge (attendre que l'élément de résultat de recherche apparaisse)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-testid='search-results-list-item-wrapper']")))

            # Accepter les cookies si présents
            try:
                driver.find_element(By.ID, "axeptio_btn_acceptAll").click()
                print("✅ Accepted cookies")
                time.sleep(1)
            except:
                print("ℹ️ No cookie popup found")

            # Trouver les containers des offres
            containers = driver.find_elements(By.CSS_SELECTOR, "li[data-testid='search-results-list-item-wrapper']")
            print(f"🔍 Found {len(containers)} job containers on page {current_page}")

            if len(containers) == 0:
                print("⚠️ No results found on this page, stopping.")
                break  # Arrêter si aucune offre n'est trouvée

            # Ajouter les résultats de cette page
            for container in containers[:30]:  # Récupérer les 30 premiers containers
                try:
                    job_data = {
                        "Titre": container.text.strip(),
                        "HTML": container.get_attribute("outerHTML"),
                    }
            
                    # Vérifier si l'élément <a> existe avant de tenter de récupérer le lien
                    link_el = container.find_element(By.CSS_SELECTOR, "a")
                    if link_el:
                        job_data["Lien"] = link_el.get_attribute("href")
                    else:
                        job_data["Lien"] = "Lien non disponible"  # Ou autre valeur par défaut
            
                    # Extraire la localisation (par exemple, s'il y a une mention de ville dans le texte)
                    location = "Non précisé"
                    try:
                        location_el = container.find_element(By.CSS_SELECTOR, "div[data-testid='job-location']")
                        location = location_el.text.strip()
                    except:
                        pass  # Si aucun emplacement n'est trouvé, on laisse "Non précisé"
            
                    job_data["Localisation"] = location
                    jobs.append(job_data)
                    print(f"✅ Extracted job with {len(job_data['Titre'])} characters of raw text")
            
                except Exception as e:
                    print(f"⚠️ Failed to extract from container: {str(e)[:100]}...")
                    continue


            # Vérifier si le nombre de résultats a changé par rapport à la page précédente
            if len(jobs) == previous_results_count:
                print("⚠️ No new results found, stopping.")
                break  # Si aucun nouveau résultat n'a été trouvé, on arrête

            previous_results_count = len(jobs)  # Mettre à jour le nombre de résultats précédents                
            current_page += 1  # Passer à la page suivante

    except Exception as e:
        print(f"⚠️ An error occurred: {str(e)}")
    
    # Vérifier que le driver est bien initialisé avant de le quitter
    if driver:
        driver.quit()  # Fermer le driver après le scraping
    return jobs


# Fonction pour séparer la colonne Titre en fonction des lignes d'éléments du JSON
def split_title_column(df):
    # Créer une nouvelle colonne pour chaque partie du titre séparée par un saut de ligne
    for i, row in df.iterrows():
        # Séparer le titre en une liste en utilisant le saut de ligne
        titles = row['Titre'].split("\n")
        
        # Ajouter une colonne pour chaque élément de la liste, en vérifiant la longueur
        for idx, title in enumerate(titles):
            df.loc[i, f"Titre_{idx+1}"] = title.strip()  # Ajouter à la colonne Titre_1, Titre_2, etc.
    
    return df

# Fonction pour récupérer la dernière valeur non vide dans la ligne
def get_last_non_empty_value(row):
    # On commence par la dernière colonne et on remonte
    for col in reversed(row.index):  # Inclure aussi la dernière colonne
        if pd.notna(row[col]) and row[col] != '':
            return row[col]
    return None

# Fonction pour ajouter la dernière information non vide à sa gauche
def add_last_non_empty_column(df):
    df["Dernière_info"] = df.apply(get_last_non_empty_value, axis=1)
    return df

# Application Streamlit
st.title('StageRadar')

# Champ de recherche pour un stage ou une entreprise
search_term = st.text_input('Rechercher un stage ou une entreprise')

# Champ de recherche pour la localisation (optionnel)
location_filter = st.text_input('Filtrer par localisation (optionnel)')

# Champ de filtre par type de contrat
contract_type = st.selectbox("Type de contrat", ['Stage', 'Alternance', 'CDI', 'CDD'])

# Bouton de recherche avec l'icône
if search_term:
    st.write(f"Résultats pour : {search_term}")
    
    # Scraper les données
    results = scrape_wttj(search_term)
    
    if results:
        st.write(f"Voici les {len(results)} offres de stage trouvées :")
        
        # Convertir les résultats en DataFrame pour afficher sous forme de tableau
        df = pd.DataFrame(results)
        
        # Si un filtre de localisation est spécifié, on l'applique
        if location_filter:
            df = df[df['Localisation'].str.contains(location_filter, case=False, na=False)]
            st.write(f"Résultats filtrés par localisation : {location_filter}")
        
        # Supprimer la colonne "HTML" et "Localisation"
        df = df.drop(columns=["HTML", "Localisation"])
        
        # Séparer la colonne "Titre" en fonction des lignes d'éléments du JSON
        df = split_title_column(df)
        
        # Ajouter la colonne avec la dernière info non vide à sa gauche
        df = add_last_non_empty_column(df)
        
        # Supprimer les colonnes Titre, Titre_5, et Titre_6 et Titre_7
        columns_to_remove = ['Titre', 'Titre_5', 'Titre_6', 'Titre_7']
        df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])

        # Réorganiser les colonnes pour que le lien soit à la fin
        cols = [col for col in df.columns if col != 'Lien']  # Liste des colonnes sans 'Lien'
        cols.append('Lien')  # Ajouter 'Lien' à la fin
        df = df[cols]  # Réorganiser le DataFrame
        
        # Réinitialiser l'index pour commencer à 1
        df.reset_index(drop=True, inplace=True)
        df.index += 1  # Modifier l'index pour commencer à 1

        # Renommer les colonnes d'office
        new_column_names = {
            "Titre_1": "Société",
            "Titre_2": "Poste",
            "Titre_3": "Lieu",
            "Titre_4": "Description"
        }
        df.rename(columns=new_column_names, inplace=True)

        # Sauvegarder le DataFrame dans un fichier Excel
        excel_file = save_to_excel(df)
        
        st.write("Télécharger les résultats :")
        st.download_button(
        label="Télécharger le fichier Excel",
        data=open(excel_file, 'rb').read(),
        file_name=excel_file,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Afficher le DataFrame sous forme de tableau interactif
        st.dataframe(df)

    else:
        st.write("Aucune offre trouvée.")
else:
    st.write("Entrez un terme pour commencer la recherche.")
