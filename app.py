from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import unicodedata

import io
from datetime import datetime
from flask import send_file
from reportlab.lib.pagesizes import A6, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5, A6, portrait
from reportlab.lib.units import mm
from extensions import db



app = Flask(__name__)
app.secret_key = "clave-secreta"  # Necesaria para usar session
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
from models import Envoltura, Cliente, PedidoServicio, Pedido
with app.app_context():
    db.create_all()
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/campagne')
def campagne():
    return render_template('campagne.html')


@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        # Guardamos los datos básicos del formulario
        session['acepta'] = request.form.get('consent')
        session['correo'] = request.form.get('correo')
        session['primera_vez'] = request.form.get('first_time')
        session['nombre'] = request.form.get('nombre_apellido')
        session['telefono'] = request.form.get('telefono')
        session['supo'] = request.form.get('source')
        session['regalos'] = int(request.form.get('cantidad'))

        # Limpiamos cualquier dato anterior de envolturas
        session['envolturas'] = []

        # Redirige a la primera pantalla de envoltura
        return redirect(url_for('envoltura', index=1, total=session['regalos']))

    return render_template('formulario.html')



@app.route('/envoltura', methods=['GET', 'POST'])
def envoltura():
    # Recupera datos globales del formulario inicial
    acepta = request.args.get('acepta', session.get('acepta'))
    primera_vez = request.args.get('primera_vez', session.get('primera_vez'))
    supo = request.args.get('supo', session.get('supo'))
    regalos = int(request.args.get('regalos', session.get('regalos', 1)))

    # Guarda en sesión si no están
    session['acepta'] = acepta
    session['primera_vez'] = primera_vez
    session['supo'] = supo
    session['regalos'] = regalos

    # Inicializa lista de envolturas si no existe
    if 'envolturas' not in session:
        session['envolturas'] = []

    # Índice actual del regalo (1 basado)
    index = len(session['envolturas']) + 1
    total = regalos

    # Procesar POST: guardar datos del regalo actual
    if request.method == 'POST':
        data = {
            "descripcion": request.form.get('descripcion'),
            "para": request.form.get('para'),
            "papel": request.form.get('papel'),
            "caja": request.form.get('caja'),
            "liston": request.form.get('liston'),
            "mono": request.form.get('mono'),
            "etiqueta": request.form.get('etiqueta')
        }
        envolturas = session['envolturas']
        envolturas.append(data)
        session['envolturas'] = envolturas

        # Si aún faltan regalos, mostrar el siguiente formulario
        if len(envolturas) < regalos:
            return redirect(url_for('envoltura'))
        else:
            # Si ya llenó todos los regalos, pasar al resumen
            return redirect(url_for('resumen'))

    return render_template('envoltura.html', index=index, total=total)


@app.route('/resumen', methods=['GET', 'POST'])
def resumen():
    acepta = session.get('acepta')
    nombre = session.get('nombre')
    correo = session.get('correo')
    telefono = session.get('telefono')
    primera_vez = session.get('primera_vez')
    supo = session.get('supo')
    regalos = session.get('regalos')
    envolturas = session.get('envolturas', [])

    if request.method == 'POST':
        # Verificar si el cliente ya existe (por teléfono)
        cliente = Cliente.query.filter_by(telefono=telefono).first()

        if not cliente:
            cliente = Cliente(
                nombre=nombre,
                telefono=telefono,
                correo=correo
            )
            db.session.add(cliente)
            db.session.commit()  # Guardamos para obtener su ID

        pedido = Pedido()
        db.session.add(pedido)
        db.session.flush()

        # Guardar los regalos asociados a este cliente
        ids_guardados = []
        for regalo in envolturas:
            nuevo = Envoltura(
                descripcion=regalo["descripcion"],
                para=regalo["para"],
                papel=regalo["papel"],
                liston=regalo["liston"],
                mono=regalo["mono"],
                caja=regalo["caja"],
                etiqueta=regalo["etiqueta"],
                cliente_id=cliente.id,
                estado="Registrado",
                pedido_id=pedido.id
            )
            db.session.add(nuevo)
            db.session.flush()
            ids_guardados.append((nuevo.id, nuevo.descripcion))

        db.session.commit()

        # Limpiar sesión
        session.pop("envolturas", None)
        session.pop("regalos", None)
        session.pop("nombre", None)
        session.pop("telefono", None)

        session['confirmacion_data'] = {
            "nombre": cliente.nombre,
            "telefono": cliente.telefono,
            "ids": ids_guardados
        }


        return redirect(url_for('confirmacion'))

    return render_template('resumen.html',
                           acepta=acepta,
                           primera_vez=primera_vez,
                           supo=supo,
                           regalos=regalos,
                           envolturas=envolturas,
                           nombre=nombre,
                           telefono=telefono)


