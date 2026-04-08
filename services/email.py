# api/services/email.py
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from settings import settings

logger = logging.getLogger(__name__)


def _get_smtp_client() -> smtplib.SMTP:
    """
    Initialise un client SMTP à partir de la configuration globale (settings).

    - Utilise settings.smtp_host / settings.smtp_port
    - Si un user + password sont définis, active STARTTLS + login
    """
    client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)

    if settings.smtp_user and settings.smtp_password:
        try:
            client.starttls()
        except smtplib.SMTPException:
            logger.exception("Échec lors de l'initialisation STARTTLS avec le serveur SMTP.")
            raise

        try:
            client.login(settings.smtp_user, settings.smtp_password)
        except smtplib.SMTPException:
            logger.exception(
                "Échec lors de l'authentification SMTP (user=%s).",
                settings.smtp_user,
            )
            raise

    return client


def _send_email(msg: EmailMessage) -> None:
    """
    Envoi générique d'un EmailMessage via SMTP.
    """
    try:
        with _get_smtp_client() as server:
            server.send_message(msg)
        logger.info("Email envoyé à %s", msg["To"])
    except Exception:
        logger.exception("Impossible d'envoyer l'email à %s", msg.get("To"))
        raise


def send_verification_email(to_email: str, verification_link: str) -> None:
    """
    Envoie un email de vérification contenant un lien.

    La configuration SMTP (hôte, port, identifiants, expéditeur)
    est lue depuis les settings :
      - settings.smtp_host
      - settings.smtp_port
      - settings.smtp_user
      - settings.smtp_password
      - settings.smtp_from
    """
    msg = EmailMessage()
    msg["Subject"] = "Plum’ID - Vérifie ton adresse email"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    msg.set_content(
        f"""Bonjour,

Merci de t'être inscrit sur Plum'ID.

Pour confirmer ton adresse email, clique sur le lien suivant :
{verification_link}

Si tu n'es pas à l'origine de cette demande, tu peux ignorer cet email.

—
L'équipe Plum'ID
"""
    )

    _send_email(msg)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Envoie un email de réinitialisation de mot de passe contenant un lien.
    """
    msg = EmailMessage()
    msg["Subject"] = "Plum’ID - Réinitialisation de ton mot de passe"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    msg.set_content(
        f"""Bonjour,

        Une demande de réinitialisation de mot de passe a été effectuée pour ce compte Plum'ID.
        
        Si tu es à l'origine de cette demande, clique sur le lien suivant pour choisir un nouveau mot de passe :
        {reset_link}
        
        Si tu n'es pas à l'origine de cette demande, tu peux ignorer cet email.
        Le lien expirera automatiquement après un certain temps.
        
        —
        L'équipe Plum'ID
        """
    )

    _send_email(msg)
