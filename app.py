import os
import uuid
from datetime import datetime, timezone

from flask import (Flask, render_template, redirect, url_for, flash,
                   request, jsonify, send_from_directory, abort)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from werkzeug.utils import secure_filename

import cloudinary
import cloudinary.uploader

from config import Config
from models import db, User, SKU, Localizacao, Avaria, FotoAvaria, FotoPalete
from forms import (LoginForm, UserForm, SKUForm, SKUImportForm, LocalizacaoForm,
                   AvariaForm, FotoPaleteForm)

app = Flask(__name__)
app.config.from_object(Config)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME') or 'dwuk4imd',
    api_key=os.environ.get('CLOUDINARY_API_KEY') or '313666729677654',
    api_secret=os.environ.get('CLOUDINARY_API_SECRET') or 'MjCHJjIfIYx0J75__Vbp68byPmM',
    secure=True
)

db.init_app(app)

@app.template_filter('image_url')
def image_url(path):
    if path and (path.startswith('http://') or path.startswith('https://')):
        return path
    return url_for('uploaded_file', filename=path)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_photos(files, subfolder):
    saved_paths = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            result = cloudinary.uploader.upload(
                file,
                folder=f"avarias-app/{subfolder}",
                resource_type="image"
            )
            saved_paths.append(result["secure_url"])
    return saved_paths


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def lancador_or_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role == 'visualizador':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def visualizador_or_admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role == 'lancador':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_now():
    return {'now': datetime.now()}


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(matricula=form.matricula.data).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login realizado com sucesso!', 'success')
            return redirect(next_page or url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    total_avarias = Avaria.query.count()
    total_skus = SKU.query.count()
    total_localizacoes = Localizacao.query.count()
    ultimas_avarias = Avaria.query.order_by(Avaria.created_at.desc()).limit(10).all()

    from sqlalchemy import func
    areas_data = db.session.query(
        Localizacao.area,
        func.sum(Avaria.quantidade).label('total')
    ).join(Avaria, Localizacao.id == Avaria.localizacao_id
    ).group_by(Localizacao.area).order_by(func.sum(Avaria.quantidade).desc()).all()

    return render_template('dashboard.html',
                         total_avarias=total_avarias,
                         total_skus=total_skus,
                         total_localizacoes=total_localizacoes,
                         ultimas_avarias=ultimas_avarias,
                         areas_data=areas_data)


@app.route('/avaria/nova', methods=['GET', 'POST'])
@login_required
@lancador_or_admin_required
def nova_avaria():
    form = AvariaForm()
    if form.validate_on_submit():
        sku = SKU.query.filter_by(codigo=form.sku_codigo.data.strip()).first()
        if not sku:
            sku = SKU(codigo=form.sku_codigo.data.strip(),
                      descricao=form.sku_descricao.data.strip())
            db.session.add(sku)
            db.session.flush()

        endereco = form.endereco.data.strip().upper()
        localizacao = Localizacao.query.filter_by(endereco=endereco).first()
        if not localizacao:
            localizacao = Localizacao(endereco=endereco,
                                     area=form.area.data.strip())
            db.session.add(localizacao)
            db.session.flush()

        avaria = Avaria(
            localizacao_id=localizacao.id,
            sku_id=sku.id,
            sku_codigo=sku.codigo,
            sku_descricao=sku.descricao,
            quantidade=form.quantidade.data,
            observacoes=form.observacoes.data,
            user_id=current_user.id
        )
        db.session.add(avaria)
        db.session.flush()

        fotos_item = request.files.getlist('fotos_item')
        if fotos_item and any(f.filename for f in fotos_item):
            paths = save_photos([f for f in fotos_item if f.filename], 'fotos_avarias')
            for path in paths:
                db.session.add(FotoAvaria(avaria_id=avaria.id, file_path=path))

        fotos_palete = request.files.getlist('fotos_palete')
        if fotos_palete and any(f.filename for f in fotos_palete):
            paths = save_photos([f for f in fotos_palete if f.filename], 'fotos_paletes')
            for path in paths:
                db.session.add(FotoPalete(
                    localizacao_id=localizacao.id,
                    file_path=path,
                    user_id=current_user.id,
                    observacoes=f"Vinculado à avaria #{avaria.id}"
                ))

        db.session.commit()
        flash('Avarias registrada com sucesso!', 'success')
        return redirect(url_for('relatorios'))

    return render_template('nova_avaria.html', form=form)


@app.route('/api/sku/<codigo>')
@login_required
def api_sku(codigo):
    sku = SKU.query.filter_by(codigo=codigo.strip()).first()
    if sku:
        return jsonify({'found': True, 'codigo': sku.codigo, 'descricao': sku.descricao})
    return jsonify({'found': False})


@app.route('/api/localizacao/<endereco>')
@login_required
def api_localizacao(endereco):
    loc = Localizacao.query.filter_by(endereco=endereco.strip().upper()).first()
    if loc:
        return jsonify({'found': True, 'endereco': loc.endereco, 'area': loc.area})
    return jsonify({'found': False})


@app.route('/relatorios')
@login_required
def relatorios():
    page = request.args.get('page', 1, type=int)
    sku_filter = request.args.get('sku', '')
    area_filter = request.args.get('area', '')
    endereco_filter = request.args.get('endereco', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    from sqlalchemy import func

    query = Avaria.query

    if sku_filter:
        query = query.filter(Avaria.sku_codigo.like(f'%{sku_filter}%'))
    if endereco_filter:
        query = query.filter(Avaria.localizacao_rel.has(Localizacao.endereco.like(f'%{endereco_filter.upper()}%')))
    if area_filter:
        query = query.filter(Avaria.localizacao_rel.has(Localizacao.area.like(f'%{area_filter}%')))
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Avaria.created_at >= dt_inicio)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Avaria.created_at <= dt_fim)
        except ValueError:
            pass

    resumo_query = query.join(Localizacao, Avaria.localizacao_id == Localizacao.id)
    resumo_enderecos = resumo_query.with_entities(
        Localizacao.endereco,
        Localizacao.area,
        func.count(func.distinct(Avaria.sku_id)).label('total_skus'),
        func.sum(Avaria.quantidade).label('total_unidades'),
        func.count(Avaria.id).label('total_linhas')
    ).group_by(Localizacao.endereco, Localizacao.area).order_by(Localizacao.endereco).all()

    pagination = query.order_by(Avaria.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    areas = db.session.query(Localizacao.area).distinct().all()

    return render_template('relatorios.html',
                         pagination=pagination,
                         resumo_enderecos=resumo_enderecos,
                         areas=[a[0] for a in areas],
                         sku_filter=sku_filter,
                         area_filter=area_filter,
                         endereco_filter=endereco_filter,
                         data_inicio=data_inicio,
                         data_fim=data_fim)


@app.route('/avaria/<int:id>')
@login_required
def detalhes_avaria(id):
    avaria = db.session.get(Avaria, id)
    if not avaria:
        abort(404)
    fotos_palete = FotoPalete.query.filter_by(localizacao_id=avaria.localizacao_id).all()
    return render_template('detalhes_avaria.html', avaria=avaria, fotos_palete=fotos_palete)


@app.route('/avaria/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_avaria(id):
    avaria = db.session.get(Avaria, id)
    if not avaria:
        abort(404)
    db.session.delete(avaria)
    db.session.commit()
    flash('Avarias excluída com sucesso!', 'success')
    return redirect(url_for('relatorios'))


@app.route('/gerenciar/skus', methods=['GET', 'POST'])
@login_required
@admin_required
def gerenciar_skus():
    form = SKUForm()
    import_form = SKUImportForm()
    if form.validate_on_submit():
        existente = SKU.query.filter_by(codigo=form.codigo.data.strip()).first()
        if existente:
            flash('SKU já cadastrado!', 'warning')
        else:
            sku = SKU(codigo=form.codigo.data.strip(), descricao=form.descricao.data.strip())
            db.session.add(sku)
            db.session.commit()
            flash('SKU cadastrado com sucesso!', 'success')
        return redirect(url_for('gerenciar_skus'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = SKU.query
    if search:
        query = query.filter(
            SKU.codigo.like(f'%{search}%') | SKU.descricao.like(f'%{search}%')
        )
    pagination = query.order_by(SKU.codigo).paginate(page=page, per_page=30, error_out=False)
    return render_template('gerenciar_skus.html', form=form, import_form=import_form, pagination=pagination, search=search)


@app.route('/gerenciar/skus/importar', methods=['POST'])
@login_required
@admin_required
def importar_skus():
    import_form = SKUImportForm()
    if import_form.validate_on_submit():
        file = import_form.planilha.data
        if not file or not file.filename:
            flash('Nenhum arquivo enviado.', 'danger')
            return redirect(url_for('gerenciar_skus'))
        try:
            raw = file.read()
            content = None
            for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252']:
                try:
                    content = raw.decode(enc)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            if content is None:
                flash('Não foi possível ler o arquivo. Verifique a codificação (use UTF-8 ou Latin-1).', 'danger')
                return redirect(url_for('gerenciar_skus'))
            lines = content.splitlines()
            importados = 0
            ignorados = 0
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    ignorados += 1
                    continue
                codigo = parts[0].strip().strip('"').strip("'")
                descricao = parts[1].strip().strip('"').strip("'")
                if not codigo or not descricao:
                    ignorados += 1
                    continue
                existente = SKU.query.filter_by(codigo=codigo).first()
                if existente:
                    ignorados += 1
                    continue
                db.session.add(SKU(codigo=codigo, descricao=descricao))
                importados += 1
            db.session.commit()
            flash(f'{importados} SKU(s) importados com sucesso! {ignorados} ignorados (duplicados ou inválidos).', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao importar: {str(e)}', 'danger')
    else:
        flash('Envie um arquivo CSV válido.', 'danger')
    return redirect(url_for('gerenciar_skus'))


@app.route('/gerenciar/skus/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_sku(id):
    sku = db.session.get(SKU, id)
    if not sku:
        abort(404)
    if sku.avarias:
        for avaria in sku.avarias:
            db.session.delete(avaria)
    db.session.delete(sku)
    db.session.commit()
    flash(f'SKU {sku.codigo} e {len(sku.avarias)} avaria(s) vinculada(s) foram excluídos!', 'success')
    return redirect(url_for('gerenciar_skus'))


@app.route('/gerenciar/localizacoes', methods=['GET', 'POST'])
@login_required
@admin_required
def gerenciar_localizacoes():
    form = LocalizacaoForm()
    if form.validate_on_submit():
        existente = Localizacao.query.filter_by(
            endereco=form.endereco.data.strip().upper()).first()
        if existente:
            flash('Endereço já cadastrado!', 'warning')
        else:
            loc = Localizacao(
                endereco=form.endereco.data.strip().upper(),
                area=form.area.data.strip(),
                observacoes=form.observacoes.data
            )
            db.session.add(loc)
            db.session.commit()
            flash('Localização cadastrada com sucesso!', 'success')
        return redirect(url_for('gerenciar_localizacoes'))

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Localizacao.query
    if search:
        query = query.filter(
            Localizacao.endereco.like(f'%{search}%') |
            Localizacao.area.like(f'%{search}%')
        )
    pagination = query.order_by(Localizacao.endereco).paginate(page=page, per_page=30, error_out=False)
    return render_template('gerenciar_localizacoes.html', form=form, pagination=pagination, search=search)


@app.route('/gerenciar/localizacoes/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_localizacao(id):
    loc = db.session.get(Localizacao, id)
    if not loc:
        abort(404)
    if loc.avarias:
        flash('Não é possível excluir localização com avarias vinculadas.', 'danger')
        return redirect(url_for('gerenciar_localizacoes'))
    db.session.delete(loc)
    db.session.commit()
    flash('Localização excluída!', 'success')
    return redirect(url_for('gerenciar_localizacoes'))


@app.route('/foto-palete', methods=['GET', 'POST'])
@login_required
@lancador_or_admin_required
def foto_palete():
    form = FotoPaleteForm()
    if form.validate_on_submit():
        endereco = form.endereco.data.strip().upper()
        localizacao = Localizacao.query.filter_by(endereco=endereco).first()
        if not localizacao:
            flash('Endereço não encontrado. Cadastre a localização primeiro.', 'danger')
            return render_template('foto_palete.html', form=form)

        fotos = request.files.getlist('fotos')
        if fotos and any(f.filename for f in fotos):
            paths = save_photos([f for f in fotos if f.filename], 'fotos_paletes')
            for path in paths:
                db.session.add(FotoPalete(
                    localizacao_id=localizacao.id,
                    file_path=path,
                    user_id=current_user.id,
                    observacoes=form.observacoes.data
                ))
            db.session.commit()
            flash(f'{len(paths)} foto(s) vinculada(s) ao palete {endereco}!', 'success')
        else:
            flash('Selecione pelo menos uma foto.', 'warning')
        return redirect(url_for('relatorios'))

    return render_template('foto_palete.html', form=form)


@app.route('/palete/<endereco>')
@login_required
def detalhes_palete(endereco):
    localizacao = Localizacao.query.filter_by(endereco=endereco.strip().upper()).first_or_404()
    avarias = Avaria.query.filter_by(localizacao_id=localizacao.id).order_by(
        Avaria.created_at.desc()).all()
    fotos = FotoPalete.query.filter_by(localizacao_id=localizacao.id).order_by(
        FotoPalete.created_at.desc()).all()
    return render_template('detalhes_palete.html',
                         localizacao=localizacao,
                         avarias=avarias,
                         fotos=fotos)


@app.route('/gerenciar/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def gerenciar_usuarios():
    form = UserForm()
    if form.validate_on_submit():
        existente = User.query.filter_by(matricula=form.matricula.data).first()
        if existente:
            flash('Matrícula já cadastrada!', 'warning')
        else:
            user = User(
                matricula=form.matricula.data,
                nome=form.nome.data,
                email=form.email.data or None,
                role=form.role.data
            )
            if form.password.data:
                user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('gerenciar_usuarios'))

    usuarios = User.query.order_by(User.matricula).all()
    return render_template('gerenciar_usuarios.html', form=form, usuarios=usuarios)


@app.route('/gerenciar/usuarios/<int:id>/editar', methods=['POST'])
@login_required
@admin_required
def editar_usuario(id):
    user = db.session.get(User, id)
    if not user:
        abort(404)
    matricula = request.form.get('matricula', '').strip()
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    if matricula:
        duplicado = User.query.filter(User.matricula == matricula, User.id != id).first()
        if duplicado:
            flash('Matrícula já em uso.', 'danger')
            return redirect(url_for('gerenciar_usuarios'))
        user.matricula = matricula
    if nome:
        user.nome = nome
    user.email = email or None
    user.role = request.form.get('role', user.role)
    user.is_active = request.form.get('is_active') == 'on'
    password = request.form.get('password')
    if password:
        user.set_password(password)
    db.session.commit()
    flash('Usuário atualizado!', 'success')
    return redirect(url_for('gerenciar_usuarios'))


@app.route('/gerenciar/usuarios/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(id):
    user = db.session.get(User, id)
    if not user:
        abort(404)
    if user.matricula == 'admin':
        flash('Não é possível excluir o usuário admin.', 'danger')
        return redirect(url_for('gerenciar_usuarios'))
    if current_user.id == user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('gerenciar_usuarios'))
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído!', 'success')
    return redirect(url_for('gerenciar_usuarios'))


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.route('/migrar')
def migrar():
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('usuarios')]
    alterou = False
    if 'username' in cols and 'matricula' not in cols:
        db.session.execute(db.text('ALTER TABLE usuarios RENAME COLUMN username TO matricula'))
        alterou = True
    elif 'username' in cols and 'matricula' in cols:
        db.session.execute(db.text('ALTER TABLE usuarios DROP COLUMN username'))
        alterou = True
    if 'nome' not in cols:
        db.session.execute(db.text('ALTER TABLE usuarios ADD (nome VARCHAR2(120))'))
        alterou = True
    try:
        db.session.execute(db.text('ALTER TABLE usuarios MODIFY (email NULL)'))
        alterou = True
    except Exception:
        pass
    if alterou:
        db.session.commit()
        admin = User.query.filter_by(matricula='admin').first()
        if admin and not admin.nome:
            admin.nome = 'Administrador'
            db.session.commit()
    if not User.query.filter_by(matricula='31674').first():
        user = User(matricula='31674', nome='Felipe Gomes', role='admin')
        user.set_password('1234')
        db.session.add(user)
        db.session.commit()
        return 'Migração concluída! Usuário 31674 criado. <a href="/login">Ir para login</a>'
    return 'Migração concluída! <a href="/login">Ir para login</a>'


def init_admin():
    admin = User.query.filter_by(matricula='admin').first()
    if not admin:
        admin = User(
            matricula='admin',
            nome='Administrador',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Usuário admin criado (admin / admin123)')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_admin()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
