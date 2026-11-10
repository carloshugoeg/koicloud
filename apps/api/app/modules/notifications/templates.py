from __future__ import annotations

from html import escape
from typing import Any, NamedTuple

from app.core.config import get_settings

_LOGO_PATH = "/koi/koi-mark-32.png"
_PUBLIC_LOGO_ORIGIN = "https://koicloud-web.vercel.app"


class RenderedEmail(NamedTuple):
    template: str
    subject: str
    text_body: str
    html_body: str


TEMPLATES: dict[str, dict[str, Any]] = {
    "verify_email": {
        "subject": "Verificá tu correo",
        "required_context": ("url", "email"),
    },
    "reset_password": {
        "subject": "Restablecé tu contraseña",
        "required_context": ("url", "email"),
    },
    "invoice_issued": {
        "subject": "Tu factura de KoiCloud",
        "required_context": ("code", "total"),
    },
    "subscription_canceled": {
        "subject": "Cancelación programada",
        "required_context": ("plan", "ends_on"),
    },
}


def _email_logo_url() -> str:
    domain = get_settings().koicloud_domain.strip()
    host = domain.lower()
    if host in {"", "local", "localhost"} or host.endswith(".local"):
        return f"{_PUBLIC_LOGO_ORIGIN}{_LOGO_PATH}"
    return f"https://{domain}{_LOGO_PATH}"


def _email_logo_img() -> str:
    src = escape(_email_logo_url(), quote=True)
    return (
        f'<img src="{src}" width="32" height="32" alt="Símbolo de KoiCloud" '
        'style="vertical-align:middle;border:0;">'
    )


def _render_verify_email(context: dict[str, Any]) -> tuple[str, str]:
    email = str(context["email"])
    url = str(context["url"])

    text = (
        f"Hola,\n\n"
        f"Gracias por registrarte en KoiCloud con el correo {email}.\n"
        f"Para verificar tu cuenta y comenzar a utilizar la plataforma, visita el siguiente enlace:\n\n"
        f"{url}\n\n"
        f"Este enlace vence en 24 horas.\n"
        f"Si no solicitaste esta cuenta, puedes ignorar este mensaje.\n"
    )

    safe_email = escape(email, quote=True)
    safe_url = escape(url, quote=True)
    text += "\nKoiCloud · PaaS de datos\n"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Verificá tu correo</title></head>
<body style="margin:0;padding:0;background-color:#F2ECDC;color:#14211F;font-family:Verdana,sans-serif;line-height:1.6;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F2ECDC;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background-color:#FFFCF4;border-top:4px solid #0A6D64;">
<tr><td style="padding:24px;border-bottom:1px solid #F2ECDC;">
{_email_logo_img()}
<span style="font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:600;vertical-align:middle;">KoiCloud</span>
</td></tr>
<tr><td style="padding:24px;">
<h1 style="margin:0 0 20px;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:600;">Verificá tu correo</h1>
<p>Hola,</p>
<p>Gracias por registrarte en KoiCloud con el correo <strong>{safe_email}</strong>.</p>
<p>Para verificar tu cuenta y comenzar a utilizar la plataforma, hacé clic en el botón:</p>
<table role="presentation" cellpadding="0" cellspacing="0"><tr><td bgcolor="#0A6D64" style="background-color:#0A6D64;">
<a href="{safe_url}" style="display:inline-block;padding:12px 24px;border:1px solid #0A6D64;color:#FFFCF4;font-weight:600;text-decoration:none;">Verificá tu correo</a>
</td></tr></table>
<p style="margin-top:24px;">Si el botón no funciona, copiá y pegá este enlace en tu navegador:</p>
<p style="overflow-wrap:anywhere;word-break:break-all;"><a href="{safe_url}" style="color:#0A6D64;text-decoration:underline;">{safe_url}</a></p>
</td></tr>
<tr><td style="padding:20px 24px;background-color:#FBF7EC;border-top:1px solid #F2ECDC;font-size:13px;">
<p style="margin:0 0 8px;">KoiCloud · PaaS de datos</p>
<p style="margin:0 0 8px;">Este enlace vence en 24 horas.</p>
<p style="margin:0;">Si no solicitaste esta cuenta, podés ignorar este mensaje.</p>
</td></tr></table>
</td></tr></table>
</body>
</html>"""
    return text, html


def _render_reset_password(context: dict[str, Any]) -> tuple[str, str]:
    email = str(context["email"])
    url = str(context["url"])

    text = (
        f"Hola,\n\n"
        f"Recibimos una solicitud para restablecer la contraseña de tu cuenta ({email}) en KoiCloud.\n"
        f"Para definir tu nueva contraseña, visita el siguiente enlace:\n\n"
        f"{url}\n\n"
        f"Este enlace vence en 1 hora y es de un solo uso.\n"
        f"Si no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual continuará segura.\n"
    )

    safe_email = escape(email, quote=True)
    safe_url = escape(url, quote=True)
    text += "\nKoiCloud · PaaS de datos\n"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Restablecé tu contraseña</title></head>
<body style="margin:0;padding:0;background-color:#F2ECDC;color:#14211F;font-family:Verdana,sans-serif;line-height:1.6;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F2ECDC;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background-color:#FFFCF4;border-top:4px solid #0A6D64;">
<tr><td style="padding:24px;border-bottom:1px solid #F2ECDC;">
{_email_logo_img()}
<span style="font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:600;vertical-align:middle;">KoiCloud</span>
</td></tr>
<tr><td style="padding:24px;">
<h1 style="margin:0 0 20px;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:600;">Restablecé tu contraseña</h1>
<p>Hola,</p>
<p>Recibimos una solicitud para restablecer la contraseña de tu cuenta (<strong>{safe_email}</strong>) en KoiCloud.</p>
<p>Para definir tu nueva contraseña, haz clic en el botón:</p>
<table role="presentation" cellpadding="0" cellspacing="0"><tr><td bgcolor="#0A6D64" style="background-color:#0A6D64;">
<a href="{safe_url}" style="display:inline-block;padding:12px 24px;border:1px solid #0A6D64;color:#FFFCF4;font-weight:600;text-decoration:none;">Restablecé tu contraseña</a>
</td></tr></table>
<p style="margin-top:24px;">Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
<p style="overflow-wrap:anywhere;word-break:break-all;"><a href="{safe_url}" style="color:#0A6D64;text-decoration:underline;">{safe_url}</a></p>
</td></tr>
<tr><td style="padding:20px 24px;background-color:#FBF7EC;border-top:1px solid #F2ECDC;font-size:13px;">
<p style="margin:0 0 8px;">KoiCloud · PaaS de datos</p>
<p style="margin:0 0 8px;">Este enlace vence en 1 hora y es de un solo uso.</p>
<p style="margin:0;">Si no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual continuará segura.</p>
</td></tr></table>
</td></tr></table>
</body>
</html>"""
    return text, html


