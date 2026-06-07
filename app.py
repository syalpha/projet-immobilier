import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import plotly.express as px
import io

# configuration de la page
st.set_page_config(page_title="Immobilier CoinAfrique", page_icon="🏠", layout="wide")

# titre principal
st.title("🏠 Projet Immobilier - CoinAfrique Sénégal")
st.write("Application de collecte et d'analyse de données immobilières")
st.markdown("---")

# parametres du scraping
url_base = "https://sn.coinafrique.com/categorie/immobilier"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ─── fonction pour scraper une page ─────────────────────────────────────────
def scraper_une_page(numero_page):
    url = url_base + "?page=" + str(numero_page)

    try:
        reponse = requests.get(url, headers=headers, timeout=30)
        reponse.raise_for_status()
    except requests.exceptions.ConnectTimeout:
        st.warning("Timeout sur la page " + str(numero_page) + " - on passe")
        return []
    except requests.exceptions.ConnectionError:
        st.warning("Erreur de connexion sur la page " + str(numero_page) + " - on passe")
        return []
    except Exception as e:
        st.warning("Erreur : " + str(e))
        return []

    soup = BeautifulSoup(reponse.text, "html.parser")

    annonces = soup.find_all("div", class_="col s6 m4 l3")

    liste_biens = []

    for annonce in annonces:
        bien = {
            "prix": None,
            "description": None,
            "localisation": None,
            "type_de_bien": None,
            "nombre_pieces": None,
            "nombre_salle_de_bain": None,
            "superficie": None,
            "url": None
        }

        # recuperer l'url
        lien = annonce.find("a", href=True)
        if lien:
            href = lien["href"]
            if href.startswith("http"):
                bien["url"] = href
            else:
                bien["url"] = "https://sn.coinafrique.com" + href

        # recuperer le prix
        prix_tag = annonce.find(class_=re.compile(r"price|prix", re.I))
        if prix_tag:
            bien["prix"] = prix_tag.get_text(strip=True)

        # recuperer la description et le type de bien
        titre_tag = annonce.find("p", class_=re.compile(r"title|name", re.I))
        if titre_tag is None:
            titre_tag = annonce.find("p")
        if titre_tag:
            bien["description"] = titre_tag.get_text(strip=True)
            texte = bien["description"].lower()
            if "villa" in texte:
                bien["type_de_bien"] = "Villa"
            elif "appartement" in texte:
                bien["type_de_bien"] = "Appartement"
            elif "terrain" in texte:
                bien["type_de_bien"] = "Terrain"
            elif "maison" in texte:
                bien["type_de_bien"] = "Maison"
            elif "bureau" in texte:
                bien["type_de_bien"] = "Bureau"
            elif "studio" in texte:
                bien["type_de_bien"] = "Studio"
            else:
                bien["type_de_bien"] = "Autre"

        # recuperer la localisation
        loc_tag = annonce.find(class_=re.compile(r"location|localisation", re.I))
        if loc_tag:
            bien["localisation"] = loc_tag.get_text(strip=True)

        # recuperer les autres infos dans le texte
        texte_complet = annonce.get_text(" ", strip=True)

        result_pieces = re.search(r"(\d+)\s*(?:pièces?|chambres?)", texte_complet, re.I)
        if result_pieces:
            bien["nombre_pieces"] = int(result_pieces.group(1))

        result_sdb = re.search(r"(\d+)\s*(?:salle[s]?\s*de\s*bain|sdb)", texte_complet, re.I)
        if result_sdb:
            bien["nombre_salle_de_bain"] = int(result_sdb.group(1))

        result_sup = re.search(r"(\d+[\.,]?\d*)\s*m²?", texte_complet, re.I)
        if result_sup:
            bien["superficie"] = result_sup.group(1)

        if bien["url"] is not None:
            liste_biens.append(bien)

    return liste_biens


