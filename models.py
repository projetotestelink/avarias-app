from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='visualizador')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    avarias = db.relationship('Avaria', backref='usuario', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class SKU(db.Model):
    __tablename__ = 'skus'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    avarias = db.relationship('Avaria', backref='sku_rel', lazy=True)

    def __repr__(self):
        return f'<SKU {self.codigo}>'


class Localizacao(db.Model):
    __tablename__ = 'localizacoes'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    endereco = db.Column(db.String(50), unique=True, nullable=False, index=True)
    area = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    avarias = db.relationship('Avaria', backref='localizacao_rel', lazy=True)
    fotos_palete = db.relationship('FotoPalete', backref='localizacao_rel', lazy=True)

    def __repr__(self):
        return f'<Localizacao {self.endereco}>'


class Avaria(db.Model):
    __tablename__ = 'avarias'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    localizacao_id = db.Column(db.Integer, db.ForeignKey('localizacoes.id'), nullable=False)
    sku_id = db.Column(db.Integer, db.ForeignKey('skus.id'), nullable=False)
    sku_codigo = db.Column(db.String(50), nullable=False)
    sku_descricao = db.Column(db.String(200), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    fotos = db.relationship('FotoAvaria', backref='avaria_rel', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Avaria {self.id} - SKU {self.sku_codigo}>'


class FotoAvaria(db.Model):
    __tablename__ = 'fotos_avaria'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    avaria_id = db.Column(db.Integer, db.ForeignKey('avarias.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class FotoPalete(db.Model):
    __tablename__ = 'fotos_palete'

    id = db.Column(db.Integer, db.Identity(always=False), primary_key=True)
    localizacao_id = db.Column(db.Integer, db.ForeignKey('localizacoes.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship('User', backref='fotos_palete')
