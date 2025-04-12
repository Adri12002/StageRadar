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
        return []
    
    current_page = 1
    jobs = []
    previous_results_count = 0

    try:
        while True:
            url = f"https://www.welcometothejungle.com/fr/jobs?refinementList%5Boffices.country_code%5D%5B%5D=FR&refinementList%5Bcontract_type%5D%5B%5D=internship&query={search_term}&page={current_page}"
            st.write(f"🌐 Chargement de la page {current_page}...")
            
            try:
                driver.get(url)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-testid='search-results-list-item-wrapper']"))
                )
            except Exception as e:
                st.warning(f"Timeout ou erreur de chargement de la page {current_page}")
                break

            # Accepter les cookies
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "axeptio_btn_acceptAll"))
                )
                cookie_btn.click()
                time.sleep(1)
            except:
                pass

            # Trouver les containers des offres
            containers = driver.find_elements(By.CSS_SELECTOR, "li[data-testid='search-results-list-item-wrapper']")
            if not containers:
                break

            for container in containers[:30]:
                try:
                    job_data = {
                        "Titre": container.text.strip(),
                        "Lien": container.find_element(By.CSS_SELECTOR, "a").get_attribute("href"),
                        "Localisation": "Non précisé"
                    }
                    
                    try:
                        job_data["Localisation"] = container.find_element(
                            By.CSS_SELECTOR, "div[data-testid='job-location']"
                        ).text.strip()
                    except:
                        pass
                    
                    jobs.append(job_data)
                    
                except Exception as e:
                    continue

            if len(jobs) == previous_results_count:
                break
                
            previous_results_count = len(jobs)
            current_page += 1
            time.sleep(2)  # Be polite with delay between requests

    except Exception as e:
        st.error(f"Erreur lors du scraping: {str(e)}")
    finally:
        driver.quit()
        
    return jobs

# Fonctions de traitement des données (unchanged)
def save_to_excel(df, filename='resultats_stages.xlsx'):
    df.to_excel(filename, index=False)
    return filename

def split_title_column(df):
    for i, row in df.iterrows():
        titles = row['Titre'].split("\n")
        for idx, title in enumerate(titles):
            df.loc[i, f"Titre_{idx+1}"] = title.strip()
    return df

def get_last_non_empty_value(row):
    for col in reversed(row.index):
        if pd.notna(row[col]) and row[col] != '':
            return row[col]
    return None

def add_last_non_empty_column(df):
    df["Dernière_info"] = df.apply(get_last_non_empty_value, axis=1)
    return df

# Application Streamlit
st.title('StageRadar')

# Interface utilisateur
search_term = st.text_input('Rechercher un stage ou une entreprise')
location_filter = st.text_input('Filtrer par localisation (optionnel)')
contract_type = st.selectbox("Type de contrat", ['Stage', 'Alternance', 'CDI', 'CDD'])

if st.button("Lancer la recherche") and search_term:
    with st.spinner('Recherche en cours...'):
        results = scrape_wttj(search_term)
        
    if results:
        df = pd.DataFrame(results)
        
        if location_filter:
            df = df[df['Localisation'].str.contains(location_filter, case=False, na=False)]
        
        df = df.drop(columns=["Localisation"])
        df = split_title_column(df)
        df = add_last_non_empty_column(df)
        
        columns_to_remove = ['Titre', 'Titre_5', 'Titre_6', 'Titre_7']
        df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])

        cols = [col for col in df.columns if col != 'Lien']
        cols.append('Lien')
        df = df[cols]
        
        df.reset_index(drop=True, inplace=True)
        df.index += 1

        new_column_names = {
            "Titre_1": "Société",
            "Titre_2": "Poste",
            "Titre_3": "Lieu",
            "Titre_4": "Description"
        }
        df.rename(columns=new_column_names, inplace=True)

        excel_file = save_to_excel(df)
        
        st.success(f"{len(df)} offres trouvées!")
        st.dataframe(df)
        
        st.download_button(
            label="Télécharger le fichier Excel",
            data=open(excel_file, 'rb').read(),
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Aucune offre trouvée.")