@app.route('/confirmacion')
def confirmacion():
    data = session.get('confirmacion_data')
    if not data:
        return redirect(url_for('index'))

    return render_template('confirmacion.html', data=data)


@app.route('/marcar_envuelto/<int:envoltura_id>', methods=['POST'])
def marcar_envuelto(envoltura_id):
    envoltura = Envoltura.query.get_or_404(envoltura_id)
    envoltura.estado = "Envuelto"   # Usa exactamente el texto que usas en tu BD
    db.session.commit()
    return redirect(url_for('benevolos'))

@app.route('/benevolos')
def benevolos():
    # Listamos solo envolturas con estado "Aceptado"
    envolturas = Envoltura.query.filter_by(estado="Aceptado").all()
    return render_template('benevolos.html', envolturas=envolturas)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    pedidos = Envoltura.query.all()
    pedidos_registrados = Envoltura.query.filter_by(estado="Registrado").all()
    pedidos_cancelados = Envoltura.query.filter_by(estado="Cancelado").all()
    pedidos_aceptados = Envoltura.query.filter_by(estado="Aceptado").all()
    pedidos_facturados = Envoltura.query.filter_by(estado="Facturado").all()
    pedidos_envueltos = Envoltura.query.filter_by(estado="Envuelto").all()
    ordenes = Pedido.query.all()
    encargado_session = session.get("encargado")
    pedidos_info = []
    for p in ordenes:
        total = len(p.envolturas)
        pendientes = len([e for e in p.envolturas if e.estado not in ("Cancelado", "Facturado")])

        pedidos_info.append({
            "id": p.id,
            "total": total,
            "pendientes": pendientes
        })
    resultados = []
    cliente = None

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        if cliente_id:
            cliente = Cliente.query.filter_by(id=cliente_id).first()
            if cliente:
                resultados = Envoltura.query.filter_by(cliente_id=cliente.id).all()
    print('pedidos_aceptados: ' + str(pedidos_aceptados))
    return render_template( 'admin.html', pedidos_info=pedidos_info, pedidos=pedidos, resultados=resultados, cliente=cliente,
        pedidos_registrados=pedidos_registrados, pedidos_cancelados=pedidos_cancelados,
        pedidos_aceptados=pedidos_aceptados, pedidos_facturados=pedidos_facturados, pedidos_envueltos=pedidos_envueltos,
    encargado_session=encargado_session)


