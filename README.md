# SafeSite AI

Détection de non-conformité EPI (casque, gilet, masque, gants) sur flux vidéo de chantier, avec pipeline de données complet : détection et suivi, événements Kafka, lac de données, couche gold orchestrée par Airflow, suivi MLOps, détection de dérive, dashboard multi-caméras et agent text-to-SQL en lecture seule.

## Architecture

```
vidéo / RTSP (MediaMTX)
   -> YOLOv8s (modèle versionné, MLflow) + ByteTrack
   -> épisodes de violation (src/episodes.py)
   -> Kafka (topic d'événements, dead-letter + replay)
   -> src/event_consumer.py -> Postgres public.violations (événements bruts)
   -> S3 (LocalStack) : bronze (détections) / silver (épisodes), partition camera_id
Airflow (DAG gold_daily, 02:00) : public.violations -> gold.violations_hourly, gold.daily_summary
Consommateurs :
   - Dashboard Streamlit : agrégats <- gold, détail <- public.violations, dérive <- bronze
   - Agent text-to-SQL (LangGraph) : gold uniquement, rôle Postgres agent_ro (lecture seule)
```

Schéma : `docs/architecture.png`.

## Services (Docker)

| Service | Port | Rôle |
|---|---|---|
| Postgres | 5432 | événements bruts, schéma `gold`, base `airflow` |
| Adminer | 8080 | interface SQL |
| Kafka | 9092 | bus d'événements |
| MediaMTX | 8554 | serveur RTSP |
| LocalStack | 4566 | S3 local (bronze/silver) |
| Airflow api-server | 8081 | orchestration (fichier `docker-compose.airflow.yml`) |
| Streamlit (hors Docker) | 8501 | dashboard (`src/dashboard.py`) et page « Ask the agent » (`src/pages/ask_agent.py`) |

## Démarrage

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseigner les valeurs (voir ci-dessous)
docker compose up -d
docker compose -f docker-compose.airflow.yml up -d
streamlit run src/dashboard.py
```

Variables `.env` (voir `.env.example`) : `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`, `ROBOFLOW_API_KEY`, `AIRFLOW_UID`, `AGENT_PG_USER` / `AGENT_PG_PASSWORD` (rôle lecture seule), `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_FALLBACK_MODEL`, `GOOGLE_API_KEY`, `GEMINI_MODEL`. Ne jamais committer `.env`.

## Commandes utiles

```bash
python -m agent "combien de violations par caméra ?"   # agent en ligne de commande
python -m agent.evals                                   # évaluation (24 questions + 7 refus)
python scripts/rebuild_bronze.py --camera-id 2 --video <chemin.mp4>   # reconstruire le lac
pytest tests/
# backfill du gold pour un jour
airflow dags trigger gold_daily --conf '{"day": "2026-09-30"}'
```

## Résultats mesurés

- Gold : 2422 violations, 4 types canoniques (no_gloves 552, no_helmet 553, no_mask 262, no_vest 1055), 38 lignes journalières.
- Agent : 23/24 en strict, 24/24 avec projection, 7/7 refus, 1,00 essai en moyenne, latence médiane 1,2 s (max 4,6 s). Attaques par injection bloquées par le validateur (analyse SQL) puis par le rôle Postgres.
- Drift caméra 2 vs 3 : KS 0,482, PSI 0,136 (niveau « watch »).
- Reconstruction du lac : caméra 1 = 1704 détections / 11 épisodes ; caméra 2 = 2441 / 5 ; caméra 3 = 9102 / 3.

## Sécurité

Deux barrières indépendantes pour l'agent : validateur `agent/sql_guard.py` (une seule instruction SELECT, liste blanche `gold.*`, fonctions dangereuses interdites, LIMIT) et rôle Postgres `agent_ro` (lecture seule, schéma gold uniquement, timeout 5 s). Les clés API ne vivent que dans `.env`.

## Limites connues

- Les horodatages de la caméra 1 sont synthétiques (pic du 1er octobre, trou du 24 au 30 septembre) : les tendances par jour de cette caméra ne reflètent pas un site réel.
- Le lac LocalStack n'est pas persistant : malgré le volume `localstack_data`, le bucket a disparu après un `docker compose restart`. Après un redémarrage, reconstruire avec `scripts/rebuild_bronze.py` (jamais en rejouant `inference_service.py`, qui créerait des doublons). Les 2414 lignes de la caméra 1 en base ne sont pas reproduites par les 11 épisodes du bronze reconstruit.
- Pas d'authentification sur le dashboard, qui utilise un rôle Postgres administrateur.
- Le tableau d'événements bruts affiche les étiquettes d'origine ; seul le gold est normalisé.
- L'agent vérifie la sécurité d'une requête, pas la vérité de sa réponse : relire le SQL affiché.
- Les noms de modèles LLM gratuits changent vite ; les lister via l'API du fournisseur.

## Documentation

`docs/` : cadrage, contrats d'événements, évaluation, revue de fiabilité, résultats d'entraînement. `JOURNAL.md` : journal de bord. `LATER.md` : pistes différées.
