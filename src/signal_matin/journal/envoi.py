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


def _parametre(nom: str) -> str:
    """Valeur d'une variable d'environnement, sans espaces ni retours a la ligne parasites."""
    return (os.environ.get(nom) or "").strip()


def _modes(port: int) -> list[tuple[int, bool]]:
    """Tentatives (port, SSL direct) : le port demande, puis l'autre mode standard en secours."""
    principal = (port, port == 465)
    secours = (587, False) if port == 465 else (465, True)
    return [principal] if principal == secours else [principal, secours]


def _envoyer_via(serveur: str, port: int, ssl_direct: bool, utilisateur: str, mot_de_passe: str,
                 message: EmailMessage) -> None:
    contexte = ssl.create_default_context()
    if ssl_direct:
        with smtplib.SMTP_SSL(serveur, port, context=contexte, timeout=60) as smtp:
            smtp.login(utilisateur, mot_de_passe)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(serveur, port, timeout=60) as smtp:
            smtp.ehlo()
            smtp.starttls(context=contexte)
            smtp.ehlo()
            smtp.login(utilisateur, mot_de_passe)
            smtp.send_message(message)


def envoyer(edition: dict, html: str, pieces: list[Path], *, essai: bool = False, journal=print,
            _transport=_envoyer_via) -> None:
    manquantes = [v for v in VARIABLES if not _parametre(v)]
    if manquantes:
        raise EnvoiImpossible("paramètres d'envoi absents : " + ", ".join(manquantes))
    serveur = _parametre("SMTP_SERVEUR")
    for prefixe in ("https://", "http://", "smtp://", "smtps://"):
        if serveur.lower().startswith(prefixe):
            serveur = serveur[len(prefixe):]
    serveur = serveur.rstrip("/")
    port_brut = _parametre("SMTP_PORT") or "465"
    try:
        port = int(port_brut)
    except ValueError:
        raise EnvoiImpossible(f"SMTP_PORT invalide : « {port_brut} » (attendu 465 ou 587)") from None
    utilisateur = _parametre("SMTP_UTILISATEUR")
    mot_de_passe = _parametre("SMTP_MOT_DE_PASSE").replace(" ", "")
    expediteur = _parametre("MAIL_EXPEDITEUR") or utilisateur
    destinataires = [a.strip() for a in _parametre("MAIL_DESTINATAIRE").split(",") if a.strip()]
    message = construire_message(edition, html, pieces, expediteur=expediteur,
                                 destinataire=", ".join(destinataires), essai=essai)
    erreurs = []
    for port_essai, ssl_direct in _modes(port):
        mode = "SSL" if ssl_direct else "STARTTLS"
        # Ni le mot de passe ni l'identifiant ne sont ecrits dans le journal.
        journal(f"· Envoi via {serveur}:{port_essai} ({mode})")
        try:
            _transport(serveur, port_essai, ssl_direct, utilisateur, mot_de_passe, message)
        except smtplib.SMTPAuthenticationError as erreur:
            # Identifiants refuses : changer de port n'y changera rien.
            raise EnvoiImpossible(
                f"identifiants refusés par {serveur} ({erreur.smtp_code}) : vérifier SMTP_UTILISATEUR "
                "et SMTP_MOT_DE_PASSE (mot de passe d'application)") from erreur
        except (smtplib.SMTPException, OSError) as erreur:
            # Le message d'erreur SMTP ne contient jamais le mot de passe.
            erreurs.append(f"{port_essai}/{mode} → {type(erreur).__name__} : {erreur}")
            journal(f"  échec : {type(erreur).__name__} : {erreur}")
            continue
        journal(f"✓ E-mail envoyé ({len(destinataires)} destinataire(s))")
        return
    raise EnvoiImpossible(f"{serveur} injoignable · " + " ; ".join(erreurs))


def tester_connexion(journal=print) -> int:
    """Diagnostic SMTP sans rien envoyer : resolution DNS, accueil du serveur, identification.

    Chaque ligne est aussi emise en annotation GitHub Actions (visible dans le resume du run).
    Le serveur est decrit par son adresse IP et son nom inverse, que GitHub ne masque pas.
    """
    import socket

    def note(texte: str) -> None:
        journal(texte)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::notice title=Test e-mail::{texte}", flush=True)

    manquantes = [v for v in VARIABLES if not _parametre(v)]
    if manquantes:
        note("paramètres absents : " + ", ".join(manquantes))
        return 2
    serveur = _parametre("SMTP_SERVEUR")
    for prefixe in ("https://", "http://", "smtp://", "smtps://"):
        if serveur.lower().startswith(prefixe):
            serveur = serveur[len(prefixe):]
    serveur = serveur.rstrip("/")
    connus = {"smtp.gmail.com": "Gmail", "smtp.protonmail.ch": "Proton"}
    note(f"serveur : {connus.get(serveur.lower(), 'NON STANDARD')} · {len(serveur)} caractères")
    utilisateur = _parametre("SMTP_UTILISATEUR")
    note(f"identifiant : {'adresse e-mail' if '@' in utilisateur else 'SANS @'} · "
         f"mot de passe : {len(_parametre('SMTP_MOT_DE_PASSE').replace(' ', ''))} caractères")
    try:
        ip = socket.getaddrinfo(serveur, None, socket.AF_INET)[0][4][0]
        try:
            inverse = socket.gethostbyaddr(ip)[0]
        except OSError:
            inverse = "sans nom inverse"
        note(f"résolution : {ip} ({inverse})")
    except OSError as erreur:
        note(f"résolution impossible : {erreur}")
        return 2
    contexte = ssl.create_default_context()
    reussi = False
    for port, ssl_direct in ((465, True), (587, False)):
        mode = "SSL" if ssl_direct else "STARTTLS"
        try:
            if ssl_direct:
                smtp = smtplib.SMTP_SSL(serveur, port, context=contexte, timeout=30)
            else:
                smtp = smtplib.SMTP(serveur, port, timeout=30)
            with smtp:
                accueil = smtp.ehlo()[0]
                if not ssl_direct:
                    smtp.starttls(context=contexte)
                    smtp.ehlo()
                smtp.login(utilisateur, _parametre("SMTP_MOT_DE_PASSE").replace(" ", ""))
            note(f"{port}/{mode} : accueil {accueil}, identification acceptée ✓")
            reussi = True
        except smtplib.SMTPAuthenticationError as erreur:
            note(f"{port}/{mode} : connexion OK mais identifiants refusés ({erreur.smtp_code})")
        except (smtplib.SMTPException, OSError) as erreur:
            note(f"{port}/{mode} : {type(erreur).__name__} : {erreur}")
    return 0 if reussi else 2