# ─── fonction de nettoyage du prix ──────────────────────────────────────────
def convertir_prix(prix):
    if pd.isna(prix):
        return None
    prix_str = str(prix).replace(" ", "").replace("\xa0", "")
    prix_str = re.sub(r"[^\d]", "", prix_str)
    if prix_str == "":
        return None
    return float(prix_str)


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR - navigation
# ════════════════════════════════════════════════════════════════════════════
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["Scraping", "Visualisation", "Formulaire KoboToolbox"])


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 - SCRAPING
# ════════════════════════════════════════════════════════════════════════════
if page == "Scraping":
    st.header("Partie 1 - Collecte des données")
    st.write("Choisissez le nombre de pages à scraper puis cliquez sur le bouton.")

    # choix du nombre de pages
    nb_pages = st.number_input("Nombre de pages à scraper", min_value=1, max_value=50, value=2)

    # bouton pour lancer le scraping
    if st.button("🚀 Démarrer le scraping"):
        tous_les_biens = []

        # barre de progression
        barre = st.progress(0)
        texte_statut = st.empty()

        for i in range(1, nb_pages + 1):
            texte_statut.text("Scraping de la page " + str(i) + " sur " + str(nb_pages) + "...")
            barre.progress(i / nb_pages)

            biens_page = scraper_une_page(i)
            tous_les_biens.extend(biens_page)
            time.sleep(1)

        texte_statut.text("Scraping terminé !")

        if len(tous_les_biens) == 0:
            st.error("Aucune donnée récupérée. Vérifiez votre connexion.")
        else:
            # on cree le dataframe
            df = pd.DataFrame(tous_les_biens)

            # on nettoie
            df = df.drop_duplicates(subset=["url"])
            df = df.dropna(subset=["url"])
            df = df.reset_index(drop=True)

            # on sauvegarde dans la session pour l'utiliser dans les autres pages
            st.session_state["df"] = df

            st.success("Scraping terminé ! Nombre de biens récupérés : " + str(len(df)))

    # affichage du tableau si les données existent
    if "df" in st.session_state:
        df = st.session_state["df"]

        # métriques
        col1, col2, col3 = st.columns(3)
        col1.metric("Total biens", len(df))
        col2.metric("Types de bien", df["type_de_bien"].nunique())
        col3.metric("Localisations", df["localisation"].nunique())

        st.write("### Données collectées")
        st.dataframe(df, use_container_width=True)

        # bouton téléchargement
        csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️ Télécharger le dataset (CSV)",
            data=csv,
            file_name="dataset_coinafrique.csv",
            mime="text/csv"
        )
    else:
        st.info("Lancez d'abord le scraping pour voir les données.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 - VISUALISATION
# ════════════════════════════════════════════════════════════════════════════
elif page == "Visualisation":
    st.header("Partie 2 - Visualisation des données")

    if "df" not in st.session_state:
        st.warning("Aucune donnée disponible. Faites d'abord le scraping.")
    else:
        df = st.session_state["df"].copy()

        # nettoyage des prix
        df["prix_numerique"] = df["prix"].apply(convertir_prix)
        df["superficie_numerique"] = pd.to_numeric(df["superficie"], errors="coerce")

        st.success("Données chargées : " + str(len(df)) + " biens")

        # graphique 1 - repartition des types de bien
        st.subheader("Graphique 1 : Répartition des types de bien")
        type_count = df["type_de_bien"].value_counts().reset_index()
        type_count.columns = ["type_de_bien", "nombre"]
        fig1 = px.pie(
            type_count,
            names="type_de_bien",
            values="nombre",
            title="Répartition des types de bien",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig1, use_container_width=True)

        # graphique 2 - top quartiers les plus chers
        st.subheader("Graphique 2 : Top 10 des quartiers les plus chers")
        df_prix = df.dropna(subset=["localisation", "prix_numerique"])
        if len(df_prix) > 0:
            prix_par_quartier = df_prix.groupby("localisation")["prix_numerique"].mean().reset_index()
            prix_par_quartier.columns = ["localisation", "prix_moyen"]
            prix_par_quartier = prix_par_quartier.sort_values("prix_moyen", ascending=False).head(10)
            fig2 = px.bar(
                prix_par_quartier,
                x="prix_moyen",
                y="localisation",
                orientation="h",
                title="Top 10 des quartiers les plus chers (prix moyen en FCFA)",
                color="prix_moyen",
                color_continuous_scale="Reds"
            )
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Pas assez de données de prix pour ce graphique.")

        # graphique 3 - nombre d'annonces par localisation
        st.subheader("Graphique 3 : Nombre d'annonces par localisation")
        df_loc = df.dropna(subset=["localisation"])
        if len(df_loc) > 0:
            annonces_par_loc = df_loc["localisation"].value_counts().head(10).reset_index()
            annonces_par_loc.columns = ["localisation", "nombre_annonces"]
            fig3 = px.bar(
                annonces_par_loc,
                x="localisation",
                y="nombre_annonces",
                title="Nombre d'annonces par localisation (Top 10)",
                color="nombre_annonces",
                color_continuous_scale="Blues",
                text_auto=True
            )
            fig3.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Pas assez de données de localisation pour ce graphique.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 - KOBOTOOLBOX
# ════════════════════════════════════════════════════════════════════════════
elif page == "Formulaire KoboToolbox":
    st.header("Partie 3 - Formulaire KoboToolbox")
    st.write("Formulaire de collecte des besoins immobiliers des clients.")

    # remplacez ce lien par votre vrai lien kobotoolbox
    lien_kobo = "ttps://ee.kobotoolbox.org/x/iUKQhCaO"

    st.components.v1.iframe(src=lien_kobo, height=700, scrolling=True)

    st.info("Remplacez la variable lien_kobo dans le code par votre vrai lien Enketo KoboToolbox.")