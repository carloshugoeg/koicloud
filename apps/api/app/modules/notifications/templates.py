from __future__ import annotations

from typing import Any, NamedTuple


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

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head><meta charset=\"utf-8\"><title>Verificá tu correo</title></head>\n"
        "<body>\n"
        "  <h2>Verificá tu correo</h2>\n"
        "  <p>Hola,</p>\n"
        f"  <p>Gracias por registrarte en KoiCloud con el correo <strong>{email}</strong>.</p>\n"
        "  <p>Para verificar tu cuenta y comenzar a utilizar la plataforma, haz clic en el siguiente enlace:</p>\n"
        f"  <p><a href=\"{url}\">{url}</a></p>\n"
        "  <p>Este enlace vence en 24 horas.</p>\n"
        "  <p>Si no solicitaste esta cuenta, puedes ignorar este mensaje.</p>\n"
        "</body>\n"
        "</html>"
    )
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

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"es\">\n"
        "<head><meta charset=\"utf-8\"><title>Restablecé tu contraseña</title></head>\n"
        "<body>\n"
        "  <h2>Restablecé tu contraseña</h2>\n"
        "  <p>Hola,</p>\n"
        f"  <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta (<strong>{email}</strong>) en KoiCloud.</p>\n"
        "  <p>Para definir tu nueva contraseña, haz clic en el siguiente enlace:</p>\n"
        f"  <p><a href=\"{url}\">{url}</a></p>\n"
        "  <p>Este enlace vence en 1 hora y es de un solo uso.</p>\n"
        "  <p>Si no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual continuará segura.</p>\n"
        "</body>\n"
        "</html>"
    )
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
