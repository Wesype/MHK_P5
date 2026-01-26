-- Table principale des dossiers (snapshot actuel)
CREATE TABLE IF NOT EXISTS dossiers (
    numero VARCHAR(50) PRIMARY KEY,
    titre TEXT,
    lien TEXT,
    categorie VARCHAR(50),
    statut VARCHAR(50),
    demandeur VARCHAR(255),
    date_creation VARCHAR(50),
    date_modification VARCHAR(50),
    page INTEGER
);

-- Table pour stocker les changements détectés
CREATE TABLE IF NOT EXISTS changements (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(50),
    type_changement VARCHAR(20), -- 'nouveau', 'modifie', 'supprime'
    ancien_statut VARCHAR(50),
    nouveau_statut VARCHAR(50),
    ancienne_categorie VARCHAR(50),
    nouvelle_categorie VARCHAR(50),
    date_detection TIMESTAMP DEFAULT NOW(),
    webhook_envoye BOOLEAN DEFAULT FALSE
);

-- Table pour tracker les dossiers expirants (sans dupliquer les données)
CREATE TABLE IF NOT EXISTS dossiers_expirants (
    numero VARCHAR(50) PRIMARY KEY,
    date_ajout TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_changements_date ON changements(date_detection);
CREATE INDEX IF NOT EXISTS idx_changements_webhook ON changements(webhook_envoye);
