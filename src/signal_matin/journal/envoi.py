"""Envoi de l'edition par e-mail (SMTP).

Les parametres viennent uniquement de variables d'environnement (secrets GitHub
ou fichier .env local), jamais de config.yaml ni du depot :

    SMTP_SERVEUR        ex. smtp.gmail.com
    SMTP_PORT           465 (SSL, par defaut) ou 587 (STARTTLS)
    SMTP_UTILISATEUR    identifiant du compte d'envoi
    SMTP_MOT_DE_PASSE   mot de passe d'application ou jeton SMTP
    MAIL_DESTINATAIRE   adresse qui recoit le journal
    MAIL_EXPEDITEUR     facultatif, par defaut SMTP_UTILISATEUR

Le corps du message est la version numerique (HTML une colonne) ; le PDF A4 et
la page HTML sont joints pour une lecture hors de la messagerie.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import unescape
from pathlib import Path

from .rendu import date_longue

VARIABLES = ("SMTP_SERVEUR", "SMTP_UTILISATEUR", "SMTP_MOT_DE_PASSE", "MAIL_DESTINATAIRE")


class EnvoiImpossible(RuntimeError):
    pass


def _texte_brut(html: str) -> str:
    sans_style = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    texte = re.sub(r"<(br|/p|/h\d|/li|/div|/tr)[^>]*>", "\n", sans_style, flags=re.I)
    texte = unescape(re.sub(r"<[^>]+>", "", texte))
    return re.sub(r"\n\s*\n+", "\n\n", texte).strip()


def construire_message(edition: dict, html: str, pieces: list[Path], *, expediteur: str,
                       destinataire: str, essai: bool = False) -> EmailMessage:
    jour = dt.date.fromisoformat(edition["date"])
    sujet = f"Signal Matin · {date_longue(jour)}"
    if edition.get("secours"):
        sujet += " (édition de secours)"
    if essai:
        sujet = "[Essai] " + sujet
    message = EmailMessage()
    message["Subject"] = sujet
    message["From"] = f"Signal Matin <{expediteur}>"
    message["To"] = destinataire
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=expediteur.split("@")[-1] or "signal-matin")
    message.set_content(_texte_brut(html))
    message.add_alternative(html, subtype="html")
    for piece in pieces:
        if not piece.is_file():
            continue
        if piece.suffix == ".pdf":
            message.add_attachment(piece.read_bytes(), maintype="application", subtype="pdf", filename=piece.name)
        else:
            message.add_attachment(piece.read_text(encoding="utf-8"), subtype="html", filename=piece.name)
    return message


def envoyer(edition: dict, html: str, pieces: list[Path], *, essai: bool = False, journal=print) -> None:
    manquantes = [v for v in VARIABLES if not os.environ.get(v)]
    if manquantes:
        raise EnvoiImpossible("paramètres d'envoi absents : " + ", ".join(manquantes))
    serveur = os.environ["SMTP_SERVEUR"]
    port = int(os.environ.get("SMTP_PORT") or 465)
    utilisateur = os.environ["SMTP_UTILISATEUR"]
    expediteur = os.environ.get("MAIL_EXPEDITEUR") or utilisateur
    destinataires = [a.strip() for a in os.environ["MAIL_DESTINATAIRE"].split(",") if a.strip()]
    message = construire_message(edition, html, pieces, expediteur=expediteur,
                                 destinataire=", ".join(destinataires), essai=essai)
    contexte = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(serveur, port, context=contexte, timeout=60) as smtp:
                smtp.login(utilisateur, os.environ["SMTP_MOT_DE_PASSE"])
                smtp.send_message(message)
        else:
            with smtplib.SMTP(serveur, port, timeout=60) as smtp:
                smtp.starttls(context=contexte)
                smtp.login(utilisateur, os.environ["SMTP_MOT_DE_PASSE"])
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as erreur:
        # Le message d'erreur SMTP ne contient jamais le mot de passe.
        raise EnvoiImpossible(f"{type(erreur).__name__} : {erreur}") from erreur
    journal(f"✓ E-mail envoyé ({len(destinataires)} destinataire(s))")
