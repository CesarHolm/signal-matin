# Installer le journal sur le PC Windows

Durée : environ 20 minutes, une seule fois. Toutes les commandes se tapent dans
**PowerShell**, ouvert dans le dossier du projet.

## 1. Installer les outils (une fois)

1. **Python 3.12** : https://www.python.org/downloads/ → à la première fenêtre,
   cocher **« Add python.exe to PATH »**, puis « Install Now ».
2. **Git** : https://git-scm.com/download/win → installer avec les options par défaut.

Vérifier dans PowerShell :

```powershell
python --version
git --version
```

## 2. Récupérer le projet

```powershell
cd $HOME\Documents
git clone https://github.com/CesarHolm/signal-matin.git
cd signal-matin
git checkout cesar/personnalisation
```

## 3. Installer le journal

```powershell
python scripts\setup.py --yes --skip-preview
```

Le script crée l'environnement, installe les dépendances et le navigateur qui
fabrique les PDF, puis crée deux fichiers locaux (jamais publiés sur GitHub) :
`config.yaml` (sources, imprimante) et `.env` (clé API).

## 4. Ajouter la clé API

```powershell
notepad .env
```

Compléter la ligne `ANTHROPIC_API_KEY=` avec la clé créée sur
platform.claude.com (sans espace ni guillemets), enregistrer, fermer.
**Ne jamais coller cette clé dans une conversation.**

## 5. Indiquer l'imprimante

```powershell
Get-Printer | Select-Object Name
notepad config.yaml
```

Recopier le nom exact de la Brother dans `printing: printer: "…"`.

## 6. Premier essai

```powershell
.\.venv\Scripts\python.exe main.py journal --essai --direct
```

`--direct` fait les appels IA immédiatement (quelques minutes) au lieu du traitement de nuit.

Le PDF est créé dans `output\pdf\`. L'option `--essai` évite de mémoriser les
mots du jour et les solutions : on peut relancer autant de fois que nécessaire.
Sans `--essai`, l'édition est mémorisée (révisions et solutions du lendemain).

Pour tester l'impression recto verso :

```powershell
.\.venv\Scripts\python.exe main.py journal-imprimer
```

## 7. Programmer l'exécution automatique

```powershell
powershell -ExecutionPolicy Bypass -File scripts\installer_taches_journal.ps1
```

Deux tâches sont créées, du lundi au vendredi :

| Tâche | Heure | Rôle |
|---|---|---|
| Signal Matin - génération | 4 h 00 | sort le PC de veille, génère le journal (traitement de nuit) |
| Signal Matin - impression | 7 h 00 | imprime le PDF en recto verso |

Le soir, mettre le PC **en veille** (pas en arrêt complet) et le laisser branché.
Les journaux d'exécution sont dans `output\logs\`.
Pour supprimer les tâches : ajouter `-Desinstaller` à la commande ci-dessus.

## En cas de souci

- **Pas de journal à 7 h** : ouvrir le dernier fichier de `output\logs\`.
- **« ÉDITION DE SECOURS » en une** : l'IA n'a pas répondu (clé absente, crédits
  épuisés ou panne). Le journal sort quand même avec les titres et chapôs bruts.
- **Mettre à jour le projet** : `git pull` dans le dossier.
