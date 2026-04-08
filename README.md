# Plum’ID — API

API REST pour Plum’ID (reconnaissance d’images de plumes).  
Stack : **FastAPI**, **SQLAlchemy**, **MySQL** (ou SQLite en dev), **JWT** (comptes utilisateurs), **API Key** (service-to-service), **SMTP** (vérification d’email).

* **Docs interactives** : `http://localhost:8000/docs` (Swagger)
* **Schéma OpenAPI** : `http://localhost:8000/openapi.json`

---

## Sommaire

1. [Prérequis](#prérequis)  
2. [Configuration (.env)](#configuration-env)  
3. [Lancement avec Docker Compose](#lancement-avec-docker-compose)  
4. [Authentification](#authentification)  
   * [API Key](#1-api-key-service-to-service)  
   * [JWT + Vérification d'email](#2-jwt-comptes-utilisateurs--vérification-demail)  
5. [Endpoints](#endpoints)  
   * [Health](#health)  
   * [Species](#species)  
   * [Feathers](#feathers)  
   * [Pictures](#pictures)  
   * [Auth Utilisateurs](#auth-utilisateurs)  
6. [Modèles de données](#modèles-de-données)  
7. [Conventions & Erreurs](#conventions--erreurs)  
8. [Exemples `curl`](#exemples-curl)

---

## Prérequis

* **Docker** et **Docker Compose** (v2+)
* Un fichier `.env` correctement rempli (voir section suivante)

> Aucune installation locale de Python, MySQL ou uvicorn n'est nécessaire.

---

## Configuration (.env)

Créer un fichier `.env` à la racine du projet.

### Logs & API

```env
# --- LOGGING
LOG_LEVEL=INFO          # DEBUG / INFO / WARNING / ERROR
LOG_SENSITIVE=0         # 1 pour loguer plus de détails (à éviter en prod)
````

### API Key (service-to-service)

```env
# --- API KEY (service-to-service)
# Utilisée par le middleware d’auth interne (Bearer <token>)
PLUMID_API_KEY=change_me_for_internal_calls
```

### Auth JWT (comptes utilisateurs)

```env
# --- AUTH JWT (comptes utilisateurs)
AUTH_SECRET=change_this_to_a_long_random_secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### CORS

```env
# --- CORS (CSV d'origines autorisées)
# Exemple pour front en localhost
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Base de données

Deux modes sont possibles :

#### 1) URL complète (recommandé)

```env
DATABASE_URL=mysql+pymysql://plumid:password@localhost:3306/bird_db?charset=utf8mb4
```

#### 2) Champs unitaires (si `DATABASE_URL` est vide)

```env
# Hôte & port
IP_DB=localhost          # alias supportés : DB_HOST
PORT_DB=3306             # alias supportés : DB_PORT

# Credentials
USER_DB=plumid           # alias : DB_USER
MDP_DB=password          # alias : DB_PASSWORD
NAME_DB=bird_db          # alias : DB_NAME
DB_CHARSET=utf8mb4

# Pool & SSL (optionnels)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
#MYSQL_SSL_CA=/etc/ssl/certs/rds-combined-ca-bundle.pem
```

Le code reconstruit un DSN MySQL si `DATABASE_URL` est vide.

### SMTP (envoi d’email de vérification)

```env
# --- SMTP (vérification d'email)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@plumid.local
```

En dev, tu peux utiliser un serveur type Mailpit/MailHog (`localhost:1025`), en prod un vrai provider.

### Frontend (lien de vérification)

```env
# --- FRONTEND
FRONTEND_BASE_URL=http://localhost:5173
```

Le lien de vérification envoyé par email sera de la forme :
`<FRONTEND_BASE_URL>/verify-email?token=<JWT>`

---

## Lancement avec Docker Compose

Le `docker-compose.yaml` démarre deux services :

| Service | Image / Build | Port exposé |
| ------- | -------------- | ----------- |
| `db` | `mysql:8.0` | `3306` |
| `api` | `Dockerfile` local | `8000` |

La base de données est alimentée par les variables d'environnement du `.env` et un volume nommé `db_data` assure la persistance des données.

### Démarrage

```bash
# Construire et démarrer tous les services en arrière-plan
docker compose up -d --build
```

L'API écoute alors sur `http://localhost:8000`.  
L'API attend que MySQL soit prêt (healthcheck) avant de démarrer.

### Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f

# Logs d'un seul service
docker compose logs -f api

# Arrêter les services
docker compose down

# Arrêter ET supprimer les volumes (reset BDD)
docker compose down -v
```

### Variables Docker Compose

Le `docker-compose.yaml` lit ton `.env` et surcharge automatiquement `DATABASE_URL` pour pointer vers le service `db` interne :

```env
DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@db:3306/${MYSQL_DATABASE}?charset=utf8mb4
```

Tu peux personnaliser le compte MySQL via ces variables dans ton `.env` :

```env
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=plumid
MYSQL_USER=plumid
MYSQL_PASSWORD=plumid_password
```

---

## Authentification

L’API supporte **deux mécanismes distincts** :

1. **API Key** (service-to-service)
2. **JWT** (comptes utilisateurs, avec vérification d’email)

Les routes métiers (`/species`, `/feathers`, `/pictures`) peuvent être protégées soit par l’API Key, soit par `get_current_user` (JWT) selon la config choisie dans le code.

---

### 1) API Key (service-to-service)

Pour les appels internes (jobs, micro-services, etc.) :

```http
Authorization: Bearer <PLUMID_API_KEY>
```

Exemple `curl` :

```bash
curl -H "Authorization: Bearer $PLUMID_API_KEY" http://localhost:8000/health
```

---

### 2) JWT (comptes utilisateurs + vérification d’email)

Les comptes utilisateurs sont stockés dans la table `users`.
À l’inscription :

* un utilisateur est créé avec `is_verified = false`,
* un email de vérification est envoyé avec un lien contenant un **token** JWT (`scope = "email_verify"`),
* tant que l’email n’est pas vérifié, le **login renvoie 403**.

Endpoints :

* `POST /auth/register` — créer un compte et envoyer un email de vérification
* `GET  /auth/verify-email` — valider l’adresse email à partir du token
* `POST /auth/login` — obtenir un `access_token` JWT (si compte vérifié)
* `GET  /auth/me` — récupérer le profil courant (JWT valide requis)

#### `POST /auth/register`

Crée un nouvel utilisateur non vérifié et envoie un email de vérification.

**Body JSON :**

```json
{
  "mail": "user@example.com",
  "username": "birdlover",
  "password": "StrongPassw0rd!"
}
```

**Réponse 201 :**

```json
{
  "idusers": 1,
  "mail": "user@example.com",
  "username": "birdlover",
  "role": "user",
  "is_verified": false,
  "email_verified_at": null
}
```

**Erreurs possibles :**

* `400` — email déjà utilisé :

  ```json
  {
    "error": {
      "code": "HTTP_400",
      "message": "Un utilisateur avec cet email existe déjà.",
      "trace_id": "..."
    }
  }
  ```

* `422` — format d’email invalide (Pydantic, `EmailStr`).

#### `GET /auth/verify-email?token=<JWT>`

Valide l’adresse email à partir du token reçu par email.

**Succès (200) :**

```json
{
  "message": "Adresse email vérifiée avec succès."
}
```

**Déjà vérifié (200) :**

```json
{
  "message": "Adresse email déjà vérifiée."
}
```

**Erreurs :**

* `400` — token invalide ou expiré :

  ```json
  {
    "error": {
      "code": "HTTP_400",
      "message": "Token de vérification invalide ou expiré.",
      "trace_id": "..."
    }
  }
  ```

* `404` — utilisateur introuvable :

  ```json
  {
    "error": {
      "code": "HTTP_404",
      "message": "Utilisateur introuvable.",
      "trace_id": "..."
    }
  }
  ```

#### `POST /auth/login`

**Body JSON :**

```json
{
  "mail": "user@example.com",
  "password": "StrongPassw0rd!"
}
```

**Réponse 200 :**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Erreurs :**

* `401` — mail ou mot de passe incorrect :

  ```json
  {
    "error": {
      "code": "HTTP_401",
      "message": "Email ou mot de passe invalide.",
      "trace_id": "..."
    }
  }
  ```

* `403` — email non vérifié :

  ```json
  {
    "error": {
      "code": "HTTP_403",
      "message": "Adresse email non vérifiée. Merci de vérifier ton email.",
      "trace_id": "..."
    }
  }
  ```

#### `GET /auth/me`

**Headers :**

```http
Authorization: Bearer <jwt>
```

**Réponse 200 :**

```json
{
  "idusers": 1,
  "mail": "user@example.com",
  "username": "birdlover",
  "role": "user",
  "is_verified": true,
  "email_verified_at": "2025-10-29T09:42:15.123456+00:00"
}
```

Le token est signé en **HS256** avec `AUTH_SECRET`.
La durée de vie est définie par `ACCESS_TOKEN_EXPIRE_MINUTES`.

---

## Endpoints

> **Résumé des routes principales :**
>
> * `GET    /health`
> * `POST   /species`
> * `GET    /species/{idspecies}`
> * `DELETE /species/{idspecies}`
> * `POST   /feathers`
> * `GET    /feathers/{idfeathers}`
> * `DELETE /feathers/{idfeathers}`
> * `POST   /pictures`
> * `GET    /pictures/{idpictures}`
> * `DELETE /pictures/{idpictures}`
> * `POST   /auth/register`
> * `GET    /auth/verify-email`
> * `POST   /auth/login`
> * `GET    /auth/me`

### Health

[...]

*(les sections Species / Feathers / Pictures sont inchangées par rapport à ta version, tu peux les garder telles quelles, elles restent valides.)*

---

## Modèles de données

### Table `users`

* `idusers` (PK, int, auto)
* `mail` (unique, varchar 255)
* `username` (varchar 100)
* `password_hash` (varchar 255, hashé via bcrypt)
* `role` (varchar 45, ex. `"user"`, `"admin"`)
* `created_at` (datetime, default `CURRENT_TIMESTAMP`)
* `pictures_idpictures` (FK → `pictures.idpictures`, `ON DELETE SET NULL`)
* `is_verified` (bool, défaut `false`)
* `email_verified_at` (datetime, nullable) — horodatage de la vérification

*(Les autres tables `species`, `feathers`, `pictures` restent comme tu les avais, tu peux garder les définitions actuelles.)*

---

## Conventions & Erreurs

*(Identique à ta version, avec le même format d’erreur et les codes HTTP)*

---

## Exemples `curl`

Ajout d’un exemple pour la vérification d’email :

```bash
# Inscription utilisateur
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
        "mail": "user@example.com",
        "username": "birdlover",
        "password": "StrongPassw0rd!"
      }'

# (L'utilisateur reçoit un mail avec un lien du type :
#   http://localhost:5173/verify-email?token=<JWT>
# Le front peut ensuite appeler directement l’API si besoin.)

# Vérification d’email côté backend (test manuel par exemple)
curl "http://localhost:8000/auth/verify-email?token=<JWT>"

# Login utilisateur (après vérification d’email)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
        "mail": "user@example.com",
        "password": "StrongPassw0rd!"
      }'

# Profil utilisateur courant (remplace <jwt> par le token reçu)
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <jwt>"
```
