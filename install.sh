#!/usr/bin/env bash
# =============================================================================
#  Brother Scan — installation automatique
#
#    curl -fsSL https://raw.githubusercontent.com/TheRemiDev/Brother-Scan/main/install.sh | sudo bash
#
#  Relancer ce script met simplement à jour / répare l'installation existante.
#  Variables facultatives : REPO_URL, BRANCH, DOMAIN, INSTALL_DIR
# =============================================================================
set -Eeuo pipefail

REPO_URL="${REPO_URL:-https://github.com/TheRemiDev/Brother-Scan.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/brother-scan}"
DATA_DIR="/var/lib/brother-scan"
CONF_DIR="/etc/brother-scan"
ENV_FILE="$CONF_DIR/brother-scan.env"
SERVICE="brother-scan"
APP_USER="brotherscan"

# ----------------------------------------------------------------- affichage
if [[ -t 1 ]]; then B=$'\e[1m'; D=$'\e[2m'; G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; N=$'\e[0m'; else B= D= G= R= Y= N=; fi
step() { echo; echo "${B}▸ $*${N}"; }
ok()   { echo "  ${G}✔${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; }
die()  { echo; echo "  ${R}✘ $*${N}" >&2; exit 1; }
trap 'die "Erreur ligne $LINENO. Rien n’a été cassé : corrigez puis relancez le script."' ERR

# Les questions passent par le terminal, même via « curl | bash »
TTY=/dev/tty
{ true <"$TTY"; } 2>/dev/null || TTY=/dev/null  # exécution sans terminal (mise à jour automatique)
ask() { # ask VAR "Question" "défaut"
  local __var=$1 __q=$2 __def=${3:-} __ans
  if [[ -n $__def ]]; then read -r -p "  $__q ${D}[$__def]${N} : " __ans <"$TTY" || true; else read -r -p "  $__q : " __ans <"$TTY" || true; fi
  printf -v "$__var" '%s' "${__ans:-$__def}"
}
ask_secret() { # ask_secret VAR "Question"
  local __var=$1 __q=$2 __ans
  read -r -s -p "  $__q : " __ans <"$TTY" || true; echo
  printf -v "$__var" '%s' "$__ans"
}
ask_yes() { # ask_yes "Question" o|n
  local __ans; read -r -p "  $1 ${D}[$( [[ $2 == o ]] && echo O/n || echo o/N )]${N} : " __ans <"$TTY" || true
  __ans=${__ans:-$2}; [[ ${__ans,,} == o* || ${__ans,,} == y* ]]
}
env_get() { [[ -f $ENV_FILE ]] && grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e "s/^'//" -e "s/'$//" -e "s/'\\\\''/'/g" || true; }
q() { printf "'%s'" "${1//\'/\'\\\'\'}"; } # valeur protégée pour le fichier .env

echo
echo "${B}  Scan.${N}  ${D}— installation pour Brother DCP-L3560CDW${N}"

[[ $EUID -eq 0 ]] || die "Lancez ce script en root : sudo bash install.sh"
command -v apt-get >/dev/null || die "Ce script prend en charge Debian / Ubuntu (apt)."

# ----------------------------------------------------------------- paquets
step "Paquets système"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip iproute2 tzdata >/dev/null
ok "git, python3, venv"

# ----------------------------------------------------------------- code
step "Récupération du programme"
if [[ -d $INSTALL_DIR/.git ]]; then
  git -C "$INSTALL_DIR" fetch -q origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout -q -B "$BRANCH" "origin/$BRANCH"
  git -C "$INSTALL_DIR" reset -q --hard "origin/$BRANCH"
  ok "mis à jour ($(git -C "$INSTALL_DIR" rev-parse --short HEAD))"
else
  git clone -q --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" \
    || die "Clonage impossible. Dépôt privé ? Relancez avec REPO_URL=https://<jeton>@github.com/TheRemiDev/Brother-Scan.git"
  ok "installé dans $INSTALL_DIR"
fi

id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin "$APP_USER"
install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"
install -d -m 750 -o root -g "$APP_USER" "$CONF_DIR"

step "Environnement Python"
[[ -x $INSTALL_DIR/venv/bin/python ]] || python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
ok "dépendances installées"

# ----------------------------------------------------------------- configuration
FIRST_INSTALL=1; [[ -f $ENV_FILE ]] && FIRST_INSTALL=0
RECONF=$FIRST_INSTALL
if [[ $FIRST_INSTALL == 0 ]]; then
  step "Configuration existante détectée"
  ask_yes "Modifier la configuration (domaine, e-mails) ?" n && RECONF=1
fi

DOMAIN="${DOMAIN:-$(env_get BS_DOMAIN)}"; DOMAIN="${DOMAIN:-scan.remividon.fr}"
PORT="$(env_get BS_PORT)"

if [[ $RECONF == 1 ]]; then
  step "Adresse du site"
  ask DOMAIN "Nom de domaine" "$DOMAIN"

  step "Boîte e-mail qui reçoit les numérisations"
  echo "  ${D}Identifiants de la boîte scan@… (chez votre hébergeur e-mail).${N}"
  IMAP_USER_DEF="$(env_get BS_IMAP_USER)"; ask IMAP_USER "Adresse e-mail" "${IMAP_USER_DEF:-scan@${DOMAIN#*.}}"
  MAIL_DOMAIN="${IMAP_USER#*@}"
  ask IMAP_HOST "Serveur IMAP" "$(env_get BS_IMAP_HOST || true)"
  [[ -z $IMAP_HOST ]] && IMAP_HOST="imap.$MAIL_DOMAIN" && echo "    → $IMAP_HOST"
  ask IMAP_PORT "Port IMAP (SSL)" "$(p=$(env_get BS_IMAP_PORT); echo "${p:-993}")"
  ask_secret IMAP_PASSWORD "Mot de passe (laisser vide pour conserver l’actuel)"
  [[ -z $IMAP_PASSWORD ]] && IMAP_PASSWORD="$(env_get BS_IMAP_PASSWORD)"
  [[ -n $IMAP_PASSWORD ]] || die "Mot de passe e-mail requis."

  echo "  ${D}Envoi (réexpédition des PDF).${N}"
  ask SMTP_HOST "Serveur SMTP" "$(h=$(env_get BS_SMTP_HOST); echo "${h:-${IMAP_HOST/imap/smtp}}")"
  ask SMTP_PORT "Port SMTP (465 = SSL, 587 = STARTTLS)" "$(p=$(env_get BS_SMTP_PORT); echo "${p:-465}")"
  SMTP_SECURITY=ssl; [[ $SMTP_PORT == 587 || $SMTP_PORT == 25 ]] && SMTP_SECURITY=starttls
  ask SMTP_FROM "Nom affiché à l’envoi" "$(f=$(env_get BS_SMTP_FROM); echo "${f:-Scan <$IMAP_USER>}")"

  ask ALLOWED "Expéditeurs autorisés (adresse de l’imprimante, vide = tous)" "$(env_get BS_ALLOWED_SENDERS)"
fi

# Port libre, uniquement sur 127.0.0.1 : aucun conflit avec les autres programmes du VPS
port_free() { ! ss -Hltn "( sport = :$1 )" | grep -q .; }
if [[ -z $PORT ]] || { ! port_free "$PORT" && ! systemctl is-active -q "$SERVICE"; }; then
  PORT=8710; while ! port_free "$PORT"; do PORT=$((PORT + 1)); done
fi

if [[ $RECONF == 1 ]]; then
  SECRET="$(env_get BS_SECRET_KEY)"; [[ -n $SECRET ]] || SECRET="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
  umask 027
  cat >"$ENV_FILE" <<EOF
# Configuration Brother Scan — modifiable avec : sudo brother-scan config
BS_DOMAIN=$(q "$DOMAIN")
BS_PORT=$(q "$PORT")
BS_PUBLIC_URL=$(q "https://$DOMAIN")
BS_DATA_DIR=$(q "$DATA_DIR")
BS_SECRET_KEY=$(q "$SECRET")
BS_SCAN_ADDRESS=$(q "$IMAP_USER")
BS_RETENTION_HOURS='24'
BS_POLL_SECONDS='20'

BS_IMAP_HOST=$(q "$IMAP_HOST")
BS_IMAP_PORT=$(q "$IMAP_PORT")
BS_IMAP_SECURITY='ssl'
BS_IMAP_USER=$(q "$IMAP_USER")
BS_IMAP_PASSWORD=$(q "$IMAP_PASSWORD")
BS_IMAP_FOLDER='INBOX'

BS_SMTP_HOST=$(q "$SMTP_HOST")
BS_SMTP_PORT=$(q "$SMTP_PORT")
BS_SMTP_SECURITY=$(q "$SMTP_SECURITY")
BS_SMTP_USER=$(q "$IMAP_USER")
BS_SMTP_PASSWORD=$(q "$IMAP_PASSWORD")
BS_SMTP_FROM=$(q "$SMTP_FROM")

BS_ALLOWED_SENDERS=$(q "$ALLOWED")
EOF
  umask 022
  chown root:"$APP_USER" "$ENV_FILE"; chmod 640 "$ENV_FILE"
  ok "configuration enregistrée"
else
  sed -i "s/^BS_PORT=.*/BS_PORT='$PORT'/" "$ENV_FILE"
fi

run_app() { # exécute une commande Python de l'appli avec la configuration
  (cd "$INSTALL_DIR" && runuser -u "$APP_USER" -- env BS_ENV_FILE="$ENV_FILE" "$INSTALL_DIR/venv/bin/python" -m brotherscan.cli "$@")
}

if [[ $RECONF == 1 ]]; then
  step "Test de la boîte e-mail"
  run_app check-mail || warn "Connexion e-mail en échec : vérifiez avec « sudo brother-scan config » (le site s'installe quand même)."
fi

# ----------------------------------------------------------------- code PIN
if ! run_app has-pin 2>/dev/null && [[ $TTY == /dev/null ]]; then
  warn "Aucun code PIN défini : lancez « sudo brother-scan pin »."
elif ! run_app has-pin 2>/dev/null; then
  step "Code PIN d’accès"
  echo "  ${D}Aucune contrainte : chiffres, lettres, phrase… Modifiable ensuite dans le site.${N}"
  while :; do
    ask_secret PIN1 "Choisissez votre code"
    ask_secret PIN2 "Confirmez le code"
    [[ -n $PIN1 && $PIN1 == "$PIN2" ]] && break
    warn "Codes vides ou différents, recommencez."
  done
  printf '%s\n' "$PIN1" | run_app set-pin >/dev/null
  unset PIN1 PIN2
  ok "code PIN enregistré"
fi

# ----------------------------------------------------------------- service
step "Service système"
cat >/etc/systemd/system/$SERVICE.service <<EOF
[Unit]
Description=Brother Scan (https://$DOMAIN)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
Environment=BS_ENV_FILE=$ENV_FILE
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn brotherscan.main:app --host 127.0.0.1 --port $PORT --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-server-header --log-level warning
Restart=always
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
MemoryMax=600M

[Install]
WantedBy=multi-user.target
EOF

# Mise à jour automatique chaque nuit
cat >/etc/systemd/system/$SERVICE-update.service <<EOF
[Unit]
Description=Mise à jour automatique de Brother Scan
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/brother-scan update --quiet
EOF
cat >/etc/systemd/system/$SERVICE-update.timer <<EOF
[Unit]
Description=Mise à jour quotidienne de Brother Scan

[Timer]
OnCalendar=*-*-* 04:00
RandomizedDelaySec=45min
Persistent=true

[Install]
WantedBy=timers.target
EOF

ln -sf "$INSTALL_DIR/scripts/brother-scan" /usr/local/bin/brother-scan
chmod +x "$INSTALL_DIR/scripts/brother-scan" "$INSTALL_DIR/install.sh"
systemctl daemon-reload
systemctl enable -q --now $SERVICE-update.timer
systemctl enable -q $SERVICE
systemctl restart $SERVICE
for _ in $(seq 1 30); do curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && break; sleep 1; done
curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null || die "Le service ne démarre pas : journalctl -u $SERVICE -n 50"
ok "en ligne sur 127.0.0.1:$PORT (invisible depuis l’extérieur)"

# ----------------------------------------------------------------- domaine + SSL
step "Domaine et certificat SSL ($DOMAIN)"
SERVER_IP="$(curl -4 -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
# Résolution publique (DNS-over-HTTPS) : /etc/hosts associe souvent le nom du VPS à 127.0.1.1
public_dns() {
  curl -fsS --max-time 6 -H 'accept: application/dns-json' "https://cloudflare-dns.com/dns-query?name=$1&type=A" 2>/dev/null \
    | grep -oE '"data":"[0-9.]+"' | head -1 | cut -d'"' -f4 || true
}
DNS_IP="$(public_dns "$DOMAIN")"
[[ -n $DNS_IP ]] || DNS_IP="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '$1 !~ /^127\./ {print $1; exit}' || true)"
if [[ -z $DNS_IP ]]; then
  warn "$DOMAIN ne pointe nulle part. Créez un enregistrement DNS A vers ${SERVER_IP:-l’IP du VPS} puis relancez le script."
elif [[ -n $SERVER_IP && $DNS_IP != "$SERVER_IP" ]]; then
  warn "$DOMAIN pointe vers $DNS_IP alors que ce serveur est $SERVER_IP (normal si vous passez par un proxy type Cloudflare)."
else
  ok "DNS correct ($DNS_IP)"
fi
LE_EMAIL="$(env_get BS_SCAN_ADDRESS)"

listener() { ss -Hltnp "( sport = :$1 )" 2>/dev/null | grep -oE 'users:\(\("[^"]+"' | head -1 | cut -d'"' -f2 || true; }
WEB="$(listener 80)"; [[ -z $WEB ]] && WEB="$(listener 443)"

if [[ -z $WEB ]]; then
  apt-get install -y -qq nginx >/dev/null; WEB=nginx
  ok "nginx installé"
fi

case "$WEB" in
  nginx)
    apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
    if [[ -d /etc/nginx/sites-available ]]; then
      VHOST=/etc/nginx/sites-available/$SERVICE.conf; ln -sf "$VHOST" /etc/nginx/sites-enabled/$SERVICE.conf
    else
      VHOST=/etc/nginx/conf.d/$SERVICE.conf
    fi
    # Ne réécrit le vhost que s'il n'a pas encore été équipé du SSL par certbot
    if [[ ! -f $VHOST ]] || ! grep -q "managed by Certbot" "$VHOST"; then
      cat >"$VHOST" <<EOF
# Brother Scan — généré par install.sh
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    client_max_body_size 64m;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
    else
      sed -i -E "s#proxy_pass http://127\.0\.0\.1:[0-9]+;#proxy_pass http://127.0.0.1:$PORT;#" "$VHOST"
    fi
    nginx -t -q || die "Configuration nginx invalide (nginx -t pour le détail)."
    systemctl enable -q nginx; systemctl reload-or-restart nginx
    ok "nginx configuré"
    if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$LE_EMAIL" --redirect --keep-until-expiring -q; then
      ok "certificat SSL actif (renouvellement automatique)"
    else
      warn "Certificat non obtenu (DNS pas encore propagé ?). Relancez simplement : sudo brother-scan ssl"
    fi
    ;;
  apache2|httpd)
    apt-get install -y -qq certbot python3-certbot-apache >/dev/null
    a2enmod -q proxy proxy_http headers >/dev/null
    cat >/etc/apache2/sites-available/$SERVICE.conf <<EOF
