import csv
import json
from collections import Counter

def find_duplicates_csv(filename='dossiers_complets.csv'):
    """Trouve les doublons dans le fichier CSV"""
    numeros = []
    dossiers_by_numero = {}
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            numero = row['numero']
            numeros.append(numero)
            
            if numero not in dossiers_by_numero:
                dossiers_by_numero[numero] = []
            dossiers_by_numero[numero].append(row)
    
    # Compter les occurrences
    counter = Counter(numeros)
    duplicates = {num: count for num, count in counter.items() if count > 1}
    
    return duplicates, dossiers_by_numero

def find_duplicates_json(filename='dossiers_complets.json'):
    """Trouve les doublons dans le fichier JSON"""
    with open(filename, 'r', encoding='utf-8') as f:
        dossiers = json.load(f)
    
    numeros = [d['numero'] for d in dossiers]
    dossiers_by_numero = {}
    
    for dossier in dossiers:
        numero = dossier['numero']
        if numero not in dossiers_by_numero:
            dossiers_by_numero[numero] = []
        dossiers_by_numero[numero].append(dossier)
    
    counter = Counter(numeros)
    duplicates = {num: count for num, count in counter.items() if count > 1}
    
    return duplicates, dossiers_by_numero

def display_duplicates(duplicates, dossiers_by_numero):
    """Affiche les doublons de manière détaillée"""
    if not duplicates:
        print("✅ Aucun doublon trouvé!")
        return
    
    print(f"\n{'='*60}")
    print(f"🔍 {len(duplicates)} numéros de dossier en doublon")
    print(f"   Total d'occurrences en double: {sum(duplicates.values()) - len(duplicates)}")
    print(f"{'='*60}\n")
    
    for numero, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
        print(f"📋 Dossier {numero} - {count} occurrences:")
        
        for i, dossier in enumerate(dossiers_by_numero[numero], 1):
            print(f"   [{i}] Catégorie: {dossier['categorie']:<20} | "
                  f"Statut: {dossier['statut']:<20} | "
                  f"Page: {dossier['page']}")
        print()

def save_duplicates_report(duplicates, dossiers_by_numero, filename='doublons_rapport.json'):
    """Sauvegarde un rapport des doublons"""
    rapport = []
    
    for numero, count in duplicates.items():
        rapport.append({
            'numero': numero,
            'occurrences': count,
            'dossiers': dossiers_by_numero[numero]
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Rapport sauvegardé dans {filename}")

def remove_duplicates_keep_first(input_file='dossiers_complets.json', 
                                  output_file='dossiers_sans_doublons.json'):
    """Supprime les doublons en gardant la première occurrence"""
    with open(input_file, 'r', encoding='utf-8') as f:
        dossiers = json.load(f)
    
    seen = set()
    unique_dossiers = []
    duplicates_removed = 0
    
    for dossier in dossiers:
        numero = dossier['numero']
        if numero not in seen:
            seen.add(numero)
            unique_dossiers.append(dossier)
        else:
            duplicates_removed += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_dossiers, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Doublons supprimés: {duplicates_removed}")
    print(f"📊 Dossiers uniques: {len(unique_dossiers)}")
    print(f"💾 Fichier nettoyé: {output_file}")

if __name__ == "__main__":
    print("🔍 Analyse des doublons dans dossiers_complets.json\n")
    
    # Analyser le fichier JSON
    duplicates, dossiers_by_numero = find_duplicates_json()
    
    # Afficher les doublons
    display_duplicates(duplicates, dossiers_by_numero)
    
    # Sauvegarder le rapport
    if duplicates:
        save_duplicates_report(duplicates, dossiers_by_numero)
        
        # Proposer de nettoyer
        print("\n" + "="*60)
        response = input("Voulez-vous créer un fichier sans doublons ? (o/n): ")
        if response.lower() == 'o':
            remove_duplicates_keep_first()
