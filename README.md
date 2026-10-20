# Scan.

Interface web privée pour la **Brother DCP-L3560CDW** : l'imprimante envoie ses numérisations par e-mail à
`scan@remividon.fr`, et le site **https://scan.remividon.fr** (protégé par un code PIN) permet de :

1. **Télécharger** les 10 derniers documents (heure, nombre de pages, aperçu de chaque page) ;
2. **Fusionner** plusieurs numérisations en un seul PDF, dans l'ordre choisi ;
3. **Réexpédier** un PDF par e-mail (adresse saisie ou contacts favoris en un geste) ;
4. **Ranger dans Google Drive** en deux clics, dans des dossiers choisis à l'avance (plusieurs comptes possibles).

Chaque document est **supprimé définitivement au bout de 24 h**, sur le serveur _et_ dans la boîte mail
(l'e-mail est même effacé dès que le PDF est récupéré ; les dossiers « Envoyés » et « Corbeille » sont purgés à 24 h).

---

## Installation (une seule commande)

Prérequis : un VPS Debian / Ubuntu, et un enregistrement DNS **A** `scan.remividon.fr` → IP du VPS.

```bash
curl -fsSL https://raw.githubusercontent.com/TheRemiDev/Brother-Scan/main/install.sh | sudo bash
```

> Dépôt privé ? Utilisez un jeton GitHub (lecture seule) :
> `curl -fsSL -H "Authorization: token <JETON>" https://raw.githubusercontent.com/TheRemiDev/Brother-Scan/main/install.sh | sudo REPO_URL=https://<JETON>@github.com/TheRemiDev/Brother-Scan.git bash`

Le script pose quelques questions (domaine, identifiants de la boîte `scan@`, **code PIN**) puis s'occupe de tout :

- service systemd isolé (utilisateur dédié, accès disque limité) ;
- **aucun conflit de ports** : l'application écoute uniquement sur `127.0.0.1`, sur le premier port libre à partir de 8710 ;
- **domaine + SSL** : ajoute un site au serveur web déjà présent (nginx, Apache ou Caddy), ou installe nginx s'il n'y en a pas,
  puis obtient le certificat Let's Encrypt (renouvelé automatiquement). Si un autre proxy occupe les ports 80/443
  (Traefik, Docker…), le script indique la route à ajouter ;
- **mises à jour automatiques** chaque nuit (avec retour arrière si la nouvelle version ne démarre pas).

Relancer le script est sans risque : il met à jour et répare l'installation en conservant la configuration.

## Mise à jour

Rien à faire : la mise à jour se fait seule chaque nuit (04 h). Pour l'appliquer tout de suite :

```bash
sudo brother-scan update
```

## Commandes

| Commande | Rôle |
| --- | --- |
| `sudo brother-scan update` | Mettre à jour maintenant |
| `sudo brother-scan pin` | Changer le code PIN (aussi possible dans le site : ⚙ Réglages) |
| `sudo brother-scan config` | Modifier les réglages e-mail |
| `sudo brother-scan check` | Tester la connexion à la boîte e-mail |
| `sudo brother-scan ssl` | Redemander le certificat SSL |
| `brother-scan status` | État du service |
| `brother-scan logs` | Journal en direct |
| `sudo brother-scan uninstall` | Tout supprimer |

## Réglage de l'imprimante

Dans l'interface web de la Brother (`https://<ip-de-l-imprimante>` → **Réseau › Protocole › SMTP**) :

- Serveur SMTP : celui de votre hébergeur e-mail, port 465 (SSL) ou 587 (STARTTLS) ;
- Adresse de l'appareil + authentification SMTP : une boîte d'envoi (ou `scan@remividon.fr` elle-même) ;
- **Numériser › Numérisation vers serveur e-mail** : format **PDF**, destinataire `scan@remividon.fr`
  (enregistrez-le dans un raccourci pour l'avoir en un appui).

Conseil : à l'installation, indiquez l'adresse d'envoi de l'imprimante comme « expéditeur autorisé » ;
les autres e-mails sont alors ignorés (et effacés au bout de 24 h).

## Google Drive

Tout se configure dans le site : **⚙ Réglages › Google Drive**. Une seule préparation est nécessaire chez Google
(environ 5 minutes, une fois pour toutes) :

1. Sur [console.cloud.google.com](https://console.cloud.google.com/apis/library/drive.googleapis.com), créez un projet
   et activez **Google Drive API**.
2. **Écran de consentement OAuth** : type « Externe », puis **Publier l'application**
   (en mode « Test », Google coupe l'accès au bout de 7 jours).
3. **Identifiants › Créer des identifiants › ID client OAuth › Application Web**, avec comme URI de redirection
   autorisée `https://scan.remividon.fr/api/drive/callback` (affichée et copiable dans les réglages).
4. Collez l'ID client et le code secret dans les réglages, puis **Ajouter un dossier Drive** : connectez le compte,
   choisissez (ou créez) le dossier. Google affichera « application non validée » : *Paramètres avancés › Accéder à…*,
   c'est normal pour une application personnelle.

Ensuite, sur chaque document : **Drive › choisir le dossier** — c'est envoyé. Le nom du fichier est modifiable avant l'envoi.
On peut ajouter autant de dossiers que voulu, sur un ou plusieurs comptes Google.

> Les copies envoyées dans Google Drive sont **conservées** (elles ne sont pas soumises à la suppression des 24 h).

## Sécurité

- Code PIN de longueur libre (chiffres, lettres, phrase…), stocké haché (scrypt) ; blocage progressif après 5 erreurs.
- Session de 12 h en cookie signé `HttpOnly` / `Secure` / `SameSite=Strict` ; changer le PIN déconnecte toutes les sessions.
- Google Drive : seuls les jetons de connexion sont stockés (jamais renvoyés au navigateur) ; retirer le dernier
  dossier d'un compte révoque aussi l'accès chez Google.
- Documents dans `/var/lib/brother-scan` (accès réservé au service), configuration dans `/etc/brother-scan`.

## Développement

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
BS_DATA_DIR=./data venv/bin/python -m brotherscan.cli set-pin
BS_DATA_DIR=./data venv/bin/uvicorn brotherscan.main:app --reload --port 8710
python3 tests/test_core.py
```