@app.route('/cancelar_pedido/<int:pedido_id>', methods=['POST'])
def cancelar_pedido(pedido_id):
    pedido = Envoltura.query.get(pedido_id)
    if pedido:
        pedido.estado = "Cancelado"
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/procesar_pedido/<int:pedido_id>', methods=['POST'])
def procesar_pedido(pedido_id):
    pedido = Envoltura.query.get(pedido_id)
    if not pedido:
        return "Pedido no encontrado", 404

    data = request.get_json()

    precios = data.get("precios", {})
    comentarios = data.get("comentarios", {})
    encargado = data.get("encargado", "")
    session["encargado"] = encargado
    for servicio, precio in precios.items():
        comentario = comentarios.get(servicio, "")

        registro = PedidoServicio(
            pedido_id=pedido_id,
            servicio=servicio,
            precio=float(precio) if precio else None,
            comentario=comentario
        )
        db.session.add(registro)

    pedido.encargado = encargado
    pedido.estado = "Aceptado"
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/pedido_json/<int:pedido_id>')
def pedido_json(pedido_id):
    pedido = Envoltura.query.get(pedido_id)
    if not pedido:
        return {"error": "Pedido no encontrado"}, 404

    servicios_existentes = [
        {
            "servicio": s.servicio,
            "precio": float(s.precio) if s.precio else None,
            "comentario": s.comentario
        }
        for s in PedidoServicio.query.filter_by(pedido_id=pedido_id).all()
    ]

    servicios_si = []
    if pedido.caja == "Sí": servicios_si.append("Caja")
    if pedido.liston == "Sí": servicios_si.append("Listón")
    if pedido.mono == "Sí": servicios_si.append("Moño")
    if pedido.etiqueta == "Sí": servicios_si.append("Etiqueta")

    print(servicios_existentes)
    return {
        "cliente": pedido.cliente.nombre,
        "telefono": pedido.cliente.telefono,
        "descripcion": pedido.descripcion,
        "estado": pedido.estado,
        "servicios_si": servicios_si,
        "servicios_existentes": servicios_existentes,
        "encargado": pedido.encargado or ""
    }


def normalize(v):
    if not v: return ""
    v = v.lower()
    # quita tildes
    v = ''.join(c for c in unicodedata.normalize('NFD', v)
                if unicodedata.category(c) != 'Mn')
    return v

