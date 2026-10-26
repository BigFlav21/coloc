# Coloc

Application web pour organiser une colocation : agenda commun, menus de la semaine, liste de courses partagée et idées d'activités. Les colocataires se connectent avec leur prénom et un PIN.

## Fonctionnalités

- **Agenda** : calendrier mensuel, évènements (soirée, dîner, invité, absence) avec réponse « Je viens / Non ».
- **Menus** : qui cuisine chaque soir de la semaine, et qui mange.
- **Courses** : liste partagée par rayon, avec cases à cocher.
- **Idées** : propositions d'activités avec votes.
- **Comptes** : PIN temporaire à changer à la première connexion, blocage après 5 échecs.

## Stack

FastAPI, Jinja2, HTMX, SQLite (SQLModel), pytest, Docker.

## Lancer en local

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Linux/macOS : .venv/bin/python
.venv/Scripts/python -m pytest
```

Créer les colocataires (un PIN temporaire est généré et affiché, ou `--pin 1234`) :

```bash
.venv/Scripts/python -m app.seed add Alex
.venv/Scripts/python -m app.seed list
.venv/Scripts/python -m app.seed reset Alex     # nouveau PIN temporaire
```

Démarrer l'application :

```bash
.venv/Scripts/python -m uvicorn app.main:get_app --factory --reload --port 8321
```

La base locale est `data/coloc.db`. La maquette statique de référence est dans `mockup/`.

## Configuration

Variables d'environnement (voir `.env.example`) :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `COLOC_SECRET_KEY` | clé de signature des sessions (obligatoire en production) | valeur de dev |
| `COLOC_COOKIE_SECURE` | `true` quand le site est servi en HTTPS | `false` |
| `COLOC_PORT` | port publié sur `127.0.0.1` par docker compose | `8321` |
| `COLOC_DATABASE_URL` | URL de la base | `sqlite:///./data/coloc.db` |
| `COLOC_TIMEZONE` | fuseau horaire | `Europe/Paris` |

## Déploiement avec Docker

Le projet compose `coloc` est autonome : conteneur `coloc-app`, réseau `coloc_net`, volume `coloc_data`, mémoire et CPU limités, logs bornés. Le port n'est publié que sur `127.0.0.1`, à placer derrière un reverse proxy HTTPS.

```bash
cp .env.example .env        # puis renseigner COLOC_SECRET_KEY
./scripts/up.sh
./scripts/seed.sh add Alex
```

| Script | Action |
| --- | --- |
| `scripts/up.sh` | construit et démarre |
| `scripts/down.sh` | arrête et supprime le conteneur (la base est conservée) |
| `scripts/restart.sh` | redémarre l'application |
| `scripts/logs.sh` | suit les logs |
| `scripts/status.sh` | état et santé |
| `scripts/update.sh` | `git pull`, rebuild et relance |
| `scripts/seed.sh` | gère les colocataires dans le conteneur (`add`, `reset`, `list`) |

Le reverse proxy doit transmettre l'en-tête `Host` d'origine, sinon la vérification d'origine refuse les écritures.

Caddy :

```
coloc.exemple.fr {
    reverse_proxy 127.0.0.1:8321
}
```

nginx :

```
location / {
    proxy_pass http://127.0.0.1:8321;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Sécurité

PIN hashés (scrypt), blocage de 15 minutes après 5 échecs par prénom, cookie de session signé (HttpOnly, SameSite=Lax, Secure en HTTPS), rejet des requêtes d'écriture venant d'une autre origine, conteneur non-root en lecture seule sans capabilities.
