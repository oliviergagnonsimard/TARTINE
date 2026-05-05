import resend
import os
import secrets
from dotenv import load_dotenv
from database import connectToDB, releaseConn, createNotification, getUserByEmail

load_dotenv()

resend.api_key = os.environ.get("RESEND_API_KEY")

def createVerificationToken(idClient):
    token = secrets.token_urlsafe(32)
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'UPDATE client SET verification_token = %s WHERE "idClient" = %s',
            (token, idClient)
        )
        conn.commit()
    releaseConn(conn)
    return token

def verifyUserToken(token):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'UPDATE client SET is_verified = TRUE, verification_token = NULL '
            'WHERE verification_token = %s RETURNING "idClient"',
            (token,)
        )
        row = curs.fetchone()
        conn.commit()
    releaseConn(conn)
    return row

def sendConfirmationEmail(toEmail, token):
    confirmUrl = f"{os.environ.get('BASE_URL')}/confirm/{token}"
    
    resend.Emails.send({
        "from": "Tartine <noreply@tartine.app>",
        "to": toEmail,
        "subject": "Confirme ton compte TARTINE",
        "html": f"""
            <h2>Bienvenue sur Tartine!</h2>
            <p>Clique sur le lien ci-dessous pour confirmer ton compte :</p>
            <a href="{confirmUrl}" style="
                background-color: #e91e8c;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            ">Confirmer mon compte</a>
            <p style="color: #aaa; font-size: 12px; margin-top: 20px;">
                Si tu n'as pas créé de compte, ignore ce courriel.
            </p>
        """
    })



def createResetToken(idClient):
    token = secrets.token_urlsafe(32)
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            "UPDATE client SET reset_token = %s, reset_token_expiry = NOW() + INTERVAL '1 hour' WHERE \"idClient\" = %s",
            (token, idClient)
        )
        conn.commit()
    releaseConn(conn)
    return token

def verifyResetToken(token):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'SELECT "idClient" FROM client WHERE reset_token = %s AND reset_token_expiry > NOW()',
            (token,)
        )
        row = curs.fetchone()
    releaseConn(conn)
    return row[0] if row else None

def sendResetEmail(toEmail, token):
    confirmUrl = f"{os.environ.get('BASE_URL')}/reset-password/{token}"
    
    resend.Emails.send({
        "from": "Tartine <noreply@tartine.app>",
        "to": toEmail,
        "subject": "Réinitialisation de votre mot de passe Tartine",
        "html": f"""
            <h2>Problème de connexion?</h2>
            <p>Clique sur le lien ci-dessous afin de réinitialiser ton mot de passe</p>
            <a href="{confirmUrl}" style="
                background-color: #e91e8c;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            ">Continuer</a>
        """
    })

    createNotification(getUserByEmail(toEmail)[0], "Changement de mot de passe", "Nous vous avons envoyé un courriel pour réinitialiser votre mot de passe")
