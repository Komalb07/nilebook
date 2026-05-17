import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

FROM_EMAIL = os.getenv("FROM_EMAIL", "Nilebook <onboarding@resend.dev>")
EMAIL_DELIVERY_MODE = os.getenv("EMAIL_DELIVERY_MODE", "console").lower()


def send_email(to: str, subject: str, html: str):
    if EMAIL_DELIVERY_MODE == "console":
        print(f"\n[Nilebook email skipped: console mode]\nTo: {to}\nSubject: {subject}\n")
        print(html)
        print("\n[End Nilebook email]\n")
        return {"mode": "console", "to": to, "subject": subject}

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY is missing")

    return resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    })


def send_verification_email(to: str, verification_link: str):
    subject = "Verify your Nilebook email"

    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #17351f;">
      <h2>Verify your email</h2>
      <p>Welcome to Nilebook. Please verify your email address to activate your account.</p>
      <p>
        <a href="{verification_link}"
           style="display:inline-block;padding:12px 18px;background:#1f7a45;color:white;text-decoration:none;border-radius:999px;font-weight:bold;">
          Verify Email
        </a>
      </p>
      <p>If the button does not work, copy and paste this link into your browser:</p>
      <p>{verification_link}</p>
    </div>
    """

    return send_email(to, subject, html)


def send_password_reset_email(to: str, reset_link: str):
    subject = "Reset your Nilebook password"

    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #17351f;">
      <h2>Reset your password</h2>
      <p>You requested to reset your Nilebook password. This link expires soon.</p>
      <p>
        <a href="{reset_link}"
           style="display:inline-block;padding:12px 18px;background:#1f7a45;color:white;text-decoration:none;border-radius:999px;font-weight:bold;">
          Reset Password
        </a>
      </p>
      <p>If the button does not work, copy and paste this link into your browser:</p>
      <p>{reset_link}</p>
    </div>
    """

    return send_email(to, subject, html)