@app.route('/generar_boleta/<int:pedido_id>', methods=['GET'])
def generar_boleta(pedido_id):
    # Traer pedido
    pedido = Envoltura.query.get(pedido_id)
    if not pedido:
        return "Pedido no encontrado", 404

    cliente = pedido.cliente
    servicios = PedidoServicio.query.filter_by(pedido_id=pedido_id).all()

    # Datos para la boleta
    ahora = datetime.now()
    meses_es = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    fecha_str = f"{ahora.day} {meses_es[ahora.month-1]} {ahora.year}, {ahora.hour}h{ahora.minute:02d}"

    # Calcular posición de esta envoltura entre las del cliente (1 de N)
    total_envolturas = len(cliente.envolturas) if cliente else 1
    index = 1
    if cliente:
        # ordenadas por id ascendente; buscar índice 1-based
        ids = [e.id for e in sorted(cliente.envolturas, key=lambda x: x.id)]
        try:
            index = ids.index(pedido.id) + 1
        except ValueError:
            index = 1

    # Precio base de envoltura (por ahora fijo)
    precio_base_envoltura = 9.00

    # Suma precios de servicios (si alguno tiene precio None, lo ignora)
    total_servicios = 0.0
    for s in servicios:
        try:
            if s.precio is not None:
                total_servicios += float(s.precio)
        except Exception:
            pass

    total = total_servicios + precio_base_envoltura

    # Preparar PDF en memoria
    buffer = io.BytesIO()
    # Tamaño: uso A6 vertical (muy similar a ticket pequeño). Ajusta si quieres otro tamaño.
    PAGE_SIZE = portrait(A6)
    c = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE

    # Margen
    x_margin = 8 * mm
    y = height - 8 * mm

    # Logo (usa la ruta local proporcionada)
    logo_path = "/mnt/data/f899096d-d0f6-4fa6-b697-7ddd02cba461.png"
    try:
        # dibuja logo centrado en la parte superior (ajusta tamaño si necesario)
        logo_w = 28 * mm
        logo_h = 28 * mm
        c.drawImage(logo_path, (width - logo_w) / 2, y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
        y = y - logo_h - 4 * mm
    except Exception:
        # si no hay logo, seguimos sin fallo
        pass

    # ID grande centrado
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, y, str(pedido.id))
    y -= 8 * mm

    # Fecha y hora
    c.setFont("Helvetica", 8)
    c.drawString(x_margin, y, fecha_str)
    y -= 5 * mm

    # Nombre cliente
    if cliente:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x_margin, y, cliente.nombre)
        y -= 5 * mm
        c.setFont("Helvetica", 8)
        c.drawString(x_margin, y, cliente.telefono or "")
        y -= 6 * mm
    else:
        c.setFont("Helvetica", 8)
        c.drawString(x_margin, y, "—")
        y -= 6 * mm

    # Cantidad de envolturas (ej: "1 de 3")
    c.setFont("Helvetica", 8)
    c.drawString(x_margin, y, f"{index} de {total_envolturas}")
    y -= 6 * mm

    # Línea separadora
    c.line(x_margin, y, width - x_margin, y)
    y -= 4 * mm

    # Descripción del regalo
    c.setFont("Helvetica", 9)
    # Wrap simple de la descripción si es larga
    descripcion = pedido.descripcion or ""
    max_width = width - 2 * x_margin
    textobj = c.beginText(x_margin, y)
    textobj.setFont("Helvetica", 9)
    # Splitear por palabras y ajustar líneas
    words = descripcion.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 9) < max_width:
            line = test
        else:
            textobj.textLine(line)
            line = w
    if line:
        textobj.textLine(line)
    c.drawText(textobj)
    y = textobj.getY() - 4 * mm

    # Detalle servicios: mostramos cada servicio (iconos no obligatorios)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_margin, y, "Servicios / Envoltura")
    y -= 6 * mm

    # Tabla simple: nombre (izq) y precio (derecha)
    c.setFont("Helvetica", 9)
    for s in servicios:
        nombre = s.servicio
        precio_display = f"{float(s.precio):.2f}$" if (s.precio is not None) else "—"
        # Nombre a la izquierda (wrap si necesario)
        # Si se queda sin espacio vertical, crea nueva página (no esperado en A6 corto, pero por si acaso)
        if y < 25 * mm:
            c.showPage()
            y = height - 8 * mm

        # dibujar nombre
        c.drawString(x_margin, y, nombre)
        # dibujar precio alineado a la derecha
        text_w = c.stringWidth(precio_display, "Helvetica", 9)
        c.drawString(width - x_margin - text_w, y, precio_display)
        y -= 5 * mm
        # si hay comentario, lo mostramos en una línea más chica
        if s.comentario:
            c.setFont("Helvetica-Oblique", 7)
            # wrap comentario
            comment = str(s.comentario)
            # corte simple
            if c.stringWidth(comment, "Helvetica-Oblique", 7) > max_width:
                # recortar si demasiado largo
                while c.stringWidth(comment + "...", "Helvetica-Oblique", 7) > max_width and len(comment) > 5:
                    comment = comment[:-1]
                comment = comment + "..."
            c.drawString(x_margin + 3 * mm, y, comment)
            y -= 4 * mm
            c.setFont("Helvetica", 9)

    # Mostrar precio base de envoltura (fijo)
    if y < 30 * mm:
        c.showPage()
        y = height - 8 * mm

    c.setFont("Helvetica-Bold", 9)
    base_label = "Precio envoltura"
    base_str = f"{precio_base_envoltura:.2f}$"
    c.drawString(x_margin, y, base_label)
    text_w = c.stringWidth(base_str, "Helvetica-Bold", 9)
    c.drawString(width - x_margin - text_w, y, base_str)
    y -= 8 * mm

    # Total
    c.setFont("Helvetica-Bold", 11)
    total_str = f"Total: {total:.2f}$"
    c.drawString(x_margin, y, total_str)
    y -= 8 * mm

    # Encargado / Servi par
    c.setFont("Helvetica", 9)
    encargado_text = pedido.encargado or "—"
    c.drawString(x_margin, y, f"Servi par: {encargado_text}")

    # Finalizar PDF
    c.showPage()
    c.save()

    buffer.seek(0)
    filename = f"boleta_{pedido.id}.pdf"

    pedido.estado = "Facturado"
    db.session.commit()

    pendientes = Envoltura.query.filter(
        Envoltura.pedido_id == pedido.pedido_id,
        Envoltura.estado.notin_(('Facturado', 'Cancelado'))
    ).count()

    # Si no quedan pendientes → generar boleta del pedido completo
    if pendientes == 0:
        response = send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        response.headers['X-Redirect-Generar-General'] = url_for(
            'generar_boleta_pedido',
            pedido_id=pedido.pedido_id,
            _external=True
        )
        return response

    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/generar_boleta_pedido/<int:pedido_id>', methods=['GET'])
