from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.entities import (
    AcabadoAluminio,
    AdminUser,
    BlogPost,
    Category,
    Herraje,
    Insumo,
    LineaAluminio,
    Product,
    TipoVidrio,
)


async def seed_initial_data(session: AsyncSession) -> None:
    exists = await session.scalar(select(AdminUser.id).limit(1))
    if exists:
        return

    users = [
        AdminUser(id="u1", name="Hugo Martínez", email=settings.seed_admin_email, role="Super Admin", status="active", created_at=date(2024, 2, 10), password_hash=hash_password(settings.seed_admin_password)),
        AdminUser(id="u2", name="Renata Solís", email="renata@elcercho.mx", role="Editor de Contenido", status="active", created_at=date(2024, 6, 3), password_hash=hash_password("Editor123!")),
        AdminUser(id="u3", name="Iván Cortez", email="ivan@elcercho.mx", role="Ventas", status="active", created_at=date(2024, 9, 21), password_hash=hash_password("Ventas123!")),
        AdminUser(id="u4", name="Paola Nuño", email="paola@elcercho.mx", role="Ventas", status="inactive", created_at=date(2023, 11, 14), password_hash=hash_password("Ventas123!")),
    ]
    categories = [
        Category(slug="canceles-de-bano", label="Canceles de Baño", short_label="Canceles de baño", eyebrow="Línea Canceles", hero_description="Vidrio templado de 8mm y herrajes minimalistas: cero filtraciones, cero ruido en los rieles.", hero_specs=["Vidrio 8mm Templado", "Herrajes ocultos", "Instalación en 1 día"], accent="from-glass-400/25 via-graphite-800 to-graphite-900"),
        Category(slug="ventanas-puertas", label="Ventanas y Puertas", short_label="Ventanas y puertas", eyebrow="Línea Ventanería", hero_description="Sistemas Serie 3 con cámara de aire DVH: el balance entre entrada de luz y control térmico real.", hero_specs=["Perfil Serie 3", "DVH 24mm", "Doble sello EPDM"], accent="from-amber-500/20 via-graphite-800 to-graphite-900"),
        Category(slug="barandales-portones", label="Barandales y Portones", short_label="Barandales y portones", eyebrow="Línea Exteriores", hero_description="Estructura de aluminio y vidrio pensada para exteriores: resistencia a intemperie sin perder la línea minimalista.", hero_specs=["Aluminio Reforzado", "Vidrio 10mm", "Anticorrosivo"], accent="from-steel-400/25 via-graphite-800 to-graphite-900"),
        Category(slug="muebles-a-medida", label="Muebles a Medida", short_label="Muebles a medida", eyebrow="Línea Interiores", hero_description="Aluminio anodizado y cristal para mobiliario interior: la misma precisión de taller aplicada a piezas de uso diario.", hero_specs=["Aluminio + Cristal", "Acabado anodizado", "Diseño a medida"], accent="from-glass-300/20 via-graphite-800 to-graphite-900"),
    ]
    products = [
        Product(id="p1", slug="corredizo-minimalista", category_slug="canceles-de-bano", title="Cancel Corredizo Minimalista", description="Dos hojas sobre riel superior de aluminio anodizado, sin marco inferior visible.", image="/products/canceles-de-bano/corredizo-minimalista.jpg", specs=["8mm Templado", "Riel superior", "Anodizado mate"], status="active", consultations=214),
        Product(id="p2", slug="abatible-frameless", category_slug="canceles-de-bano", title="Cancel Abatible Frameless", description="Una sola hoja sin marco perimetral, sostenida por bisagras de piso a techo.", image="/products/canceles-de-bano/abatible-frameless.jpg", specs=["10mm Templado", "Bisagra piso-techo"], status="active", consultations=98),
        Product(id="p3", slug="fijo-panoramico", category_slug="canceles-de-bano", title="Cancel Fijo Panorámico", description="Panel fijo de gran formato para regaderas abiertas, con sello inferior antiderrame.", image="/products/canceles-de-bano/fijo-panoramico.jpg", specs=["8mm Templado", "Sello antiderrame"], status="draft", consultations=41),
        Product(id="p4", slug="ventana-corrediza-serie-3", category_slug="ventanas-puertas", title="Ventana Corrediza Serie 3", description="Dos o tres hojas sobre riel de rodamiento silencioso, con cámara DVH.", image="/products/ventanas-puertas/ventana-corrediza.jpg", specs=["Serie 3", "DVH 24mm", "2-3 hojas"], status="active", consultations=356),
        Product(id="p5", slug="puerta-corrediza-panoramica", category_slug="ventanas-puertas", title="Puerta Corrediza Panorámica", description="Vanos de gran formato para conectar interior y jardín, riel embebido a piso.", image="/products/ventanas-puertas/puerta-corrediza.jpg", specs=["Serie 4", "Riel embebido"], status="active", consultations=187),
        Product(id="p6", slug="barandal-vidrio-templado", category_slug="barandales-portones", title="Barandal de Vidrio Templado", description="Paneles de vidrio templado de 10mm con fijación puntual de acero inoxidable.", image="/products/barandales-portones/barandal-vidrio.jpg", specs=["10mm Templado", "Fijación puntual", "Inox 304"], status="active", consultations=132),
        Product(id="p7", slug="porton-corredizo-automatizado", category_slug="barandales-portones", title="Portón Corredizo Automatizado", description="Estructura de aluminio reforzado sobre riel de piso, compatible con motor.", image="/products/barandales-portones/porton-corredizo.jpg", specs=["Aluminio reforzado", "Listo para motor"], status="active", consultations=76),
        Product(id="p8", slug="closet-puertas-cristal", category_slug="muebles-a-medida", title="Clóset con Puertas de Cristal", description="Sistema corredizo o abatible con puertas de cristal esmerilado o transparente.", image="/products/muebles-a-medida/closet-cristal.jpg", specs=["Cristal esmerilado", "Marco delgado"], status="draft", consultations=29),
    ]
    posts = [
        BlogPost(id="b1", slug="fachadas-muro-cortina", category="Tendencias", title="Fachadas de muro cortina: la nueva piel de la arquitectura comercial", excerpt="Por qué cada vez más despachos eligen envolventes de vidrio estructural sobre mampostería tradicional.", content="Contenido completo del artículo sobre fachadas de muro cortina...", accent="from-glass-400/30 to-graphite-900", status="published", date=date(2026, 6, 2), views=1840),
        BlogPost(id="b2", slug="mantenimiento-canceles-bano", category="Mantenimiento", title="Cómo alargar la vida útil de tus canceles de baño", excerpt="Limpieza, lubricación de rieles y señales tempranas de desgaste en herrajes y sellos.", content="Contenido completo del artículo sobre mantenimiento de canceles...", accent="from-amber-500/25 to-graphite-900", status="published", date=date(2026, 5, 18), views=2960),
        BlogPost(id="b3", slug="dvh-vs-vidrio-simple", category="Guía técnica", title="DVH vs. vidrio simple: qué gana realmente tu factura eléctrica", excerpt="Comparativa real de aislamiento térmico entre sistemas de doble y triple acristalamiento.", content="Contenido completo del artículo sobre DVH vs vidrio simple...", accent="from-steel-400/25 to-graphite-900", status="draft", date=date(2026, 7, 10), views=410),
    ]
    insumos = [
        Insumo(id="i1", sku="ALU-PRF-001", nombre="Riel superior Serie 3", categoria="Perfiles de Aluminio", unidad="m", costo_unitario=186, factor_desperdicio=8, notas="Proveedor: Extrusiones del Norte", ultima_modificacion=date(2026, 7, 28), estado="active", pending_review=False),
        Insumo(id="i2", sku="ALU-PRF-002", nombre="Jamba Serie 3", categoria="Perfiles de Aluminio", unidad="m", costo_unitario=164, factor_desperdicio=8, notas="", ultima_modificacion=date(2026, 7, 28), estado="active", pending_review=False),
        Insumo(id="i5", sku="VID-CRI-001", nombre="Vidrio Templado 6mm", categoria="Cristales / Vidrios", unidad="m²", costo_unitario=520, factor_desperdicio=10, notas="Proveedor: Cristales Cortés", ultima_modificacion=date(2026, 7, 15), estado="active", pending_review=False),
        Insumo(id="i8", sku="HER-ACC-001", nombre="Manija tipo H acero inoxidable", categoria="Herrajes y Accesorios", unidad="pza", costo_unitario=245, factor_desperdicio=2, notas="", ultima_modificacion=date(2026, 6, 30), estado="active", pending_review=False),
        Insumo(id="i11", sku="CON-SEL-001", nombre="Silicón estructural (cartucho)", categoria="Consumibles / Selladores", unidad="pza", costo_unitario=145, factor_desperdicio=15, notas="", ultima_modificacion=date(2026, 7, 2), estado="active", pending_review=False),
    ]
    quote_config = [
        LineaAluminio(id="tradicional", label="Línea Tradicional / Económica", description="Perfil estándar, ideal para proyectos residenciales con presupuesto ajustado.", factor=950),
        LineaAluminio(id="europea", label="Línea Europea / Pesada", description="Perfil reforzado de mayor calibre, mejor sellado y vida útil en uso intensivo.", factor=1550),
        LineaAluminio(id="ruptura-termica", label="Sistema con Ruptura Térmica", description="Barrera de poliamida que corta el puente térmico - máximo aislamiento.", factor=2250),
        AcabadoAluminio(id="anodizado", label="Anodizado Natural", swatch="#b9bec5", extra=0),
        AcabadoAluminio(id="blanco", label="Blanco", swatch="#f4f5f7", extra=60),
        AcabadoAluminio(id="negro-mate", label="Negro Mate", swatch="#26282b", extra=90),
        AcabadoAluminio(id="madera", label="Tipo Madera", swatch="linear-gradient(135deg,#8a5a34,#5e3b20)", extra=150),
        TipoVidrio(id="crudo", label="Vidrio Crudo Monolítico", spec="4-5mm, económico, sin tratamiento térmico", factor=210),
        TipoVidrio(id="templado-6", label="Templado 6mm", spec="Resistente a impacto, cumple NOM de seguridad", factor=360),
        TipoVidrio(id="templado-9", label="Templado 9mm", spec="Mayor grosor, usado en vanos amplios", factor=520),
        TipoVidrio(id="templado-10", label="Templado 10mm", spec="Para fachadas y paños de gran formato", factor=590),
        TipoVidrio(id="laminado", label="Vidrio Laminado", spec="Dos capas + PVB, seguridad ante rotura", factor=680),
        TipoVidrio(id="dvh", label="Duovent / DVH", spec="Doble vidriado hermético, máximo aislamiento", factor=860),
        Herraje(id="cerradura", label="Cerradura de seguridad", price=480),
        Herraje(id="jaladera-h", label="Jaladera tipo H acero inoxidable", price=390),
        Herraje(id="cierrapuertas", label="Cierrapuertas hidráulico", price=920),
    ]
    session.add_all([*users, *categories, *products, *posts, *insumos, *quote_config])
    await session.commit()

