-- Logs techniques : une ligne par tentative d'extraction (succès ou échec)
CREATE TABLE IF NOT EXISTS log_technique (
    id              SERIAL PRIMARY KEY,
    execution_date  DATE NOT NULL,
    devise          VARCHAR(3) NOT NULL,
    etape           VARCHAR(30) NOT NULL,      -- extraction / bronze / silver / gold
    statut          VARCHAR(10) NOT NULL,      -- succes / echec
    message         TEXT,
    duree_ms        INT,
    horodatage      TIMESTAMP NOT NULL DEFAULT now()
);

-- Logs métier : une ligne par règle qualité appliquée sur un enregistrement
CREATE TABLE IF NOT EXISTS log_qualite (
    id              SERIAL PRIMARY KEY,
    execution_date  DATE NOT NULL,
    devise          VARCHAR(3) NOT NULL,
    regle           VARCHAR(30) NOT NULL,      -- completude / exactitude / coherence / fraicheur / unicite
    statut          VARCHAR(15) NOT NULL,      -- ok / quarantaine
    detail          TEXT,
    horodatage      TIMESTAMP NOT NULL DEFAULT now()
);
