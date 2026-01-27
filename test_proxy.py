import requests
from datetime import datetime
import time
import urllib3

# Désactiver les avertissements SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration du proxy - Proxy-Cheap Mobile
url = 'https://ipv4.icanhazip.com'
proxy = 'proxy-us.proxy-cheap.com:5959'
proxy_auth = 'pcvqgio5qO:PC_1YnrPLlVpSKFeSeus'
proxies = {
   'http': f'http://{proxy_auth}@{proxy}',
   'https': f'http://{proxy_auth}@{proxy}'
}

# Headers pour éviter les blocages
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

# Liste des sites à tester
test_sites = [
    ('https://geo.brdtest.com/welcome.txt?product=mobile&method=native', 'Bright Data Test'),
    ('https://ipv4.icanhazip.com', 'IP Check'),
    ('https://www.google.com', 'Google'),
    ('https://www.wikipedia.org', 'Wikipedia'),
    ('https://httpbin.org/ip', 'HTTPBin IP'),
    ('https://api.ipify.org?format=json', 'IPify API'),
    ('https://demarche.numerique.gouv.fr/users/sign_in', 'Démarche Simplifiée (gouv.fr)'),
]

print("=" * 60)
print(f"Test du proxy - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print(f"Proxy: {proxy}")
print(f"Auth: {proxy_auth.split(':')[0]}...")
print(f"⏱️  Timeout configuré: 30 secondes")
print("=" * 60)

# Test de chaque site
success_count = 0
total_time = 0

for url, name in test_sites:
    print(f"\n🔍 Test: {name}")
    print(f"   URL: {url}")
    
    start_time = time.time()
    
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=30, verify=False)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"   ✅ Succès (Status: {response.status_code})")
                print(f"   ⏱️  Temps de réponse: {elapsed:.2f}s")
                success_count += 1
                total_time += elapsed
                
                # Afficher la réponse (limitée à 200 caractères)
                content = response.text.strip()
                if len(content) > 200:
                    print(f"   📄 Réponse: {content[:200]}...")
                else:
                    print(f"   📄 Réponse: {content}")
                break
            else:
                elapsed = time.time() - start_time
                print(f"   ⚠️  Status Code: {response.status_code}")
                print(f"   ⏱️  Temps de réponse: {elapsed:.2f}s")
                print(f"   📄 Réponse: {response.text[:200]}")
                retries += 1
        except requests.exceptions.ProxyError as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Erreur Proxy après {elapsed:.2f}s")
            print(f"   📄 Détail: {str(e)[:150]}")
            retries += 1
        except requests.exceptions.Timeout as e:
            elapsed = time.time() - start_time
            print(f"   ⏱️  Timeout après {elapsed:.2f}s (> 30 secondes)")
            retries += 1
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Erreur de connexion après {elapsed:.2f}s")
            print(f"   📄 Détail: {str(e)[:150]}")
            retries += 1
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Erreur après {elapsed:.2f}s: {type(e).__name__}")
            print(f"   📄 Détail: {str(e)[:150]}")
            retries += 1
    else:
        print(f"   ❌ Échec après {max_retries} tentatives")

print("\n" + "=" * 60)
print("📊 RÉSUMÉ")
print("=" * 60)
print(f"Sites testés: {len(test_sites)}")
print(f"Succès: {success_count}")
print(f"Échecs: {len(test_sites) - success_count}")
if success_count > 0:
    avg_time = total_time / success_count
    print(f"Temps moyen de réponse: {avg_time:.2f}s")
    if avg_time > 5:
        print(f"⚠️  PROXY TRÈS LENT (> 5s en moyenne)")
    elif avg_time > 2:
        print(f"⚠️  Proxy lent (> 2s en moyenne)")
    else:
        print(f"✅ Vitesse acceptable")
print("=" * 60)