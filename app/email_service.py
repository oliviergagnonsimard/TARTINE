import resend
import os
import secrets
from dotenv import load_dotenv
from database import connectToDB, releaseConn, createNotification, getUserByEmail

load_dotenv()

resend.api_key = os.environ.get("RESEND_API_KEY")


# ── Template de base ──────────────────────────────────────────────────────────

def _base_email(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">

          <!-- Logo / marque -->
          <tr>
            <td align="center" style="padding-bottom:28px;">
              <span style="font-size:28px;font-weight:800;letter-spacing:-1px;color:#fff;">
                tar<span style="color:#e91e8c;">tine</span>
              </span>
            </td>
          </tr>

          <!-- Carte principale -->
          <tr>
            <td style="
              background:#111111;
              border:0.5px solid #222222;
              border-radius:16px;
              padding:36px 40px;
              position:relative;
            ">
              {body}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="padding-top:28px;">
              <p style="margin:0;font-size:12px;color:#333;line-height:1.6;">
                Tu reçois ce courriel car un compte Tartine est associé à cette adresse.<br>
                Si ce n'est pas toi, ignore simplement ce message.
              </p>
              <p style="margin:12px 0 0;font-size:11px;color:#222;">
                © 2025 Tartine · noreply@tartine.app
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Corps : confirmation de compte ───────────────────────────────────────────

def _confirmation_body(confirm_url: str) -> str:
    return f"""
      <!-- Icône -->
      <div style="
        width:48px;height:48px;border-radius:12px;
        background:rgba(233,30,140,0.12);
        display:flex;align-items:center;justify-content:center;
        margin-bottom:24px;font-size:22px;
      ">✉️</div>

      <!-- Titre -->
      <h1 style="margin:0 0 8px;font-size:24px;font-weight:700;
                 letter-spacing:-0.5px;color:#ffffff;line-height:1.2;">
        Bienvenue sur Tartine&nbsp;!
      </h1>
      <p style="margin:0 0 28px;font-size:14px;color:#555555;line-height:1.6;">
        Plus qu'une étape — confirme ton adresse pour activer ton compte.
      </p>

      <!-- Bouton -->
      <a href="{confirm_url}" style="
        display:inline-block;
        background:#d32f89;
        color:#ffffff;
        font-size:14px;font-weight:600;
        padding:13px 28px;
        border-radius:8px;
        text-decoration:none;
        letter-spacing:0.2px;
        margin-bottom:28px;
      ">Confirmer mon compte →</a>

      <!-- Séparateur -->
      <div style="border-top:0.5px solid #1e1e1e;margin-bottom:24px;"></div>

      <!-- Lien de secours -->
      <p style="margin:0;font-size:12px;color:#444444;line-height:1.7;">
        Le bouton ne fonctionne pas&nbsp;?<br>
        Copie ce lien dans ton navigateur&nbsp;:<br>
        <span style="color:#e91e8c;word-break:break-all;">{confirm_url}</span>
      </p>

      <!-- Expiry note -->
      <p style="margin:16px 0 0;font-size:12px;color:#333333;">
        🔒 Ce lien est valide pendant <strong style="color:#555;">24 heures</strong>.
      </p>
    """


# ── Corps : réinitialisation de mot de passe ─────────────────────────────────

def _reset_body(reset_url: str) -> str:
    return f"""
      <!-- Icône -->
      <div style="
        width:48px;height:48px;border-radius:12px;
        background:rgba(233,30,140,0.12);
        font-size:22px;
        display:flex;align-items:center;justify-content:center;
        margin-bottom:24px;
      ">🔑</div>

      <!-- Titre -->
      <h1 style="margin:0 0 8px;font-size:24px;font-weight:700;
                 letter-spacing:-0.5px;color:#ffffff;line-height:1.2;">
        Réinitialisation du mot de passe
      </h1>
      <p style="margin:0 0 28px;font-size:14px;color:#555555;line-height:1.6;">
        On a reçu une demande pour réinitialiser le mot de passe associé à ce compte.<br>
        Si ce n'est pas toi, ignore ce courriel — rien ne changera.
      </p>

      <!-- Bouton -->
      <a href="{reset_url}" style="
        display:inline-block;
        background:#d32f89;
        color:#ffffff;
        font-size:14px;font-weight:600;
        padding:13px 28px;
        border-radius:8px;
        text-decoration:none;
        letter-spacing:0.2px;
        margin-bottom:28px;
      ">Choisir un nouveau mot de passe →</a>

      <!-- Séparateur -->
      <div style="border-top:0.5px solid #1e1e1e;margin-bottom:24px;"></div>

      <!-- Lien de secours -->
      <p style="margin:0;font-size:12px;color:#444444;line-height:1.7;">
        Le bouton ne fonctionne pas&nbsp;?<br>
        Copie ce lien dans ton navigateur&nbsp;:<br>
        <span style="color:#e91e8c;word-break:break-all;">{reset_url}</span>
      </p>

      <!-- Expiry note -->
      <p style="margin:16px 0 0;font-size:12px;color:#333333;">
        ⏱ Ce lien expire dans <strong style="color:#555;">1 heure</strong>.
      </p>
    """


# ── Tokens ───────────────────────────────────────────────────────────────────

def createVerificationToken(idClient):
    token = secrets.token_urlsafe(32)
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'UPDATE "user" SET verification_token = %s WHERE "idClient" = %s',
            (token, idClient)
        )
        conn.commit()
    releaseConn(conn)
    return token

def verifyUserToken(token):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'UPDATE "user" SET is_verified = TRUE, verification_token = NULL '
            'WHERE verification_token = %s RETURNING "idClient"',
            (token,)
        )
        row = curs.fetchone()
        conn.commit()
    releaseConn(conn)
    return row

def createResetToken(idClient):
    token = secrets.token_urlsafe(32)
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            "UPDATE \"user\" SET reset_token = %s, reset_token_expiry = NOW() + INTERVAL '1 hour' "
            "WHERE \"idClient\" = %s",
            (token, idClient)
        )
        conn.commit()
    releaseConn(conn)
    return token

def verifyResetToken(token):
    conn = connectToDB()
    with conn.cursor() as curs:
        curs.execute(
            'SELECT "idClient" FROM "user" WHERE reset_token = %s AND reset_token_expiry > NOW()',
            (token,)
        )
        row = curs.fetchone()
    releaseConn(conn)
    return row[0] if row else None


# ── Envoi des courriels ───────────────────────────────────────────────────────

def sendConfirmationEmail(toEmail, token):
    confirm_url = f"{os.environ.get('BASE_URL')}/confirm/{token}"
    resend.Emails.send({
        "from": "Tartine <noreply@tartine.app>",
        "to": toEmail,
        "subject": "Confirme ton compte Tartine",
        "html": _base_email("Confirme ton compte Tartine", _confirmation_body(confirm_url))
    })

def sendResetEmail(toEmail, token):
    reset_url = f"{os.environ.get('BASE_URL')}/reset-password/{token}"
    resend.Emails.send({
        "from": "Tartine <noreply@tartine.app>",
        "to": toEmail,
        "subject": "Réinitialisation de ton mot de passe Tartine",
        "html": _base_email("Réinitialisation du mot de passe", _reset_body(reset_url))
    })
    createNotification(
        getUserByEmail(toEmail)[0],
        "Changement de mot de passe",
        "Nous vous avons envoyé un courriel pour réinitialiser votre mot de passe"
    )