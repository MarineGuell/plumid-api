# Guide des migrations de base de données

Ce projet utilise [Alembic](https://alembic.sqlalchemy.org/) pour gérer les migrations de schéma SQLAlchemy.

---

## Prérequis

Les migrations s'exécutent **dans le conteneur Docker** `api`, qui a accès au réseau interne Docker (et donc à la base de données `db`).

La stack doit être démarrée :

```bash
docker compose up -d
```

---

## Workflow standard

### 1. Modifier un modèle SQLAlchemy

Édite le fichier concerné dans `models/` (ex: `models/species.py`).  
Répercute les changements dans le schema Pydantic correspondant (`schemas/`).

### 2. Générer la migration

```bash
docker compose exec api alembic revision --autogenerate -m "description du changement"
```

Alembic compare l'état des modèles avec le schéma actuel de la BDD et génère un fichier dans `alembic/versions/`.

> **Important :** Toujours vérifier le fichier généré avant de l'appliquer. Alembic ne détecte pas tout automatiquement (renommages de colonnes, contraintes complexes, etc.).

### 3. Appliquer la migration

```bash
docker compose exec api alembic upgrade head
```

---

## Commandes utiles

| Commande | Description |
| --- | --- |
| `alembic upgrade head` | Applique toutes les migrations en attente |
| `alembic upgrade +1` | Applique la prochaine migration uniquement |
| `alembic downgrade -1` | Annule la dernière migration |
| `alembic downgrade base` | Revient à l'état initial (aucune migration appliquée) |
| `alembic current` | Affiche la révision actuellement appliquée en BDD |
| `alembic history` | Liste toutes les migrations dans l'ordre |
| `alembic show <revision>` | Détaille une révision spécifique |

Toutes ces commandes sont à préfixer de `docker compose exec api`.

---

## Erreurs fréquentes

### `Target database is not up to date`

La BDD a des migrations en attente. Il faut les appliquer **avant** de générer une nouvelle révision :

```bash
docker compose exec api alembic upgrade head
# puis relancer la génération
docker compose exec api alembic revision --autogenerate -m "..."
```

### `Can't locate revision identified by '...'`

Le fichier de migration en BDD ne correspond à aucun fichier dans `alembic/versions/`. Causes possibles : fichier supprimé, branche Git différente. Vérifier avec `alembic history`.

### La migration générée est vide

Alembic n'a détecté aucun changement. Vérifier que :

- Le modèle est bien importé dans `alembic/env.py` (via `import models`)
- Le modèle hérite bien de `Base` (depuis `models/base.py`)

---

## Structure des fichiers

```txt
alembic/
├── env.py            # Configuration Alembic (pointe vers Base.metadata et settings)
├── script.py.mako    # Template pour les fichiers de migration
└── versions/         # Fichiers de migration générés (à commiter dans Git)
alembic.ini           # Configuration générale Alembic
```

---

## Conventions

- **Nommer clairement** les migrations : `add_user_email_verified`, `remove_species_sex_column`, etc.
- **Commiter** les fichiers de migration dans Git avec les modifications de modèles correspondantes.
- **Ne jamais modifier** une migration déjà appliquée en production. Créer une nouvelle révision à la place.
