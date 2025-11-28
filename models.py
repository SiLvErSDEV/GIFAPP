from app import db
import datetime

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(120))
    envolturas = db.relationship('Envoltura', backref='cliente', lazy=True)

class Envoltura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200))
    para = db.Column(db.String(100))
    papel = db.Column(db.String(50))
    liston = db.Column(db.String(10))
    mono = db.Column(db.String(10))
    caja = db.Column(db.String(10))
    etiqueta = db.Column(db.String(10))
    estado = db.Column(db.String(30), default="Registrado")
    encargado = db.Column(db.String(100))
    #precio_caja = db.Column(db.Float, nullable=True)
    #precio_liston = db.Column(db.Float, nullable=True)
    #precio_mono = db.Column(db.Float, nullable=True)
    #precio_etiqueta = db.Column(db.Float, nullable=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)


class PedidoServicio(db.Model):
    __tablename__ = 'PedidoServicio'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('envoltura.id'), nullable=False)
    servicio = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Numeric(10,2))
    comentario = db.Column(db.Text)
    pedido = db.relationship('Envoltura', backref=db.backref('servicios', lazy=True))


class Pedido(db.Model):
    __tablename__ = 'pedido'
    id = db.Column(db.Integer, primary_key=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.datetime.now)
    envolturas = db.relationship('Envoltura', backref='pedido', lazy=True)
    propina = db.Column(db.Float, default=0.0)
    donacion = db.Column(db.Float, default=0.0)
