# Zelda — CAAL local sur CachyOS

Profil personnel de CAAL avec Qwen3-TTS, Bonsai 2 via Vulkan et OpenWakeWord Hey Zelda. Les paramètres privés sont conservés dans .local/ et ne sont pas versionnés.

## Configuration préparée sur cette VM

- Dépôt : /chemin/vers/caal-zelda
- VM : IP_DE_LA_VM ; Home Assistant : http://IP_HOME_ASSISTANT:8123
- LLM : Bonsai 2 27B PTQ1_0, moteur PrismML prism-b10709-9a9394a, Vulkan, contexte 4096, une requête parallèle, raisonnement désactivé.
- TTS : llama.cpp existant, Qwen3-TTS Base Q4_K_M, projecteur Q8_0, référence WAV du profil Zelda, contexte 2048.
- STT : Whisper small multilingue, local sur CPU via Speaches.
- Wake word : modèle communautaire Hey Zelda, OpenWakeWord côté serveur.
- .local/zelda.env et .local/settings.json contiennent les chemins et clés générées. Ces fichiers sont exclus de Git et du contexte Docker.

## Créer le profil sur une nouvelle installation

Télécharger les modèles Bonsai avec `bash scripts/download-bonsai.sh`, puis :

```bash
python3 scripts/prepare-zelda.py \
  --host-ip IP_DE_LA_VM \
  --speaker /chemin/reference.wav \
  --tts-bin /chemin/llama.cpp/build/bin/llama-tts \
  --tts-model /chemin/Qwen3-TTS-12Hz-1.7B-Base-Q4_K_M.gguf \
  --tts-mmproj /chemin/mmproj-Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf \
  --bonsai-server .local/bonsai/bin/llama-prism-b10709-9a9394a/llama-server \
  --bonsai-model .local/bonsai/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf \
  --ha-url http://IP_HOME_ASSISTANT:8123
```

Ce script ne remplace jamais une configuration existante. Modifier `.local/zelda.env`
pour changer les chemins ou l'adresse IP. La langue du service vocal est `fr` par
défaut ; la changer via `QWEN_TTS_LANGUAGE` et redémarrer le pont si nécessaire.

## 1. Démarrer Bonsai dans un terminal

```bash
cd /chemin/vers/caal-zelda
bash scripts/download-bonsai.sh
bash scripts/run-bonsai.sh
```

Le téléchargement est déjà terminé ; le premier script vérifie aussi le SHA-256. Confirmer dans les logs la Radeon/Vulkan et le transfert des couches. Bonsai **2** exige le fork PrismML : ne pas remplacer son moteur par le llama.cpp utilisé pour Qwen3-TTS. Les kernels PTQ1_0 sont implémentés pour Vulkan dans cette version, contrairement à PQ2_0.

## 2. Démarrer la voix dans un autre terminal

```bash
cd /chemin/vers/caal-zelda
bash scripts/run-qwen-tts.sh
```

Le pont expose /v1/audio/speech, accepte uniquement la voix zelda et renvoie du WAV mono 24 kHz. Il recharge llama-tts à chaque requête : cette première version n'est pas du streaming audio natif et ajoute une latence de chargement. Une seule synthèse est acceptée à la fois ; une requête concurrente reçoit HTTP 429. Pour commencer, utiliser des phrases courtes et mesurer la VRAM avec les deux moteurs actifs.

## 3. Installer puis démarrer Docker

Docker n'était pas disponible pendant la préparation. À exécuter dans le terminal de la VM :

```bash
sudo pacman -Syu --needed docker docker-compose
sudo systemctl enable --now docker
cd /chemin/vers/caal-zelda
sudo docker compose --env-file .local/zelda.env -f docker-compose.zelda.yaml config --quiet
sudo docker compose --env-file .local/zelda.env -f docker-compose.zelda.yaml up -d --build
```