<VirtualHost *:80>
    ServerName $DOMAIN
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:$PORT/
    ProxyPassReverse / http://127.0.0.1:$PORT/
    RequestHeader set X-Forwarded-Proto "expr=%{REQUEST_SCHEME}"
</VirtualHost>
EOF
    a2ensite -q $SERVICE >/dev/null; systemctl reload-or-restart apache2
    certbot --apache -d "$DOMAIN" --non-interactive --agree-tos -m "$LE_EMAIL" --redirect --keep-until-expiring -q \
      && ok "Apache + SSL configurés" || warn "Certificat non obtenu. Relancez : sudo brother-scan ssl"
    ;;
  caddy)
    CADDYFILE=/etc/caddy/Caddyfile
    sed -i "/# >>> brother-scan/,/# <<< brother-scan/d" "$CADDYFILE"
    printf '\n# >>> brother-scan\n%s {\n\treverse_proxy 127.0.0.1:%s\n}\n# <<< brother-scan\n' "$DOMAIN" "$PORT" >>"$CADDYFILE"
    systemctl reload caddy && ok "Caddy configuré (SSL automatique)"
    ;;
  *)
    warn "Les ports 80/443 sont utilisés par « $WEB » (Traefik, Docker, panel…)."
    warn "Ajoutez dans ce proxy une route : https://$DOMAIN  →  http://127.0.0.1:$PORT"
    ;;
esac

# ----------------------------------------------------------------- fin
echo
echo "  ${G}${B}Installation terminée.${N}"
echo
echo "  Site            ${B}https://$DOMAIN${N}"
echo "  Imprimante      envoyer les numérisations (format PDF) à ${B}$(env_get BS_SCAN_ADDRESS)${N}"
echo
echo "  ${D}Commandes utiles :${N}"
echo "    sudo brother-scan update    mettre à jour (aussi automatique chaque nuit)"
echo "    sudo brother-scan pin       changer le code PIN"
echo "    sudo brother-scan config    modifier domaine / e-mails"
echo "    sudo brother-scan status    état du service"
echo
