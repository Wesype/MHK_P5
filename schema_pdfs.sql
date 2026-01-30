-- Table pour stocker les PDFs
CREATE TABLE IF NOT EXISTS pdfs (
    id SERIAL PRIMARY KEY,
    numero_dossier VARCHAR(50) NOT NULL,
    nom_fichier TEXT NOT NULL,
    contenu BYTEA NOT NULL,
    taille INTEGER NOT NULL,
    date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (numero_dossier) REFERENCES dossiers(numero) ON DELETE CASCADE
);

-- Index pour recherche rapide par dossier
CREATE INDEX IF NOT EXISTS idx_pdfs_numero_dossier ON pdfs(numero_dossier);

-- Index pour recherche par date
CREATE INDEX IF NOT EXISTS idx_pdfs_date_upload ON pdfs(date_upload DESC);
