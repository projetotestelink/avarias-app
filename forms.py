from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, PasswordField, SelectField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])


class UserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[Optional(), Length(min=4, max=100)])
    role = SelectField('Perfil', choices=[
        ('admin', 'Administrador'),
        ('lancador', 'Lançador'),
        ('visualizador', 'Visualizador')
    ], validators=[DataRequired()])


class SKUForm(FlaskForm):
    codigo = StringField('Código SKU', validators=[DataRequired(), Length(max=50)])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])


class SKUImportForm(FlaskForm):
    planilha = FileField('Planilha (CSV)', validators=[DataRequired()])


class LocalizacaoForm(FlaskForm):
    endereco = StringField('Endereço', validators=[DataRequired(), Length(max=50)])
    area = SelectField('Área', choices=[
        ('', 'Selecione...'),
        ('CD', 'CD'),
        ('CS', 'CS'),
        ('Transporte', 'Transporte'),
        ('FL 1500', 'FL 1500')
    ], validators=[DataRequired()])
    observacoes = TextAreaField('Observações', validators=[Optional()])


class AvariaForm(FlaskForm):
    sku_codigo = StringField('Código SKU', validators=[DataRequired(), Length(max=50)])
    sku_descricao = StringField('Descrição do Item', validators=[DataRequired(), Length(max=200)])
    endereco = StringField('Endereço', validators=[DataRequired(), Length(max=50)])
    area = SelectField('Área', choices=[
        ('', 'Selecione...'),
        ('CD', 'CD'),
        ('CS', 'CS'),
        ('Transporte', 'Transporte'),
        ('FL 1500', 'FL 1500')
    ], validators=[DataRequired()])
    quantidade = IntegerField('Quantidade com Avaria', validators=[DataRequired()])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    fotos_item = FileField('Fotos do Item', validators=[Optional()])
    fotos_palete = FileField('Fotos do Palete', validators=[Optional()])


class FotoPaleteForm(FlaskForm):
    endereco = StringField('Endereço', validators=[DataRequired(), Length(max=50)])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    fotos = FileField('Fotos do Palete', validators=[DataRequired()])
