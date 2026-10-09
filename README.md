# Registered crime vs reality: dashboard

Streamlit dashboard for the social-work AI project: crimes against women and SC atrocities in India.

**Data:** NCRB *Crime in India 2023* (Vol I and II), NFHS-6 (2023-24) with NFHS-5 (2019-21) comparison, and a small exploratory survey.

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

## Deploy free (Streamlit Community Cloud)
1. Upload everything in this folder to a public GitHub repo, keeping the `data/` folder.
2. Go to share.streamlit.io, sign in with GitHub, click **Create app**.
3. Choose your repo, branch `main`, main file `app.py`, then **Deploy**.
4. Paste the app link in your report's annexure.

## Files
- `app.py` is the dashboard (4 tabs)
- `data/state_data.csv` is merged state-level NCRB and NFHS data (36 states/UTs)
- `data/india_states.geojson` is state boundaries for the maps
- `data/survey.csv` is survey responses (anonymous)
- `requirements.txt` lists the packages

Limits: NCRB counts registered cases, not true incidence. The survey is a convenience sample and exploratory only.
