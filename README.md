# EasySolar 1600 — Assistant hors ligne

Posez vos questions sur l'onduleur-chargeur **Victron EasySolar 1600** en français : l'assistant cherche la réponse dans le manuel et vous indique la page. Il fonctionne **entièrement sur votre ordinateur, sans connexion Internet**.

> Les réponses viennent d'une petite intelligence artificielle : en cas de doute, vérifiez toujours dans le manuel la page indiquée.

📄 [Manuel EasySolar 1600 en français (PDF)](Manuel-EasySolar-FR.pdf) — les pages citées par l'assistant sont les numéros imprimés en bas de page.

---

## Avant de commencer

| | Windows | Mac |
|---|---|---|
| Système | Windows 10 ou 11 (64 bits) | macOS 13 ou plus récent |
| Ordinateur | processeur Intel depuis 2013 ou AMD depuis 2015 | puce Apple (M1, M2, M3, M4...) |
| Navigateur | Microsoft Edge (déjà installé sur Windows) | rien à installer |
| Mémoire | 8 Go recommandés | 8 Go recommandés |
| Place libre | 2,5 Go (1,2 Go après installation) | 2,5 Go (1,2 Go après installation) |

Le dépôt est public : aucun compte GitHub n'est nécessaire pour télécharger l'application.

---

## Installation sur Windows

1. **Télécharger** — Ouvrez la [page de téléchargement](https://github.com/Yann0s/easysolar-bot/releases/latest) et cliquez sur **EasySolar-Windows.zip** (1,1 Go, quelques minutes).
2. **Extraire** — Dans le dossier *Téléchargements*, faites un clic droit sur **EasySolar-Windows.zip** puis **Extraire tout...** → **Extraire**. Un dossier **EasySolar** apparaît.
   ⚠️ Ne lancez pas l'application depuis l'intérieur du zip : elle ne trouverait pas ses fichiers.
3. **Ranger** *(facultatif)* — Déplacez le dossier **EasySolar** où vous voulez, par exemple dans *Documents*.
4. **Lancer** — Ouvrez le dossier **EasySolar** et double-cliquez sur **EasySolar.exe**.
5. **Premier lancement uniquement** — Windows peut afficher « *Windows a protégé votre ordinateur* ». Cliquez sur **Informations complémentaires**, puis sur **Exécuter quand même**. (L'application n'est pas signée par un éditeur payant, d'où cet avertissement.)
6. Une fenêtre **EasySolar 1600** s'ouvre. Patientez pendant le chargement (jusqu'à une minute), puis posez votre question.

💡 **Raccourci sur le bureau** : clic droit sur **EasySolar.exe** → **Afficher d'autres options** (Windows 11) → **Envoyer vers** → **Bureau (créer un raccourci)**.

---

## Installation sur Mac

1. **Télécharger** — Ouvrez la [page de téléchargement](https://github.com/Yann0s/easysolar-bot/releases/latest) et cliquez sur **EasySolar-Mac.zip** (1,1 Go, quelques minutes).
2. **Décompresser** — Dans le dossier *Téléchargements*, double-cliquez sur **EasySolar-Mac.zip** : l'application **EasySolar** apparaît.
3. **Ranger** — Faites glisser **EasySolar** dans le dossier **Applications**.
4. **Lancer** — Double-cliquez sur **EasySolar** dans *Applications*.
5. **Premier lancement uniquement** — macOS affiche « *Apple n'a pas pu vérifier...* ». Cliquez sur **Terminé**, puis :
   - ouvrez **Réglages Système** → **Confidentialité et sécurité** ;
   - descendez jusqu'au message « *EasySolar a été bloqué...* » et cliquez sur **Ouvrir quand même** ;
   - saisissez votre mot de passe, puis cliquez sur **Ouvrir**.

   (L'application n'est pas certifiée par Apple, d'où cet avertissement. Les lancements suivants se font normalement.)
6. Une fenêtre **EasySolar** s'ouvre. Patientez pendant le chargement (jusqu'à une minute), puis posez votre question.

💡 Pour la garder dans le Dock : pendant qu'elle est ouverte, clic droit sur son icône → **Options** → **Garder dans le Dock**.

---

## Utilisation

- Tapez votre question dans la zone en bas, par exemple « *Que signifie la LED Alarm qui clignote ?* », puis **Entrée**.
- La réponse indique la **page du manuel** d'où elle vient.
- Pour fermer : bouton **Quitter** en haut à droite, ou fermez simplement la fenêtre.

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| Windows : la fenêtre affiche « Ce site est inaccessible » | L'application a sans doute été lancée depuis le zip : faites **Extraire tout** (étape 2) et lancez **EasySolar.exe** depuis le dossier extrait. Sinon, fermez la fenêtre et relancez. |
| Windows : l'antivirus bloque EasySolar.exe | L'application n'est pas signée : autorisez-la dans votre antivirus. |
| Mac : « EasySolar est endommagé » | Le zip est incomplet : supprimez-le et téléchargez-le à nouveau. |
| Le chargement est très long | Fermez les autres programmes : l'assistant a besoin d'environ 2 Go de mémoire. |

---

## Désinstaller

- **Windows** : supprimez le dossier **EasySolar**, puis le dossier `%LOCALAPPDATA%\EasySolar` (à coller dans la barre d'adresse de l'Explorateur).
- **Mac** : mettez **EasySolar** (dans *Applications*) à la corbeille.

---

## Pour les développeurs

Compilation, modèles, tests et état du projet : voir [HANDOFF.md](HANDOFF.md).
