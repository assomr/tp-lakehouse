# TP autonome — Pipeline Lakehouse + Airflow + Dashboard métier

## Cadrage métier

**Domaine** : suivi des taux de change de référence BCE (EUR -> USD, GBP, CHF)
pour la direction financière d'une entreprise exportatrice.

**Question métier** : sur la période observée, quelles devises ont connu une
variation significative face à l'EUR, et à quels moments un seuil a-t-il été
franchi — pour décider quand et sur quelle devise déclencher une couverture
de change (hedging) ?

**Destinataire** : le/la trésorier(ère) de l'entreprise.

Voir [`livrables/note_de_cadrage.md`](livrables/note_de_cadrage.md) pour la version détaillée.

## Démarrage

```bash
docker compose up -d --build
```

Attendre que tous les services soient `healthy` (`docker compose ps`), puis :
- Airflow UI : http://localhost:8080 (admin / admin)
- MinIO console : http://localhost:9001 (minioadmin / minioadmin)
- Metabase : http://localhost:3000

Le DAG `taux_change_frankfurter` est visible et déclenchable manuellement
dans l'UI Airflow ("Trigger DAG").

## Démonstration des 3 chemins

Captures disponibles dans [`livrables/captures/`](livrables/captures/).

### 1. Chemin nominal (`01_chemin_nominal.png`)
Toutes les tâches passent au vert, les 3 devises sont chargées en gold.

### 2. Chemin d'échec qualité (`02_chemin_echec_qualite.png`)
Le DAG reste vert, mais une règle qualité (fraîcheur) rejette les
enregistrements, qui partent en quarantaine (bucket `silver-quarantine`,
table `log_qualite` avec statut `quarantaine`). Reproductible en abaissant
temporairement `SEUIL_FRAICHEUR_JOURS` dans `scripts/quality/rules.py`.

### 3. Chemin d'échec technique (`03_chemin_echec_technique.png`)
La tâche `extract` échoue après épuisement des 3 `retries` (DAG rouge).
Reproductible en pointant temporairement `FRANKFURTER_BASE_URL` (dans
`scripts/extract/extract_frankfurter.py`) vers une URL invalide.

## Vérification de l'idempotence

Voir `sql/03_verification_idempotence.sql` et
`livrables/captures/04_verification_idempotence.png`. Rejouer plusieurs fois
le DAG sur la même date puis exécuter ces requêtes contre `postgres_gold` :
aucune duplication n'apparaît (contrainte `UNIQUE(id_date, id_devise)` +
`UPSERT`).

## Chargement de l'historique (backfill)

⚠️ Le mode `airflow dags backfill` s'est révélé instable avec les tâches
mappées dynamiquement (`.expand()`) de ce DAG : plusieurs jours exécutés en
parallèle provoquent des `deadlock` et des valeurs manquantes en amont.

Méthode fiable utilisée à la place : déclenchements séquentiels indépendants,
un jour à la fois, avec pause entre chaque run :

```bash
for i in $(seq 1 15); do
  D=$(python3 -c "from datetime import date, timedelta; print(date.today() - timedelta(days=$i))")
  docker exec tp-lakehouse-airflow-scheduler-1 airflow dags trigger taux_change_frankfurter -e "$D"
  sleep 75
done
```

## Dashboard Metabase (`livrables/captures/05_dashboard_metabase.png`)

Connecté à `postgres_gold`. Trois visualisations, chacune reliée à la
question métier :
- **Évolution des taux EUR vers USD/GBP/CHF** — graphique en ligne, répond à
  "quelle tendance sur la période".
- **Variation quotidienne par devise (dernier jour)** — graphique en barres,
  répond à "quel écart entre devises".
- **Devise la plus volatile aujourd'hui** — indicateur agrégé (KPI), répond à
  "quel seuil est franchi, sur quelle devise agir en priorité".

## Structure du projet
```
dags/                DAG Airflow (TaskFlow API)
scripts/
  common/             clients MinIO et Postgres partagés
  extract/            appel API Frankfurter -> bronze
  quality/            5 règles qualité
  transform/          bronze -> silver / quarantaine
  load/               silver -> gold (idempotent)
sql/                  DDL gold + logs + requêtes d'idempotence
docker/               Dockerfile Airflow
livrables/
  note_de_cadrage.md  note de cadrage métier (partie 1)
  captures/           captures d'écran des 3 chemins + idempotence + dashboard
docker-compose.yml
NAMING_CONVENTIONS.md
```