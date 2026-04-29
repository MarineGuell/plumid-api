"""seed species (id=0 = Non identifié + 6 espèces de référence)

Revision ID: 0002_seed_species
Revises: 0001_baseline_pg
Create Date: 2026-04-29 12:00:00.000000

Idempotente : utilise ON CONFLICT (idspecies) DO UPDATE pour pouvoir être
relancée sans danger. Resynchronise la séquence `species_idspecies_seq`
après l'insertion explicite des ids 0..6 pour que les futurs INSERT auto
ne tombent pas en collision avec les seeds.

Note : `idspecies = 0` est réservé à l'espèce sentinelle « Non identifié »
renvoyée par le service de classification quand le modèle ne reconnaît
rien. Les 6 espèces suivantes correspondent à `STUB_SPECIES` dans
`plumid-model/service.py`.

La migration est dialect-aware (PostgreSQL en prod, SQLite pour les tests
unitaires) — les deux fournissent désormais une sémantique d'`upsert` à
peu près équivalente.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002_seed_species"
down_revision: Union[str, Sequence[str], None] = "0001_baseline_pg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Une seule liste de seeds, partagée par toutes les branches dialect.
# (idspecies, region, environment, information, species_name, species_url_picture)
SEEDS = [
    (
        0, None, None,
        "Aucune espèce reconnue par le modèle. Cette entrée sentinelle est utilisée quand la prédiction est sous le seuil de confiance ou que l'image ne contient pas de plume identifiable.",
        "Non identifié",
        None,
    ),
    (
        1, "Europe", "Forêts, zones urbaines",
        "La Pie bavarde (Pica pica) est une espèce de passereaux de la famille des Corvidae, et l'une des espèces de corvidés parmi les plus répandues en Europe et dans une grande partie de l'Asie. Les pies peuvent aisément être identifiées grâce à leur morphologie et à leur plumage noir et blanc caractéristique. Il existe 13 sous-espèces de pie bavarde.",
        "Pie bavarde (Pica pica)",
        None,
    ),
    (
        2, "Europe", "Forêts",
        "Le Pic épeiche (Dendrocopos major) est l'espèce de pics la plus répandue et la plus commune en Europe et dans le Nord de l'Asie. Faisant partie des pics de taille moyenne, il se caractérise par un plumage rayé de blanc et de noir et une tache rouge écarlate sur le bas-ventre près de la queue. Espèce diurne, le Pic épeiche vit solitaire ou par couple dans un territoire dont il ne s'éloigne guère, même en hiver, les mâles étant les plus sédentaires. Il peut adopter un comportement plus erratique et migrer en hiver lorsque la nourriture se raréfie.",
        "Pic épeiche (Dendrocopos major)",
        None,
    ),
    (
        3, "Europe, Asie (introduite en Europe)", "Zones urbaines, parcs",
        "La Perruche à collier (Psittacula krameri) est une espèce de grandes perruches originaire d'Asie et d'Afrique et aujourd'hui naturalisée en Europe de l'Ouest. Elle est souvent élevée en captivité comme animal de compagnie. Elle est considérée comme l'un des oiseaux parleurs les plus habiles. Elle est d'ailleurs bien connue en Europe depuis l'Antiquité et le Moyen Âge, où elle fait partie des plus anciens oiseaux de compagnie, comme sa cousine la Perruche alexandre. Elle est souvent représentée dans l'art européen, depuis les mosaïques romaines jusqu'aux peintures de la Renaissance en passant par les enluminures médiévales.",
        "Perruche à collier (Psittacula krameri)",
        None,
    ),
    (
        4, "Europe", "Forêts, parcs",
        "Le Geai des chênes (Garrulus glandarius) est un oiseau de la famille des Corvidae facilement reconnaissable à son plumage brun rosé, ses ailes ornées de plumes bleu vif barrées de noir et sa moustache noire. Très vif et méfiant, il est connu pour ses cris rauques et ses talents d'imitateur, capables de reproduire les appels d'autres oiseaux ou même certains bruits environnants. Principalement forestier, il fréquente aussi les parcs et jardins arborés. Son nom provient de son comportement caractéristique : il collecte et cache des glands en grande quantité pour constituer des réserves alimentaires, jouant ainsi un rôle important dans la dispersion des chênes. Omnivore, il se nourrit également d'insectes, de fruits, de graines et parfois d'œufs ou de petits animaux.",
        "Geai des chênes (Garrulus glandarius)",
        None,
    ),
    (
        5, "Europe", "Zones urbaines, campagnes",
        "La Corneille noire (Corvus corone) est une espèce de passereaux de la famille des Corvidae. Elle est présente dans deux aires distinctes de l'écozone paléarctique : l'Europe de l'Ouest et du Sud-Ouest, où sa population est estimée entre 5,5 et 12 millions de couples, et en Asie du Kazakhstan au Japon, où sa population n'est pas connue. Un des oiseaux les plus communs dans son aire de répartition, elle se trouve à peu près partout, de la campagne jusqu'au cœur des grandes villes.",
        "Corneille noire (Corvus corone)",
        None,
    ),
    (
        6, "Europe, Asie, Amérique du Nord", "Zones humides, étangs, rivières",
        "Le Canard colvert, col-vert (Anas platyrhynchos), ou Canard malard au Canada, est une espèce d'oiseaux de l'ordre des Ansériformes, de la famille des Anatidae et de la sous-famille des Anatinae. C'est certainement le plus connu et reconnaissable de tous les canards, du fait de l'existence de races de canards domestiques issues de cette espèce.",
        "Canard colvert (Anas platyrhynchos)",
        None,
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    from sqlalchemy import text

    if dialect == "postgresql":
        # Postgres: ON CONFLICT DO UPDATE — refresh descriptions if the
        # migration is replayed with updated text.
        for seed in SEEDS:
            bind.execute(
                text(
                    """
                    INSERT INTO species
                        (idspecies, region, environment, information, species_name, species_url_picture)
                    VALUES (:id, :region, :env, :info, :name, :pic)
                    ON CONFLICT (idspecies) DO UPDATE SET
                        region              = EXCLUDED.region,
                        environment         = EXCLUDED.environment,
                        information         = EXCLUDED.information,
                        species_name        = EXCLUDED.species_name,
                        species_url_picture = EXCLUDED.species_url_picture
                    """
                ),
                {
                    "id": seed[0], "region": seed[1], "env": seed[2],
                    "info": seed[3], "name": seed[4], "pic": seed[5],
                },
            )
        # Resync the SERIAL sequence so the next auto-INSERT doesn't
        # collide with the explicitly-set ids 0..6.
        bind.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence('species', 'idspecies'),
                    GREATEST((SELECT COALESCE(MAX(idspecies), 0) FROM species), 1),
                    true
                )
                """
            )
        )

    elif dialect == "sqlite":
        # SQLite portable form: INSERT OR REPLACE (delete-then-insert).
        # No sequence to resync (SQLite handles AUTOINCREMENT via
        # sqlite_sequence which we don't manipulate manually).
        for seed in SEEDS:
            bind.execute(
                text(
                    """
                    INSERT OR REPLACE INTO species
                        (idspecies, region, environment, information, species_name, species_url_picture)
                    VALUES (:id, :region, :env, :info, :name, :pic)
                    """
                ),
                {
                    "id": seed[0], "region": seed[1], "env": seed[2],
                    "info": seed[3], "name": seed[4], "pic": seed[5],
                },
            )

    else:
        # Best-effort plain INSERT for any other dialect. May fail on
        # re-runs because there's no portable upsert in SQL standard.
        for seed in SEEDS:
            try:
                bind.execute(
                    text(
                        """
                        INSERT INTO species
                            (idspecies, region, environment, information, species_name, species_url_picture)
                        VALUES (:id, :region, :env, :info, :name, :pic)
                        """
                    ),
                    {
                        "id": seed[0], "region": seed[1], "env": seed[2],
                        "info": seed[3], "name": seed[4], "pic": seed[5],
                    },
                )
            except Exception:
                # Row probably already there — ignore.
                pass


def downgrade() -> None:
    # Ne supprime que les lignes 0..6 ajoutées par cette migration.
    # Les espèces ajoutées ultérieurement par l'application via l'API
    # (idspecies >= 7) ne sont pas touchées.
    op.execute("DELETE FROM species WHERE idspecies BETWEEN 0 AND 6")
