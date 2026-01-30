#!/usr/bin/env python3
"""
API Flask pour servir les PDFs stockés dans PostgreSQL
"""
from flask import Flask, send_file, jsonify, abort
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import io
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': url.hostname,
        'port': url.port,
        'database': url.path[1:],
        'user': url.username,
        'password': url.password
    }
else:
    DB_CONFIG = {
        'host': 'localhost',
        'port': '5432',
        'database': 'demarches',
        'user': 'postgres',
        'password': 'password'
    }

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/health')
def health():
    """Endpoint de santé"""
    return jsonify({'status': 'ok'})

@app.route('/pdf/<int:pdf_id>')
def get_pdf(pdf_id):
    """Récupérer un PDF par son ID"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT nom_fichier, contenu, taille
            FROM pdfs
            WHERE id = %s
        """, (pdf_id,))
        
        pdf = cur.fetchone()
        cur.close()
        conn.close()
        
        if not pdf:
            abort(404, description="PDF non trouvé")
        
        # Créer un objet BytesIO depuis le contenu
        pdf_bytes = io.BytesIO(pdf['contenu'])
        
        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=pdf['nom_fichier']
        )
        
    except Exception as e:
        abort(500, description=str(e))

@app.route('/dossier/<numero>/pdfs')
def get_dossier_pdfs(numero):
    """Lister tous les PDFs d'un dossier"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, nom_fichier, taille, date_upload
            FROM pdfs
            WHERE numero_dossier = %s
            ORDER BY date_upload DESC
        """, (numero,))
        
        pdfs = cur.fetchall()
        cur.close()
        conn.close()
        
        # Construire les URLs
        base_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
        for pdf in pdfs:
            pdf['url'] = f"{base_url}/pdf/{pdf['id']}"
            pdf['date_upload'] = pdf['date_upload'].isoformat() if pdf['date_upload'] else None
        
        return jsonify({
            'numero_dossier': numero,
            'nb_pdfs': len(pdfs),
            'pdfs': pdfs
        })
        
    except Exception as e:
        abort(500, description=str(e))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
