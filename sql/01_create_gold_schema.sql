-- Schéma en étoile — zone gold
-- Convention de nommage : dim_* pour les dimensions, fact_* pour la table de faits

CREATE TABLE IF NOT EXISTS dim_date (
    id_date         INT PRIMARY KEY,       -- format YYYYMMDD
    date_complete   DATE NOT NULL UNIQUE,
    annee           INT NOT NULL,
    mois            INT NOT NULL,
    jour_semaine    INT NOT NULL,          -- 1 = lundi ... 7 = dimanche
    jour_ouvre      BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_devise (
    id_devise       SERIAL PRIMARY KEY,
    code_iso        VARCHAR(3) NOT NULL UNIQUE,
    nom_devise      VARCHAR(50) NOT NULL,
    zone_economique VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_taux_change (
    id_taux                 SERIAL PRIMARY KEY,
    id_date                 INT NOT NULL REFERENCES dim_date(id_date),
    id_devise               INT NOT NULL REFERENCES dim_devise(id_devise),
    taux_valeur              NUMERIC(12, 6) NOT NULL,
    variation_veille_pct    NUMERIC(8, 4),
    load_ts                 TIMESTAMP NOT NULL DEFAULT now(),
    -- contrainte d'unicité : garantit l'idempotence du chargement (un seul taux par devise par jour)
    CONSTRAINT uq_fact_taux_date_devise UNIQUE (id_date, id_devise)
);

-- Données de référence pour la dimension devise (chargées une fois)
INSERT INTO dim_devise (code_iso, nom_devise, zone_economique) VALUES
    ('USD', 'Dollar américain', 'Amérique du Nord'),
    ('GBP', 'Livre sterling', 'Royaume-Uni'),
    ('CHF', 'Franc suisse', 'Europe (hors zone euro)')
ON CONFLICT (code_iso) DO NOTHING;