def _render_invoice_issued(context: dict[str, Any]) -> tuple[str, str]:
    code = str(context["code"])
    total = str(context["total"])

    text = (
        f"Hola,\n\n"
        f"Tu factura con código {code} por un total de {total} ha sido emitida.\n"
        f"Puedes consultar el detalle completo y descargar tu comprobante desde el panel de facturación en KoiCloud.\n\n"
        f"Gracias por confiar en KoiCloud.\n"
    )

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head><meta charset=\"utf-8\"><title>Tu factura de KoiCloud</title></head>\n"
        "<body>\n"
        "  <h2>Tu factura de KoiCloud</h2>\n"
        "  <p>Hola,</p>\n"
        f"  <p>Tu factura con código <strong>{code}</strong> por un total de <strong>{total}</strong> ha sido emitida.</p>\n"
        "  <p>Puedes consultar el detalle completo y descargar tu comprobante desde el panel de facturación en KoiCloud.</p>\n"
        "  <p>Gracias por confiar en KoiCloud.</p>\n"
        "</body>\n"
        "</html>"
    )
    return text, html


def _render_subscription_canceled(context: dict[str, Any]) -> tuple[str, str]:
    plan = str(context["plan"])
    ends_on = str(context["ends_on"])

    text = (
        f"Hola,\n\n"
        f"Hemos programado la cancelación de tu suscripción al plan {plan}.\n"
        f"Tu servicio permanecerá activo hasta el final del período actual: {ends_on}.\n\n"
        f"Si deseas renovar o reactivar tu plan antes de esa fecha, puedes hacerlo desde tu panel de control.\n"
    )

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head><meta charset=\"utf-8\"><title>Cancelación programada</title></head>\n"
        "<body>\n"
        "  <h2>Cancelación programada</h2>\n"
        "  <p>Hola,</p>\n"
        f"  <p>Hemos programado la cancelación de tu suscripción al plan <strong>{plan}</strong>.</p>\n"
        f"  <p>Tu servicio permanecerá activo hasta el final del período actual: <strong>{ends_on}</strong>.</p>\n"
        "  <p>Si deseas renovar o reactivar tu plan antes de esa fecha, puedes hacerlo desde tu panel de control.</p>\n"
        "</body>\n"
        "</html>"
    )
    return text, html


_RENDERERS = {
    "verify_email": _render_verify_email,
    "reset_password": _render_reset_password,
    "invoice_issued": _render_invoice_issued,
    "subscription_canceled": _render_subscription_canceled,
}


def render_template(template: str, context: dict[str, Any]) -> RenderedEmail:
    """Validate template name and context keys, then render subject, text and HTML bodies."""
    if template not in TEMPLATES:
        allowed = ", ".join(TEMPLATES.keys())
        raise ValueError(f"Unknown template '{template}'. Allowed templates: {allowed}")

    meta = TEMPLATES[template]
    required_keys = meta["required_context"]
    missing = [k for k in required_keys if k not in context or context[k] is None or str(context[k]).strip() == ""]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            f"Missing required context keys [{missing_str}] for template '{template}'."
        )

    renderer = _RENDERERS[template]
    text_body, html_body = renderer(context)
    return RenderedEmail(
        template=template,
        subject=meta["subject"],
        text_body=text_body,
        html_body=html_body,
    )
