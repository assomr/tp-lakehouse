# TP autonome — Pipeline Lakehouse + Airflow + Dashboard métier

## Cadrage métier

**Domaine** : suivi des taux de change de référence BCE (EUR -> USD, GBP, CHF)
pour la direction financière d'une entreprise exportatrice.

**Question métier** : sur la période observée, quelles devises ont connu une
variation significative face à l'EUR, et à quels moments un seuil a-t-il été
franchi — pour décider quand et sur quelle devise déclencher une couverture
de change (hedging) ?

**Destinataire** : le/la trésorier(ère) de l'entreprise.

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

### 1. Chemin nominal
Déclencher le DAG sur une date récente (jour ouvré). Toutes les tâches
passent au vert, les 3 devises sont chargées en gold.
```bash
# via l'UI : Trigger DAG w/ Config -> {"execution_date": "<date récente>"}
```
Vérifier : `SELECT * FROM fact_taux_change ORDER BY load_ts DESC LIMIT 3;`
dans `postgres_gold`.

### 2. Chemin d'échec qualité (DAG vert, donnée en quarantaine)
Pour démontrer ce chemin sans dépendre du hasard des données réelles,
modifier temporairement `SEUIL_FRAICHEUR_JOURS` dans
`scripts/quality/rules.py` à `0`, ou déclencher le DAG sur une
`execution_date` correspondant à un jour suivant un week-end/férié long
(l'écart de fraîcheur dépassera alors le seuil). Le DAG reste vert ; la
tâche `quality_and_clean` écrit dans le bucket `silver-quarantine` et logge
la raison dans `log_qualite` (statut `quarantaine`).

### 3. Chemin d'échec technique (DAG rouge)
Couper temporairement l'accès réseau au conteneur (ou pointer
`FRANKFURTER_BASE_URL` vers une URL invalide) avant de déclencher le DAG.
Après épuisement des 3 `retries`, la tâche `extract` échoue et le DAG passe
au rouge. Vérifier `log_technique` (statut `echec`).

## Vérification de l'idempotence
Voir `sql/03_verification_idempotence.sql`. Rejouer plusieurs fois le DAG
sur la même `execution_date` puis exécuter ces requêtes contre
`postgres_gold` : aucune duplication ne doit apparaître.

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
docker-compose.yml
NAMING_CONVENTIONS.md
```
