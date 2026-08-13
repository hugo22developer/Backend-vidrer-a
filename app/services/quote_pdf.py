"""Hoja de cotización formal (HTML -> PDF vía WeasyPrint).

Genera un documento A4 con branding, tabla maestra de partidas y un boceto
técnico SVG dinámico por partida (corrediza, abatible, proyectante, fijo y
mueble/vitrina), más las notas y condiciones comerciales.
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from jinja2 import BaseLoader, Environment

from app.models.entities import Quote

# Paleta industrial-elegante
_STROKE = "#334155"
_ACCENT = "#0891b2"
_FILL = "#f1f5f9"
_GLASS = "#e6f3fc"
_HATCH = "#94a3b8"
_LABEL = "#475569"

_CANVAS_W = 200
_CANVAS_H = 120
_AREA_X = 20
_AREA_Y = 18
_AREA_W = 172
_AREA_H = 84

_MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def format_money(value: Decimal | int | float) -> str:
    return f"${Decimal(value):,.2f}"


def format_date(value: datetime) -> str:
    dt = value.astimezone() if value.tzinfo else value
    return f"{dt.day} de {_MONTHS[dt.month - 1]} de {dt.year}"


def format_number(value: Decimal | int | float) -> str:
    return f"{float(value):g}"


# ---------------------------------------------------------------------------
# Bocetos técnicos (SVG)
# ---------------------------------------------------------------------------


def _sketch_kind(item: dict[str, Any]) -> str:
    label = str(item.get("subtype") or "").lower()
    if "corrediz" in label:
        return "sliding"
    if "abatible" in label:
        return "hinged"
    if "proyectante" in label:
        return "projecting"
    if "fijo" in label or "mampara" in label:
        return "fixed"
    if item.get("category") == "mueble":
        return "cabinet"
    return "sliding"


def _arrowhead(x: float, y: float, angle_deg: float, size: float = 4.5) -> str:
    a = math.radians(angle_deg)
    tip = (x + size * math.cos(a), y + size * math.sin(a))
    p1 = (x + size * math.cos(a + math.radians(160)), y + size * math.sin(a + math.radians(160)))
    p2 = (x + size * math.cos(a - math.radians(160)), y + size * math.sin(a - math.radians(160)))
    pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in (tip, p1, p2))
    return f'<polygon points="{pts}" fill="{_STROKE}"/>'


def _dbl_arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    line = (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{_STROKE}" stroke-width="1"/>'
    )
    return line + _arrowhead(x2, y2, 0) + _arrowhead(x1, y1, 180)


def _arc_points(cx: float, cy: float, r: float, start_deg: float, end_deg: float, steps: int = 16) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _polyline(points: list[tuple[float, float]], stroke: str = _ACCENT, width: float = 1.2, fill: str = "none", dash: str = "") -> str:
    data = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{data}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"{dash_attr}/>'


def _hinge_circle(cx: float, cy: float) -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.9" fill="{_ACCENT}"/>'


def _body(kind: str, x: float, y: float, rw: float, rh: float, cx: float, cy: float) -> str:
    panel = f'<rect x="{x + 4:.1f}" y="{y + 3:.1f}" width="{rw - 8:.1f}" height="{rh - 6:.1f}" fill="#ffffff" stroke="{_ACCENT}" stroke-width="1"/>'

    if kind == "sliding":
        p1 = f'<rect x="{x + 2:.1f}" y="{y + 2:.1f}" width="{rw * 0.54:.1f}" height="{rh - 4:.1f}" fill="none" stroke="{_ACCENT}" stroke-width="1"/>'
        p2 = f'<rect x="{x + rw * 0.46:.1f}" y="{y + 2:.1f}" width="{rw * 0.54:.1f}" height="{rh - 4:.1f}" fill="none" stroke="{_HATCH}" stroke-width="1"/>'
        h1 = f'<line x1="{x + rw * 0.27:.1f}" y1="{y + rh * 0.44:.1f}" x2="{x + rw * 0.27:.1f}" y2="{y + rh * 0.56:.1f}" stroke="{_ACCENT}" stroke-width="1.6"/>'
        h2 = f'<line x1="{x + rw * 0.73:.1f}" y1="{y + rh * 0.44:.1f}" x2="{x + rw * 0.73:.1f}" y2="{y + rh * 0.56:.1f}" stroke="{_ACCENT}" stroke-width="1.6"/>'
        return p1 + p2 + h1 + h2 + _dbl_arrow(x + rw * 0.12, y + rh * 0.92, x + rw * 0.88, y + rh * 0.92)

    if kind == "hinged":
        arc = _arc_points(x + 4, y + rh / 2, rw - 6, -58, 58)
        wedge = [(x + 4, y + rh / 2)] + arc + [(x + 4, y + rh / 2)]
        return (
            panel
            + _polyline(wedge, stroke=_ACCENT, fill="rgba(8,145,178,0.08)", dash="3,2")
            + _arrowhead(arc[len(arc) // 2][0], arc[len(arc) // 2][1], 90)
            + _hinge_circle(x + 4, y + rh * 0.25)
            + _hinge_circle(x + 4, y + rh * 0.75)
        )

    if kind == "projecting":
        arc = _arc_points(cx, y + rh - 4, rh - 8, -140, -40)
        wedge = [(cx, y + rh - 4)] + arc + [(cx, y + rh - 4)]
        return (
            panel
            + _polyline(wedge, stroke=_ACCENT, fill="rgba(8,145,178,0.08)", dash="3,2")
            + _arrowhead(arc[-1][0], arc[-1][1], 50)
            + _hinge_circle(x + rw * 0.35, y + rh - 4)
            + _hinge_circle(x + rw * 0.65, y + rh - 4)
        )

    if kind == "fixed":
        brace = (
            f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + rw:.1f}" y2="{y + rh:.1f}" stroke="{_HATCH}" stroke-width="1" stroke-dasharray="4,2"/>'
            f'<line x1="{x:.1f}" y1="{y + rh:.1f}" x2="{x + rw:.1f}" y2="{y:.1f}" stroke="{_HATCH}" stroke-width="1" stroke-dasharray="4,2"/>'
        )
        return f'<rect x="{x + 3:.1f}" y="{y + 3:.1f}" width="{rw - 6:.1f}" height="{rh - 6:.1f}" fill="none" stroke="{_ACCENT}" stroke-width="1"/>{brace}'

    # cabinet / vitrina
    divider = f'<line x1="{cx:.1f}" y1="{y + 2:.1f}" x2="{cx:.1f}" y2="{y + rh - 2:.1f}" stroke="{_STROKE}" stroke-width="1"/>'
    shelf = f'<line x1="{x + 2:.1f}" y1="{y + rh * 0.3:.1f}" x2="{x + rw - 2:.1f}" y2="{y + rh * 0.3:.1f}" stroke="{_HATCH}" stroke-width="1" stroke-dasharray="4,2"/>'
    handle1 = f'<line x1="{cx - 4:.1f}" y1="{y + rh * 0.62:.1f}" x2="{cx - 4:.1f}" y2="{y + rh * 0.72:.1f}" stroke="{_ACCENT}" stroke-width="1.6"/>'
    handle2 = f'<line x1="{cx + 4:.1f}" y1="{y + rh * 0.62:.1f}" x2="{cx + 4:.1f}" y2="{y + rh * 0.72:.1f}" stroke="{_ACCENT}" stroke-width="1.6"/>'
    return divider + shelf + handle1 + handle2


_KIND_LABELS = {
    "sliding": "CORREDIZA · 2 HOJAS",
    "hinged": "ABATIBLE · SENTIDO DE APERTURA",
    "projecting": "PROYECTANTE",
    "fixed": "FIJO / MAMPARA",
    "cabinet": "VITRINA / CLÓSET",
}


def build_item_sketch(item: dict[str, Any]) -> str:
    w = float(item.get("width_cm") or 0)
    h = float(item.get("height_cm") or 0)
    if w <= 0:
        w = 100.0
    if h <= 0:
        h = 100.0

    scale = min(_AREA_W / w, _AREA_H / h)
    rw = w * scale
    rh = h * scale
    x = _AREA_X + (_AREA_W - rw) / 2
    y = _AREA_Y + (_AREA_H - rh) / 2
    cx = x + rw / 2
    cy = y + rh / 2

    kind = _sketch_kind(item)
    w_label = f"{w:g} cm"
    h_label = f"{h:g} cm"

    dims = (
        f'<line x1="{x:.1f}" y1="{_AREA_Y - 7:.1f}" x2="{x + rw:.1f}" y2="{_AREA_Y - 7:.1f}" stroke="{_LABEL}" stroke-width="0.8"/>'
        + _arrowhead(x + rw, _AREA_Y - 7, 0, 3.4)
        + _arrowhead(x, _AREA_Y - 7, 180, 3.4)
        + f'<text x="{cx:.1f}" y="{_AREA_Y - 12:.1f}" text-anchor="middle" font-size="7" fill="{_LABEL}" font-family="sans-serif">{w_label}</text>'
        + f'<line x1="{_AREA_X - 7:.1f}" y1="{y:.1f}" x2="{_AREA_X - 7:.1f}" y2="{y + rh:.1f}" stroke="{_LABEL}" stroke-width="0.8"/>'
        + _arrowhead(_AREA_X - 7, y + rh, 90, 3.4)
        + _arrowhead(_AREA_X - 7, y, -90, 3.4)
        + f'<text transform="translate({_AREA_X - 14:.1f},{cy:.1f}) rotate(-90)" text-anchor="middle" font-size="7" fill="{_LABEL}" font-family="sans-serif">{h_label}</text>'
    )

    frame = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="{_FILL}" stroke="{_STROKE}" stroke-width="1.5"/>'
        + f'<rect x="{x + 2:.1f}" y="{y + 2:.1f}" width="{rw - 4:.1f}" height="{rh - 4:.1f}" fill="{_GLASS}" stroke="none"/>'
    )

    title = (
        f'<text x="{_CANVAS_W / 2:.0f}" y="{_CANVAS_H - 6:.0f}" text-anchor="middle" font-size="7.5" '
        f'fill="{_STROKE}" font-family="sans-serif" font-weight="bold" letter-spacing="1">{_KIND_LABELS[kind]}</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_CANVAS_W} {_CANVAS_H}" '
        f'width="100%" height="100%" role="img" aria-label="Boceto técnico de {_KIND_LABELS[kind]}">'
        + dims + frame + _body(kind, x, y, rw, rh, cx, cy) + title
        + "</svg>"
    )


# ---------------------------------------------------------------------------
# Plantilla HTML (Jinja2)
# ---------------------------------------------------------------------------

_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Cotización {{ folio }}</title>
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 22mm 16mm;
    @bottom-center {
      content: "Página " counter(page) " de " counter(pages);
      font-family: 'Inter', 'DejaVu Sans', sans-serif;
      font-size: 8pt;
      color: #64748b;
    }
    @bottom-right {
      content: "{{ folio }} · {{ fecha_emision }}";
      font-family: 'Inter', 'DejaVu Sans', sans-serif;
      font-size: 8pt;
      color: #94a3b8;
    }
    @bottom-left {
      content: "El Cercho · hola@elcercho.mx · +52 55 0000 0000";
      font-family: 'Inter', 'DejaVu Sans', sans-serif;
      font-size: 8pt;
      color: #94a3b8;
    }
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', 'DejaVu Sans', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    color: #1e293b;
    font-size: 10pt;
    margin: 0;
  }
  h1, h2, h3 { margin: 0; font-weight: 700; }
  p { margin: 0; }

  .sheet { width: 100%; }

  /* ---------- Encabezado / branding ---------- */
  .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #0891b2; padding-bottom: 12px; }
  .brand { display: flex; gap: 12px; align-items: center; }
  .brand .logo { width: 44px; height: 44px; flex: 0 0 44px; }
  .brand-name { font-size: 16pt; font-weight: 800; letter-spacing: -0.02em; color: #0f172a; }
  .brand-tag { font-size: 8pt; color: #64748b; letter-spacing: 0.08em; text-transform: uppercase; }
  .brand-contact { font-size: 8.5pt; color: #475569; margin-top: 3px; }
  .meta { text-align: right; }
  .meta .doc-type { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.18em; color: #94a3b8; }
  .meta .folio { font-size: 14pt; font-weight: 800; color: #0891b2; margin-top: 2px; }
  .meta .dates { font-size: 8.5pt; color: #475569; margin-top: 4px; }

  /* ---------- Cliente ---------- */
  .client-block { display: flex; gap: 24px; margin-top: 14px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; }
  .client-box { flex: 1; }
  .client-box .k { font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.14em; color: #94a3b8; margin-bottom: 3px; }
  .client-box .v { font-size: 10pt; color: #1e293b; }
  .client-box .v.muted { color: #64748b; font-size: 9pt; }

  /* ---------- Tabla maestra ---------- */
  .section-title { font-size: 10pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; color: #0891b2; margin: 16px 0 8px; }
  table.items { width: 100%; border-collapse: collapse; table-layout: fixed; }
  table.items thead th {
    background: #0f172a; color: #ffffff; font-size: 7.5pt; text-transform: uppercase;
    letter-spacing: 0.08em; padding: 7px 6px; text-align: left; border: 1px solid #0f172a;
  }
  table.items tbody td { border: 1px solid #e2e8f0; padding: 8px 6px; vertical-align: top; font-size: 9pt; }
  table.items tbody tr { break-inside: avoid; page-break-inside: avoid; }
  td.id { text-align: center; font-weight: 700; color: #475569; }
  td.dim, td.qty, td.price, td.total { text-align: right; font-family: 'DejaVu Sans', monospace; font-size: 9pt; }
  td.qty, td.dim { text-align: center; }
  .item-name { font-weight: 700; font-size: 9.5pt; color: #0f172a; }
  .spec { color: #475569; font-size: 8.5pt; margin-top: 3px; line-height: 1.5; }
  .spec b { color: #334155; }
  .inner { display: table; width: 100%; border-collapse: collapse; }
  .inner .col { display: table-cell; vertical-align: top; }
  .inner .col-desc { padding-right: 8px; }
  .inner .col-svg { width: 150px; }
  .col-svg svg { display: block; }

  /* ---------- Totales ---------- */
  .totals { margin-top: 12px; margin-left: auto; width: 240px; }
  .totals .row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 9.5pt; color: #475569; }
  .totals .row.total { border-top: 2px solid #0f172a; margin-top: 4px; padding-top: 8px; font-weight: 800; color: #0f172a; font-size: 12pt; }

  /* ---------- Notas y condiciones ---------- */
  .conditions { margin-top: 20px; border-top: 2px solid #0891b2; padding-top: 10px; }
  .conditions .section-title { margin-top: 0; }
  .cond-grid { display: table; width: 100%; border-collapse: collapse; }
  .cond-cell { display: table-cell; width: 50%; padding: 6px 12px 6px 0; vertical-align: top; }
  .cond-cell h3 { font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.08em; color: #0891b2; margin-bottom: 3px; }
  .cond-cell p { font-size: 8.5pt; color: #475569; line-height: 1.5; }
  .foot-note { margin-top: 14px; font-size: 7.5pt; color: #94a3b8; text-align: center; }
</style>
</head>
<body>
  <div class="sheet">

    <div class="header">
      <div class="brand">
        <svg class="logo" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="1" y="1" width="24" height="24" rx="5" stroke="#0891b2" stroke-width="1.4"/>
          <path d="M9 1V25M17 1V25" stroke="#94a3b8" stroke-width="1.2"/>
          <path d="M1 13H25" stroke="#94a3b8" stroke-width="1.2" opacity="0.5"/>
        </svg>
        <div>
          <p class="brand-name">El Cercho</p>
          <p class="brand-tag">Carpintería de Aluminio y Vidrio</p>
          <p class="brand-contact">Parque Industrial, McAllen / Reynosa<br/>hola@elcercho.mx · +52 55 0000 0000</p>
        </div>
      </div>
      <div class="meta">
        <p class="doc-type">Cotización formal</p>
        <p class="folio">{{ folio }}</p>
        <p class="dates">Emitida: {{ fecha_emision }}</p>
        <p class="dates">Vigente hasta: {{ fecha_vigencia }}</p>
      </div>
    </div>

    <div class="client-block">
      <div class="client-box">
        <p class="k">Cliente</p>
        <p class="v">{{ cliente_nombre }}</p>
        <p class="v muted">{{ cliente_telefono }}</p>
        <p class="v muted">{{ cliente_email }}</p>
      </div>
      <div class="client-box">
        <p class="k">Proyecto / Dirección de obra</p>
        <p class="v muted">{{ cliente_direccion or "—" }}</p>
        <p class="v muted">C.P. {{ cliente_cp or "—" }}</p>
      </div>
    </div>

    <div class="section-title">Resumen de partidas</div>
    <table class="items">
      <thead>
        <tr>
          <th style="width:6%">#</th>
          <th style="width:44%">Descripción y especificaciones</th>
          <th style="width:12%">Medidas (cm)</th>
          <th style="width:8%">Cant.</th>
          <th style="width:15%">P. Unitario</th>
          <th style="width:15%">Total</th>
        </tr>
      </thead>
      <tbody>
        {% for item in partidas %}
        <tr>
          <td class="id">{{ item.indice }}</td>
          <td>
            <p class="item-name">{{ item.producto }}</p>
            <table class="inner">
              <tr>
                <td class="col col-desc">
                  <p class="spec"><b>Área:</b> {{ item.area_m2 }} m² · <b>Cant. mínima facturable:</b> {{ item.area_min }} m²</p>
                  <p class="spec"><b>Sistema:</b> {{ item.linea }}</p>
                  <p class="spec"><b>Color / Acabado:</b> {{ item.acabado }}</p>
                  <p class="spec"><b>Vidrio:</b> {{ item.vidrio }}</p>
                  <p class="spec"><b>Herrajes:</b> {{ item.herrajes }}</p>
                </td>
                <td class="col col-svg">{{ item.boceto | safe }}</td>
              </tr>
            </table>
          </td>
          <td class="dim">{{ item.ancho }} × {{ item.alto }}</td>
          <td class="qty">{{ item.cantidad }}</td>
          <td class="price">{{ item.precio_unitario }}</td>
          <td class="total">{{ item.total }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <div class="totals">
      <div class="row"><span>Subtotal</span><span>{{ subtotal }}</span></div>
      <div class="row"><span>IVA ({{ iva_porcentaje }}%)</span><span>{{ iva }}</span></div>
      <div class="row total"><span>Total</span><span>{{ total }}</span></div>
    </div>

    <div class="conditions">
      <div class="section-title">Notas y condiciones comerciales</div>
      <table class="cond-grid">
        <tr>
          <td class="cond-cell">
            <h3>Tiempo de fabricación</h3>
            <p>Fabricación en 2 a 3 semanas a partir de la confirmación del anticipo. La instalación se agenda en sitio según la disponibilidad de la obra.</p>
          </td>
          <td class="cond-cell">
            <h3>Condiciones de pago</h3>
            <p>Anticipo del 50% para iniciar fabricación y saldo contra entrega e instalación. Precios en pesos mexicanos (MXN).</p>
          </td>
        </tr>
        <tr>
          <td class="cond-cell">
            <h3>Garantía</h3>
            <p>12 meses contra defectos de fabricación e instalación. Garantía de herrajes conforme al fabricante. No se cubren daños por mal uso, manipulación o agentes externos.</p>
          </td>
          <td class="cond-cell">
            <h3>Exclusiones</h3>
            <p>No incluye trabajos de albañilería, pintura, acabados de muros ni adecuaciones necesarias para el ajuste de marcos. Medidas verificadas en sitio al momento de la instalación.</p>
          </td>
        </tr>
        <tr>
          <td class="cond-cell">
            <h3>Vigencia</h3>
            <p>Cotización vigente por 7 días naturales a partir de la fecha de emisión. Los precios quedan sujetos a verificación de medidas en sitio.</p>
          </td>
          <td class="cond-cell">
            <h3>Nota</h3>
            <p>Este documento es una propuesta comercial y no constituye un contrato. Cualquier cambio de especificaciones o medidas deberá autorizarse por escrito.</p>
          </td>
        </tr>
      </table>
    </div>

    <p class="foot-note">El Cercho · Carpintería de Aluminio y Vidrio · hola@elcercho.mx · +52 55 0000 0000</p>
  </div>
</body>
</html>
"""