def generar_boleta_pedido(pedido_id):

    buffer = generar_boleta_pedido_completo(
        pedido_id
    )

    if not buffer:
        return "No se pudo generar la boleta", 400

    return send_file(
        buffer,
        mimetype='application/pdf',
        download_name=f'boleta_pedido_{pedido_id}.pdf'
    )


def generar_boleta_pedido_completo(pedido_id):
    pedido = Pedido.query.get(pedido_id)

    propina = pedido.propina or 0
    donacion = pedido.donacion or 0

    if not pedido:
        return None

    cliente = pedido.envolturas[0].cliente
    envolturas = Envoltura.query.filter_by(pedido_id=pedido_id).all()
    servicios_map = {}  # { envoltura_id : [servicios...] }

    for e in envolturas:
        servicios_map[e.id] = PedidoServicio.query.filter_by(pedido_id=e.id).all()

    # PDF
    buffer = io.BytesIO()
    PAGE_SIZE = portrait(A5)
    c = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE
    x_margin = 12 * mm
    y = height - 15 * mm

    # Título
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, y, f"Boleta del Pedido #{pedido.id}")
    y -= 12 * mm

    # Cliente
    if cliente:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_margin, y, f"Cliente: {cliente.nombre}")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y, f"Teléfono: {cliente.telefono}")
        y -= 8 * mm

    # Línea separadora
    c.line(x_margin, y, width - x_margin, y)
    y -= 8 * mm

    total_general = 0.0

    # Por cada envoltura
    for e in envolturas:
        if y < 40 * mm:
            c.showPage()
            y = height - 15 * mm

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y, f"Envoltura #{e.id}")
        y -= 7 * mm

        c.setFont("Helvetica", 10)
        c.drawString(x_margin, y, f"Descripción: {e.descripcion}")
        y -= 6 * mm
        c.drawString(x_margin, y, f"Para: {e.para}")
        y -= 6 * mm

        # Servicios
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y, "Servicios:")
        y -= 6 * mm

        subtotal = 9.00    # precio base
        c.setFont("Helvetica", 10)

        for s in servicios_map[e.id]:
            precio = float(s.precio or 0)
            subtotal += precio
            c.drawString(x_margin + 5 * mm, y, f"- {s.servicio}: {precio:.2f}$")
            y -= 6 * mm

        # Subtotal
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_margin, y, f"Subtotal: {subtotal:.2f}$")
        y -= 10 * mm

        total_general += subtotal

        # Línea separadora
        c.line(x_margin, y, width - x_margin, y)
        y -= 10 * mm

    # Total general
    if y < 30 * mm:
        c.showPage()
        y = height - 15 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, f"Propina: {propina:.2f}$")
    y -= 7 * mm
    c.drawString(x_margin, y, f"Donación: {donacion:.2f}$")
    y -= 10 * mm

    total_general += propina + donacion


    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y, f"TOTAL DEL PEDIDO: {total_general:.2f}$")

    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer


@app.route("/actualizar_propina_donacion/<int:pedido_id>", methods=["POST"])
def actualizar_propina_donacion(pedido_id):
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return "Pedido no encontrado", 404

    propina = float(request.form.get("propina") or 0)
    donacion = float(request.form.get("donacion") or 0)

    pedido.propina = propina
    pedido.donacion = donacion
    db.session.commit()

    return redirect(url_for("admin"))



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