Ouvrir https://IP_DE_LA_VM:3443, accepter le certificat local et autoriser le microphone. Les premiers démarrages téléchargent les modèles STT/VAD. La pile utilise des noms et volumes zelda-* ; ses ports sont ceux de CAAL, donc éviter une autre pile CAAL sur les mêmes ports.

Les moteurs natifs écoutent sur l'IP LAN de la VM afin d'être accessibles depuis les conteneurs. Leurs API utilisent les clés générées dans .local/zelda.env. Aucun accès cloud n'est nécessaire pour l'inférence après les téléchargements ; la recherche web de CAAL reste une fonction réseau optionnelle.

## 4. Connecter Home Assistant

Dans Home Assistant, installer l'intégration MCP Server et exposer à Assist les entités voulues. Dans les paramètres CAAL, activer Home Assistant, garder l'URL préparée et saisir localement un jeton longue durée. Ne pas publier ce jeton dans Git. L'intégration reste désactivée tant que le jeton n'est pas renseigné.

Tester d'abord une lecture d'état, puis une commande simple. Le bon fonctionnement des appels d'outils avec Bonsai reste à valider ; une réponse vocale seule ne suffit pas à prouver que l'action a été exécutée.

## 5. Tester Hey Zelda

Le fichier models/hey_zelda.onnx provient de la collection communautaire recommandée par OpenWakeWord. Sa licence et sa provenance sont dans models/hey_zelda.LICENSE et models/hey_zelda.md. Aucun modèle n'a été entraîné pendant cette session.

Le profil active ce détecteur à un seuil de 0,5. La session du navigateur doit rester connectée. Tester plusieurs distances et des phrases sans Hey Zelda, puis ajuster le seuil si nécessaire. La robustesse au microphone réel et à l'accent français n'est pas encore mesurée.

## Validation effectuée et limites

- Six tests Python du pont TTS passent : authentification, requêtes invalides, WAV, concurrence, expiration, texte transmis comme données.
- TypeScript sans émission, compilation syntaxique Python et syntaxe des scripts shell : passent.
- ONNX Checker et inférence CPU sur des embeddings nuls : passent pour Hey Zelda.
- La configuration des cinq services passe docker compose config --quiet. Les conteneurs restent à construire et tester.
- Le binaire PrismML démarre ; le GGUF a été téléchargé et son SHA-256 vérifié. Réponse française et appel d’outil fictif validés via HTTP ; aucune commande HA exécutée.
- Home Assistant répond HTTP 200.
- Test de coexistence : Bonsai chargé sur la VM et Qwen3-TTS ont produit 3,76 s de WAV en 2,96 s, chargement et HTTP inclus. Restent à tester : image Docker, conversation complète, contrôle HA et détection sur microphone.



## Tests de développement

```bash
python3 -m unittest discover -s tests -v
cd frontend
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
```

Sources :
- https://github.com/PrismML-Eng/Bonsai-demo/blob/main/BACKEND-SUPPORT.md
- https://github.com/fwartner/home-assistant-wakewords-collection/tree/8bcd2f20bb7b76c351b2eff871fa1ce873fe9be2/en/hey_zelda
- https://github.com/CoreWorxLab/CAAL/blob/main/docs/HOME-ASSISTANT.md

## Diagnostic Docker sur CachyOS

Si Docker échoue avec une erreur de chaîne NAT/PREROUTING, vérifier que
`/usr/lib/modules/$(uname -r)` existe. Après une mise à jour du noyau, un
redémarrage est nécessaire si les modules du noyau en cours ont été supprimés.
Sur la VM testée, le noyau actif était 7.1.8-1-cachyos alors que seuls les
modules 7.2.6-1-cachyos et 6.18.52-1-cachyos-lts étaient installés.

Après redémarrage, relancer les deux moteurs dans leurs terminaux puis :

```bash
systemctl is-active docker
sudo docker compose --env-file .local/zelda.env -f docker-compose.zelda.yaml up -d --build
```