_jinja = Environment(loader=BaseLoader())


def build_quote_html(context: dict[str, Any]) -> str:
    template = _jinja.from_string(_TEMPLATE)
    return template.render(**context)


# ---------------------------------------------------------------------------
# Contexto a partir de una cotización persistida
# ---------------------------------------------------------------------------


def quote_to_context(quote: Quote) -> dict[str, Any]:
    created = quote.created_at or datetime.now(UTC)
    partidas: list[dict[str, Any]] = []
    for indice, item in enumerate(quote.items, start=1):
        herrajes = ", ".join(item.herraje_labels) if item.herraje_labels else "—"
        item_dict: dict[str, Any] = {
            "category": item.category_id,
            "subtype": item.subtype_label,
        }
        partidas.append(
            {
                "indice": indice,
                "producto": f"{item.category_label} · {item.subtype_label}",
                "area_m2": format_number(item.area_m2),
                "area_min": format_number(item.billable_area_m2),
                "linea": item.linea_label,
                "acabado": item.acabado_label,
                "vidrio": item.vidrio_label,
                "herrajes": herrajes,
                "ancho": format_number(item.width_cm),
                "alto": format_number(item.height_cm),
                "cantidad": item.quantity,
                "precio_unitario": format_money(item.unit_price),
                "total": format_money(item.subtotal),
                "boceto": build_item_sketch(item_dict),
            }
        )

    return {
        "folio": quote.folio,
        "fecha_emision": format_date(created),
        "fecha_vigencia": format_date(created + timedelta(days=7)),
        "cliente_nombre": quote.client_name,
        "cliente_telefono": quote.client_phone,
        "cliente_email": quote.client_email,
        "cliente_direccion": quote.client_address,
        "cliente_cp": quote.client_postal_code,
        "iva_porcentaje": format_number(quote.iva_percent),
        "subtotal": format_money(quote.subtotal),
        "iva": format_money(quote.iva),
        "total": format_money(quote.total),
        "partidas": partidas,
    }


def render_quote_pdf(quote: Quote) -> bytes:
    from weasyprint import HTML

    context = quote_to_context(quote)
    html = build_quote_html(context)
    return HTML(string=html).write_pdf()
