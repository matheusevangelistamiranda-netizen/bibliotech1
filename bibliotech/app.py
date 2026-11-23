from datetime import date, timedelta
from functools import wraps
import hmac
import logging
import re
import secrets
from urllib.parse import urlsplit

import click
import mysql.connector
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import conectar

app = Flask(__name__)
app.config.from_object(Config)
app.permanent_session_lifetime = timedelta(hours=8)
logging.basicConfig(level=logging.INFO)

MULTA_POR_DIA = app.config["MULTA_POR_DIA"]
PRAZO_DIAS = app.config["PRAZO_DIAS"]
ITENS_POR_PAGINA = 12


@app.before_request
def proteger_post():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not hmac.compare_digest(session["csrf_token"], token):
            abort(400, description="Token de segurança inválido. Atualize a página e tente novamente.")
    if request.endpoint not in (None, "login", "static") and not session.get("bibliotecario_id"):
        destino = request.full_path if request.query_string else request.path
        return redirect(url_for("login", next=destino))
    if session.get("bibliotecario_id") and request.endpoint not in ("login", "static"):
        funcionario = obter(
            "SELECT ativo FROM bibliotecarios WHERE id_bibliotecario=%s",
            (session["bibliotecario_id"],),
        )
        if not funcionario or not funcionario["ativo"]:
            session.clear()
            return redirect(url_for("login"))


@app.context_processor
def disponibilizar_token():
    return {
        "csrf_token": lambda: session["csrf_token"],
        "today": date.today(),
        "nome_bibliotecario": session.get("bibliotecario_nome"),
        "bibliotecario_admin": session.get("bibliotecario_admin", False),
        "iniciais": lambda nome: "".join(parte[0].upper() for parte in nome.split()[:2]),
    }


def administrador_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("bibliotecario_admin"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@app.cli.command("criar-admin")
def criar_admin():
    """Cria o primeiro funcionário administrador pelo terminal."""
    nome = click.prompt("Nome completo").strip()
    usuario = click.prompt("Nome de usuário").strip()
    senha = click.prompt("Senha (mínimo 12 caracteres)", hide_input=True, confirmation_prompt=True)
    if not nome or len(nome) > 180:
        raise click.ClickException("O nome é obrigatório e deve ter até 180 caracteres.")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", usuario):
        raise click.ClickException("O usuário deve ter de 3 a 80 caracteres: letras, números, ponto, hífen ou sublinhado.")
    if len(senha) < 12:
        raise click.ClickException("A senha precisa ter pelo menos 12 caracteres.")
    existente = obter("SELECT id_bibliotecario FROM bibliotecarios WHERE usuario=%s", (usuario,))
    if existente:
        raise click.ClickException("Esse nome de usuário já existe.")
    executar(
        """INSERT INTO bibliotecarios (nome, usuario, senha_hash, administrador, ativo)
           VALUES (%s, %s, %s, 1, 1)""",
        (nome, usuario, generate_password_hash(senha)),
    )
    click.echo("Conta administradora criada.")


@app.route("/entrar", methods=["GET", "POST"])
def login():
    if session.get("bibliotecario_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        funcionario = obter(
            """SELECT id_bibliotecario, nome, usuario, senha_hash, administrador, ativo
                 FROM bibliotecarios WHERE usuario=%s""",
            (usuario,),
        )
        if funcionario and funcionario["ativo"] and check_password_hash(funcionario["senha_hash"], senha):
            session.clear()
            session["csrf_token"] = secrets.token_hex(32)
            session["bibliotecario_id"] = funcionario["id_bibliotecario"]
            session["bibliotecario_nome"] = funcionario["nome"]
            session["bibliotecario_admin"] = bool(funcionario["administrador"])
            session.permanent = True
            destino = request.form.get("next", "")
            parsed = urlsplit(destino)
            if (
                not destino.startswith("/")
                or destino.startswith("//")
                or "\\" in destino
                or parsed.scheme
                or parsed.netloc
            ):
                destino = url_for("index")
            return redirect(destino)
        flash("Usuário ou senha inválidos, ou conta desativada.", "erro")
    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/sair", methods=["POST"])
def logout():
    session.clear()
    flash("Sessão encerrada.", "ok")
    return redirect(url_for("login"))


@app.errorhandler(mysql.connector.Error)
def erro_banco(exc):
    app.logger.exception("Falha ao acessar o MySQL")
    return render_template(
        "erro.html",
        codigo=503,
        mensagem="Não foi possível acessar o banco de dados. Confira a configuração e tente novamente.",
    ), 503


def listar(sql, params=()):
    with conectar() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()


def obter(sql, params=()):
    rows = listar(sql, params)
    return rows[0] if rows else None


def executar(sql, params=()):
    with conectar() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def autores_formulario():
    return listar("SELECT id_autor, nome FROM autores ORDER BY nome")


def campos_livro(form):
    titulo = form.get("titulo", "").strip()
    if not titulo:
        raise ValueError("O título do livro é obrigatório.")
    if len(titulo) > 255:
        raise ValueError("O título pode ter no máximo 255 caracteres.")
    try:
        ano = int(form.get("ano_publicacao") or 0) or None
    except ValueError as exc:
        raise ValueError("Informe um ano de publicação válido.") from exc
    if ano and not 1000 <= ano <= date.today().year + 1:
        raise ValueError("O ano de publicação informado é inválido.")
    try:
        exemplares = int(form.get("total_exemplares") or 0)
    except ValueError as exc:
        raise ValueError("A quantidade de exemplares deve ser um número inteiro.") from exc
    if exemplares < 0:
        raise ValueError("A quantidade de exemplares não pode ser negativa.")
    categoria = form.get("categoria", "").strip() or None
    isbn = form.get("isbn", "").strip() or None
    editora = form.get("editora", "").strip() or None
    descricao = form.get("descricao", "").strip() or None
    capa = form.get("capa_url", "").strip() or None
    autores = form.get("autores", "").strip()
    if categoria and len(categoria) > 120:
        raise ValueError("A categoria pode ter no máximo 120 caracteres.")
    if isbn and len(isbn) > 20:
        raise ValueError("O ISBN pode ter no máximo 20 caracteres.")
    if editora and len(editora) > 180:
        raise ValueError("A editora pode ter no máximo 180 caracteres.")
    if descricao and len(descricao) > 5000:
        raise ValueError("A descrição pode ter no máximo 5.000 caracteres.")
    if capa:
        url = urlsplit(capa)
        if len(capa) > 1000 or url.scheme not in ("http", "https") or not url.netloc:
            raise ValueError("Informe uma URL de capa válida (http ou https).")
    if any(len(nome.strip()) > 180 for nome in autores.split(",")):
        raise ValueError("Cada nome de autor pode ter no máximo 180 caracteres.")
    return (
        titulo,
        categoria,
        ano,
        isbn,
        editora,
        descricao,
        capa,
        autores,
        exemplares,
    )


def campos_leitor(form):
    nome = form.get("nome", "").strip()
    email = form.get("email", "").strip() or None
    telefone = form.get("telefone", "").strip() or None
    if not nome:
        raise ValueError("O nome do leitor é obrigatório.")
    if len(nome) > 180:
        raise ValueError("O nome pode ter no máximo 180 caracteres.")
    if email and (len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        raise ValueError("Informe um endereço de e-mail válido (máximo de 254 caracteres).")
    if telefone and len(telefone) > 40:
        raise ValueError("O telefone pode ter no máximo 40 caracteres.")
    return nome, email, telefone


def salvar_autores(cur, id_livro, nomes):
    cur.execute("DELETE FROM livro_autor WHERE id_livro = %s", (id_livro,))
    for nome in dict.fromkeys(n.strip() for n in nomes.split(",") if n.strip()):
        cur.execute("SELECT id_autor FROM autores WHERE nome = %s ORDER BY id_autor LIMIT 1", (nome,))
        autor = cur.fetchone()
        if autor is None:
            cur.execute("INSERT INTO autores (nome) VALUES (%s)", (nome,))
            id_autor = cur.lastrowid
        else:
            id_autor = autor[0]
        cur.execute(
            "INSERT IGNORE INTO livro_autor (id_livro, id_autor) VALUES (%s, %s)",
            (id_livro, id_autor),
        )


def dados_livro(id_livro):
    livro = obter(
        """
        SELECT l.*,
               (SELECT GROUP_CONCAT(a.nome ORDER BY a.nome SEPARATOR ', ')
                  FROM livro_autor la JOIN autores a ON a.id_autor = la.id_autor
                 WHERE la.id_livro = l.id_livro) AS autores,
               (SELECT COUNT(*) FROM exemplares e WHERE e.id_livro = l.id_livro) AS total,
               (SELECT COUNT(*) FROM exemplares e
                 WHERE e.id_livro = l.id_livro AND e.status = 'disponivel') AS disponiveis
          FROM livros l WHERE l.id_livro = %s
        """,
        (id_livro,),
    )
    if not livro:
        abort(404)
    return livro


def formulario_livro(livro=None):
    return render_template(
        "livro_form.html",
        livro=livro or {},
        autores=autores_formulario(),
        editando=livro is not None,
    )


def consultar_estante(ordenacao, categoria=None, limite=8):
    ordenacoes = {
        "populares": "emprestimos_count DESC, disponiveis DESC, l.titulo ASC",
        "recentes": "l.ano_publicacao DESC, l.id_livro DESC",
        "classicos": "l.ano_publicacao ASC, l.titulo ASC",
        "desejados": "reservas_count DESC, emprestimos_count DESC, l.titulo ASC",
    }
    if ordenacao not in ordenacoes:
        raise ValueError("Ordenação de estante inválida.")
    filtro = " WHERE l.categoria=%s" if categoria else ""
    parametros = (categoria, limite) if categoria else (limite,)
    return listar(
        f"""
        SELECT l.id_livro, l.titulo, l.categoria, l.ano_publicacao, l.capa_url,
               (SELECT GROUP_CONCAT(a.nome ORDER BY a.nome SEPARATOR ', ')
                  FROM livro_autor la JOIN autores a ON a.id_autor=la.id_autor
                 WHERE la.id_livro=l.id_livro) AS autores,
               (SELECT COUNT(*) FROM exemplares ex WHERE ex.id_livro=l.id_livro) AS total,
               (SELECT COUNT(*) FROM exemplares ex
                 WHERE ex.id_livro=l.id_livro AND ex.status='disponivel') AS disponiveis,
               (SELECT COUNT(*) FROM emprestimos em
                 JOIN exemplares ex ON ex.id_exemplar=em.id_exemplar
                 WHERE ex.id_livro=l.id_livro) AS emprestimos_count,
               (SELECT COUNT(*) FROM reservas r
                 WHERE r.id_livro=l.id_livro AND r.status='aguardando') AS reservas_count
          FROM livros l{filtro}
         ORDER BY {ordenacoes[ordenacao]}
         LIMIT %s
        """,
        parametros,
    )


@app.route("/equipe")
@administrador_required
def equipe():
    funcionarios = listar(
        """SELECT id_bibliotecario, nome, usuario, administrador, ativo, criado_em
             FROM bibliotecarios ORDER BY nome"""
    )
    return render_template("equipe.html", funcionarios=funcionarios)


@app.route("/equipe/novo", methods=["POST"])
@administrador_required
def novo_bibliotecario():
    nome = request.form.get("nome", "").strip()
    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "")
    administrador = request.form.get("administrador") == "1"
    if not nome or len(nome) > 180:
        flash("Informe um nome com até 180 caracteres.", "erro")
    elif not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", usuario):
        flash("O usuário deve ter de 3 a 80 caracteres: letras, números, ponto, hífen ou sublinhado.", "erro")
    elif len(senha) < 12:
        flash("A senha precisa ter pelo menos 12 caracteres.", "erro")
    elif obter("SELECT id_bibliotecario FROM bibliotecarios WHERE usuario=%s", (usuario,)):
        flash("Esse nome de usuário já está em uso.", "erro")
    else:
        executar(
            """INSERT INTO bibliotecarios (nome, usuario, senha_hash, administrador, ativo)
               VALUES (%s, %s, %s, %s, 1)""",
            (nome, usuario, generate_password_hash(senha), administrador),
        )
        flash("Conta de funcionário criada.", "ok")
        return redirect(url_for("equipe"))
    funcionarios = listar(
        """SELECT id_bibliotecario, nome, usuario, administrador, ativo, criado_em
             FROM bibliotecarios ORDER BY nome"""
    )
    return render_template("equipe.html", funcionarios=funcionarios)


@app.route("/equipe/<int:id_bibliotecario>/desativar", methods=["POST"])
@administrador_required
def desativar_bibliotecario(id_bibliotecario):
    funcionario = obter(
        "SELECT id_bibliotecario, administrador, ativo FROM bibliotecarios WHERE id_bibliotecario=%s",
        (id_bibliotecario,),
    )
    if not funcionario:
        abort(404)
    if id_bibliotecario == session["bibliotecario_id"]:
        flash("Não é possível desativar a própria conta.", "erro")
    elif funcionario["administrador"] and funcionario["ativo"]:
        admins = obter(
            "SELECT COUNT(*) AS total FROM bibliotecarios WHERE administrador=1 AND ativo=1"
        )
        if admins["total"] <= 1:
            flash("Mantenha pelo menos uma conta administradora ativa.", "erro")
        else:
            executar(
                "UPDATE bibliotecarios SET ativo=0 WHERE id_bibliotecario=%s",
                (id_bibliotecario,),
            )
            flash("Conta desativada.", "ok")
    else:
        executar(
            "UPDATE bibliotecarios SET ativo=0 WHERE id_bibliotecario=%s",
            (id_bibliotecario,),
        )
        flash("Conta desativada.", "ok")
    return redirect(url_for("equipe"))


@app.route("/reservas")
def reservas():
    fila = listar(
        """SELECT r.id_reserva, r.id_livro, r.id_usuario, r.data_reserva, r.status,
                  u.nome, l.titulo, l.capa_url,
                  (SELECT COUNT(*) FROM exemplares ex
                    WHERE ex.id_livro=l.id_livro AND ex.status='disponivel') AS disponiveis
             FROM reservas r
             JOIN usuarios u ON u.id_usuario=r.id_usuario
             JOIN livros l ON l.id_livro=r.id_livro
            WHERE r.status='aguardando'
            ORDER BY r.data_reserva, r.id_reserva"""
    )
    exemplares = listar(
        """SELECT ex.id_exemplar, ex.id_livro, l.titulo
             FROM exemplares ex JOIN livros l ON l.id_livro=ex.id_livro
            WHERE ex.status='disponivel' ORDER BY l.titulo, ex.id_exemplar"""
    )
    return render_template("reservas.html", reservas=fila, exemplares=exemplares)


@app.route("/reservar/<int:id_livro>", methods=["GET", "POST"])
def reservar_livro(id_livro):
    livro = dados_livro(id_livro)
    usuarios = listar("SELECT id_usuario, nome FROM usuarios ORDER BY nome")
    if request.method == "POST":
        try:
            id_usuario = int(request.form.get("id_usuario", ""))
        except ValueError:
            flash("Selecione um leitor válido.", "erro")
            return render_template("reservar.html", livro=livro, usuarios=usuarios)
        with conectar() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT id_livro FROM livros WHERE id_livro=%s FOR UPDATE", (id_livro,))
                existe = cur.fetchone()
                cur.execute("SELECT id_usuario FROM usuarios WHERE id_usuario=%s", (id_usuario,))
                usuario = cur.fetchone()
                cur.execute(
                    "SELECT id_exemplar FROM exemplares WHERE id_livro=%s AND status='disponivel' LIMIT 1",
                    (id_livro,),
                )
                disponivel = cur.fetchone()
                cur.execute(
                    """SELECT id_reserva FROM reservas
                       WHERE id_livro=%s AND id_usuario=%s AND status='aguardando' LIMIT 1""",
                    (id_livro, id_usuario),
                )
                duplicada = cur.fetchone()
                if not existe or not usuario:
                    conn.rollback()
                    flash("Livro ou leitor não encontrado.", "erro")
                elif disponivel:
                    conn.rollback()
                    flash("Este livro está disponível para empréstimo; não precisa de reserva.", "erro")
                    return redirect(url_for("emprestimos", id_livro=id_livro))
                elif duplicada:
                    conn.rollback()
                    flash("Este leitor já está na fila de espera para esta obra.", "erro")
                else:
                    cur.execute(
                        """INSERT INTO reservas (id_usuario, id_livro, status)
                           VALUES (%s, %s, 'aguardando')""",
                        (id_usuario, id_livro),
                    )
                    conn.commit()
                    flash("Reserva adicionada à fila de espera.", "ok")
                    return redirect(url_for("reservas"))
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
        livro = dados_livro(id_livro)
    return render_template("reservar.html", livro=livro, usuarios=usuarios)


@app.route("/reservas/<int:id_reserva>/atender", methods=["POST"])
def atender_reserva(id_reserva):
    try:
        id_exemplar = int(request.form.get("id_exemplar", ""))
    except ValueError:
        flash("Escolha um exemplar disponível para atender a reserva.", "erro")
        return redirect(url_for("reservas"))
    hoje = date.today()
    prevista = hoje + timedelta(days=PRAZO_DIAS)
    with conectar() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id_usuario, id_livro, status FROM reservas WHERE id_reserva=%s FOR UPDATE",
                (id_reserva,),
            )
            reserva = cur.fetchone()
            cur.execute(
                "SELECT id_livro, status FROM exemplares WHERE id_exemplar=%s FOR UPDATE",
                (id_exemplar,),
            )
            exemplar = cur.fetchone()
            if not reserva or reserva[2] != "aguardando":
                conn.rollback()
                flash("A reserva não está mais aguardando atendimento.", "erro")
            elif not exemplar or exemplar[0] != reserva[1] or exemplar[1] != "disponivel":
                conn.rollback()
                flash("O exemplar escolhido não está disponível para essa reserva.", "erro")
            else:
                cur.execute(
                    """INSERT INTO emprestimos
                       (id_usuario, id_exemplar, data_emprestimo, data_prevista)
                       VALUES (%s, %s, %s, %s)""",
                    (reserva[0], id_exemplar, hoje, prevista),
                )
                id_emprestimo = cur.lastrowid
                cur.execute(
                    "UPDATE exemplares SET status='emprestado' WHERE id_exemplar=%s",
                    (id_exemplar,),
                )
                cur.execute(
                    """UPDATE reservas SET status='atendida', id_emprestimo=%s
                       WHERE id_reserva=%s""",
                    (id_emprestimo, id_reserva),
                )
                conn.commit()
                flash("Reserva atendida e empréstimo registrado.", "ok")
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    return redirect(url_for("reservas"))


@app.route("/reservas/<int:id_reserva>/cancelar", methods=["POST"])
def cancelar_reserva(id_reserva):
    resultado = obter(
        "SELECT status FROM reservas WHERE id_reserva=%s",
        (id_reserva,),
    )
    if not resultado:
        abort(404)
    if resultado["status"] != "aguardando":
        flash("Só é possível cancelar reservas ainda aguardando.", "erro")
    else:
        executar(
            "UPDATE reservas SET status='cancelada' WHERE id_reserva=%s",
            (id_reserva,),
        )
        flash("Reserva cancelada.", "ok")
    return redirect(url_for("reservas"))


@app.route("/")
def index():
    estatisticas = obter(
        """
        SELECT (SELECT COUNT(*) FROM livros) AS titulos,
               (SELECT COUNT(*) FROM emprestimos WHERE data_devolucao IS NULL) AS abertos,
               (SELECT COUNT(*) FROM emprestimos
                 WHERE data_devolucao IS NULL AND data_prevista < CURDATE()) AS atrasados,
               (SELECT COUNT(*) FROM emprestimos
                 WHERE data_devolucao = CURDATE()) AS devolucoes_hoje,
               (SELECT COUNT(*) FROM reservas
                 WHERE status='aguardando') AS reservas_aguardando
        """
    )
    recentes = listar(
        """
        SELECT em.id_emprestimo, l.id_livro, u.nome, l.titulo, l.capa_url, em.data_emprestimo,
               em.data_prevista, em.data_devolucao, em.multa
          FROM emprestimos em
          JOIN usuarios u ON u.id_usuario = em.id_usuario
          JOIN exemplares ex ON ex.id_exemplar = em.id_exemplar
          JOIN livros l ON l.id_livro = ex.id_livro
         ORDER BY em.id_emprestimo DESC LIMIT 6
        """
    )
    categorias = listar(
        """SELECT DISTINCT categoria FROM livros
            WHERE categoria IS NOT NULL AND categoria <> ''
            ORDER BY categoria"""
    )
    categoria = request.args.get("categoria", "").strip()
    if categoria and categoria not in {item["categoria"] for item in categorias}:
        categoria = ""
    amostras = listar(
        """SELECT id_livro, titulo, categoria, capa_url FROM (
             SELECT l.id_livro, l.titulo, l.categoria, l.capa_url,
                    ROW_NUMBER() OVER (PARTITION BY l.categoria ORDER BY l.id_livro DESC) AS posicao
               FROM livros l WHERE l.categoria IS NOT NULL AND l.categoria <> ''
           ) por_categoria WHERE posicao <= 3
           ORDER BY categoria, posicao"""
    )
    capas_por_categoria = {}
    for amostra in amostras:
        capas_por_categoria.setdefault(amostra["categoria"], []).append(amostra)
    return render_template(
        "index.html",
        estatisticas=estatisticas,
        recentes=recentes,
        categorias=categorias,
        capas_por_categoria=capas_por_categoria,
        categoria_selecionada=categoria,
        destaques=consultar_estante("populares", categoria or None),
        novidades=consultar_estante("recentes", categoria or None),
        mais_emprestados=consultar_estante("populares", categoria or None),
        classicos=consultar_estante("classicos", categoria or None),
        mais_desejados=consultar_estante("desejados", categoria or None),
    )


@app.route("/buscar")
def busca_global():
    busca = request.args.get("q", "").strip()
    livros = []
    leitores = []
    if busca:
        termo = f"%{busca}%"
        livros = listar(
            """SELECT l.id_livro, l.titulo, l.categoria, l.capa_url,
                      (SELECT GROUP_CONCAT(a.nome ORDER BY a.nome SEPARATOR ', ')
                         FROM livro_autor la JOIN autores a ON a.id_autor=la.id_autor
                        WHERE la.id_livro=l.id_livro) AS autores
                 FROM livros l
                WHERE l.titulo LIKE %s OR l.isbn LIKE %s OR EXISTS (
                  SELECT 1 FROM livro_autor la JOIN autores a ON a.id_autor=la.id_autor
                   WHERE la.id_livro=l.id_livro AND a.nome LIKE %s
                )
                ORDER BY l.titulo LIMIT 30""",
            (termo, termo, termo),
        )
        leitores = listar(
            """SELECT id_usuario, nome, email FROM usuarios
                WHERE nome LIKE %s OR email LIKE %s
                ORDER BY nome LIMIT 20""",
            (termo, termo),
        )
    return render_template("busca.html", busca=busca, livros=livros, leitores=leitores)


@app.route("/livros")
def livros():
    busca = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    autor = request.args.get("autor", "").strip()
    disponibilidade = request.args.get("disponibilidade", "").strip()
    ano = request.args.get("ano", "").strip()
    ordem = request.args.get("ordem", "titulo")
    pagina = max(request.args.get("pagina", 1, type=int), 1)
    ordenar_por = {
        "titulo": "l.titulo ASC",
        "titulo_desc": "l.titulo DESC",
        "ano": "l.ano_publicacao DESC, l.titulo ASC",
        "ano_asc": "l.ano_publicacao ASC, l.titulo ASC",
    }.get(ordem, "l.titulo ASC")

    where = []
    params = []
    if busca:
        termo = f"%{busca}%"
        where.append(
            "(l.titulo LIKE %s OR l.isbn LIKE %s OR l.categoria LIKE %s "
            "OR l.editora LIKE %s OR EXISTS (SELECT 1 FROM livro_autor la "
            "JOIN autores a ON a.id_autor = la.id_autor "
            "WHERE la.id_livro = l.id_livro AND a.nome LIKE %s))"
        )
        params.extend([termo] * 5)
    if categoria:
        where.append("l.categoria = %s")
        params.append(categoria)
    if autor:
        where.append(
            "EXISTS (SELECT 1 FROM livro_autor la JOIN autores a ON a.id_autor = la.id_autor "
            "WHERE la.id_livro = l.id_livro AND a.id_autor = %s)"
        )
        params.append(autor)
    if disponibilidade == "disponivel":
        where.append("EXISTS (SELECT 1 FROM exemplares e WHERE e.id_livro=l.id_livro AND e.status='disponivel')")
    elif disponibilidade == "indisponivel":
        where.append("NOT EXISTS (SELECT 1 FROM exemplares e WHERE e.id_livro=l.id_livro AND e.status='disponivel')")
    if ano:
        if ano.isdigit():
            where.append("l.ano_publicacao = %s")
            params.append(int(ano))
        else:
            flash("Use um ano válido no filtro.", "erro")

    condicao = " WHERE " + " AND ".join(where) if where else ""
    total_row = obter(
        f"SELECT COUNT(*) AS total FROM livros l{condicao}",
        tuple(params),
    )
    total = total_row["total"]
    total_paginas = max((total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA, 1)
    pagina = min(pagina, total_paginas)
    itens = listar(
        f"""
        SELECT l.id_livro, l.titulo, l.categoria, l.ano_publicacao, l.isbn,
               l.editora, l.descricao, l.capa_url,
               (SELECT GROUP_CONCAT(a.nome ORDER BY a.nome SEPARATOR ', ')
                  FROM livro_autor la JOIN autores a ON a.id_autor=la.id_autor
                 WHERE la.id_livro=l.id_livro) AS autores,
               (SELECT COUNT(*) FROM exemplares e WHERE e.id_livro=l.id_livro) AS total,
               (SELECT COUNT(*) FROM exemplares e
                 WHERE e.id_livro=l.id_livro AND e.status='disponivel') AS disponiveis
          FROM livros l{condicao}
         ORDER BY {ordenar_por} LIMIT %s OFFSET %s
        """,
        tuple(params + [ITENS_POR_PAGINA, (pagina - 1) * ITENS_POR_PAGINA]),
    )
    return render_template(
        "livros.html",
        livros=itens,
        categorias=listar("SELECT DISTINCT categoria FROM livros WHERE categoria IS NOT NULL AND categoria <> '' ORDER BY categoria"),
        autores=autores_formulario(),
        filtros={
            "q": busca,
            "categoria": categoria,
            "autor": autor,
            "disponibilidade": disponibilidade,
            "ano": ano,
            "ordem": ordem,
        },
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
    )


@app.route("/livros/novo", methods=["GET", "POST"])
def novo_livro():
    if request.method == "POST":
        try:
            titulo, categoria, ano, isbn, editora, descricao, capa, autores, quantidade = campos_livro(request.form)
            with conectar() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """INSERT INTO livros
                           (titulo, categoria, ano_publicacao, isbn, editora, descricao, capa_url)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (titulo, categoria, ano, isbn, editora, descricao, capa),
                    )
                    id_livro = cur.lastrowid
                    salvar_autores(cur, id_livro, autores)
                    for _ in range(quantidade):
                        cur.execute(
                            "INSERT INTO exemplares (id_livro, status) VALUES (%s, 'disponivel')",
                            (id_livro,),
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    cur.close()
            flash("Livro cadastrado com sucesso.", "ok")
            return redirect(url_for("detalhe_livro", id_livro=id_livro))
        except ValueError as exc:
            flash(str(exc), "erro")
    return formulario_livro()


@app.route("/livros/<int:id_livro>")
def detalhe_livro(id_livro):
    return render_template("livro_detalhe.html", livro=dados_livro(id_livro))


@app.route("/livros/<int:id_livro>/editar", methods=["GET", "POST"])
def editar_livro(id_livro):
    livro = dados_livro(id_livro)
    if request.method == "POST":
        try:
            titulo, categoria, ano, isbn, editora, descricao, capa, autores, quantidade = campos_livro(request.form)
            with conectar() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT COUNT(*) FROM exemplares WHERE id_livro=%s AND status <> 'disponivel'",
                        (id_livro,),
                    )
                    emprestados = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM exemplares WHERE id_livro=%s", (id_livro,))
                    total_atual = cur.fetchone()[0]
                    if quantidade < emprestados:
                        raise ValueError(f"Não é possível reduzir para menos de {emprestados} exemplares emprestados.")
                    cur.execute(
                        """UPDATE livros SET titulo=%s, categoria=%s, ano_publicacao=%s,
                           isbn=%s, editora=%s, descricao=%s, capa_url=%s WHERE id_livro=%s""",
                        (titulo, categoria, ano, isbn, editora, descricao, capa, id_livro),
                    )
                    salvar_autores(cur, id_livro, autores)
                    if quantidade > total_atual:
                        for _ in range(quantidade - total_atual):
                            cur.execute(
                                "INSERT INTO exemplares (id_livro, status) VALUES (%s, 'disponivel')",
                                (id_livro,),
                            )
                    elif quantidade < total_atual:
                        cur.execute(
                            """DELETE FROM exemplares WHERE id_livro=%s AND status='disponivel'
                               ORDER BY id_exemplar DESC LIMIT %s""",
                            (id_livro, total_atual - quantidade),
                        )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    cur.close()
            flash("Livro atualizado.", "ok")
            return redirect(url_for("detalhe_livro", id_livro=id_livro))
        except ValueError as exc:
            flash(str(exc), "erro")
            livro = dados_livro(id_livro)
            livro.update(request.form)
    return formulario_livro(livro)


@app.route("/livros/<int:id_livro>/excluir", methods=["POST"])
def excluir_livro(id_livro):
    dados_livro(id_livro)
    relacao = obter(
        """SELECT COUNT(*) AS total FROM emprestimos em
           JOIN exemplares ex ON ex.id_exemplar=em.id_exemplar WHERE ex.id_livro=%s""",
        (id_livro,),
    )
    if relacao["total"]:
        flash("Este livro possui histórico de empréstimos e não pode ser excluído.", "erro")
    else:
        with conectar() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM livro_autor WHERE id_livro=%s", (id_livro,))
                cur.execute("DELETE FROM exemplares WHERE id_livro=%s", (id_livro,))
                cur.execute("DELETE FROM livros WHERE id_livro=%s", (id_livro,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
        flash("Livro excluído.", "ok")
    return redirect(url_for("livros"))


@app.route("/leitores")
def leitores():
    busca = request.args.get("q", "").strip()
    termo = f"%{busca}%"
    itens = listar(
        """SELECT u.id_usuario, u.nome, u.email, u.telefone,
                  (SELECT COUNT(*) FROM emprestimos em WHERE em.id_usuario=u.id_usuario
                    AND em.data_devolucao IS NULL) AS emprestimos_abertos
             FROM usuarios u WHERE u.nome LIKE %s OR u.email LIKE %s
            ORDER BY u.nome""",
        (termo, termo),
    )
    return render_template("leitores.html", leitores=itens, busca=busca)


@app.route("/leitores/novo", methods=["GET", "POST"])
def novo_leitor():
    if request.method == "POST":
        try:
            nome, email, telefone = campos_leitor(request.form)
            executar(
                "INSERT INTO usuarios (nome, email, telefone) VALUES (%s, %s, %s)",
                (nome, email, telefone),
            )
            flash("Leitor cadastrado.", "ok")
            return redirect(url_for("leitores"))
        except ValueError as exc:
            flash(str(exc), "erro")
    return render_template("leitor_form.html", leitor={}, editando=False)


@app.route("/leitores/<int:id_usuario>/editar", methods=["GET", "POST"])
def editar_leitor(id_usuario):
    leitor = obter("SELECT * FROM usuarios WHERE id_usuario=%s", (id_usuario,))
    if not leitor:
        abort(404)
    if request.method == "POST":
        try:
            nome, email, telefone = campos_leitor(request.form)
            executar(
                "UPDATE usuarios SET nome=%s, email=%s, telefone=%s WHERE id_usuario=%s",
                (nome, email, telefone, id_usuario),
            )
            flash("Cadastro atualizado.", "ok")
            return redirect(url_for("leitores"))
        except ValueError as exc:
            flash(str(exc), "erro")
            leitor.update(request.form)
    return render_template("leitor_form.html", leitor=leitor, editando=True)


@app.route("/leitores/<int:id_usuario>/excluir", methods=["POST"])
def excluir_leitor(id_usuario):
    leitor = obter("SELECT id_usuario FROM usuarios WHERE id_usuario=%s", (id_usuario,))
    if not leitor:
        abort(404)
    historico = obter("SELECT COUNT(*) AS total FROM emprestimos WHERE id_usuario=%s", (id_usuario,))
    if historico["total"]:
        flash("Este leitor possui histórico de empréstimos e não pode ser excluído.", "erro")
    else:
        executar("DELETE FROM usuarios WHERE id_usuario=%s", (id_usuario,))
        flash("Leitor excluído.", "ok")
    return redirect(url_for("leitores"))


@app.route("/emprestimos")
def emprestimos():
    abertos = listar(
        """
        SELECT em.id_emprestimo, u.nome, l.titulo, em.data_emprestimo,
               em.data_prevista, em.data_prevista < CURDATE() AS atrasado,
               DATEDIFF(CURDATE(), em.data_prevista) AS dias_atraso
          FROM emprestimos em
          JOIN usuarios u ON u.id_usuario=em.id_usuario
          JOIN exemplares ex ON ex.id_exemplar=em.id_exemplar
          JOIN livros l ON l.id_livro=ex.id_livro
         WHERE em.data_devolucao IS NULL ORDER BY em.data_prevista, l.titulo
        """
    )
    leitores_disponiveis = listar("SELECT id_usuario, nome FROM usuarios ORDER BY nome")
    exemplares = listar(
        """SELECT ex.id_exemplar, ex.id_livro, l.titulo FROM exemplares ex
           JOIN livros l ON l.id_livro=ex.id_livro
          WHERE ex.status='disponivel' ORDER BY l.titulo"""
    )
    return render_template(
        "emprestimos.html",
        abertos=abertos,
        usuarios=leitores_disponiveis,
        exemplares=exemplares,
        prazo=PRAZO_DIAS,
    )


@app.route("/emprestar", methods=["POST"])
def emprestar():
    try:
        id_usuario = int(request.form.get("id_usuario", ""))
        id_exemplar = int(request.form.get("id_exemplar", ""))
    except ValueError:
        flash("Selecione um leitor e um exemplar válidos.", "erro")
        return redirect(url_for("emprestimos"))
    hoje = date.today()
    prevista = hoje + timedelta(days=PRAZO_DIAS)
    with conectar() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT status FROM exemplares WHERE id_exemplar=%s FOR UPDATE", (id_exemplar,))
            exemplar = cur.fetchone()
            cur.execute("SELECT id_usuario FROM usuarios WHERE id_usuario=%s", (id_usuario,))
            usuario = cur.fetchone()
            if not exemplar or exemplar[0] != "disponivel" or not usuario:
                flash("O leitor ou exemplar não existe, ou o exemplar não está disponível.", "erro")
                conn.rollback()
            else:
                cur.execute(
                    """INSERT INTO emprestimos
                       (id_usuario, id_exemplar, data_emprestimo, data_prevista)
                       VALUES (%s, %s, %s, %s)""",
                    (id_usuario, id_exemplar, hoje, prevista),
                )
                cur.execute("UPDATE exemplares SET status='emprestado' WHERE id_exemplar=%s", (id_exemplar,))
                conn.commit()
                flash(f"Empréstimo registrado. Devolução até {prevista:%d/%m/%Y}.", "ok")
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    return redirect(url_for("emprestimos"))


@app.route("/devolver/<int:id_emprestimo>", methods=["POST"])
def devolver(id_emprestimo):
    with conectar() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """SELECT id_exemplar, data_prevista FROM emprestimos
                   WHERE id_emprestimo=%s AND data_devolucao IS NULL FOR UPDATE""",
                (id_emprestimo,),
            )
            linha = cur.fetchone()
            if linha is None:
                flash("Empréstimo não encontrado ou já devolvido.", "erro")
                conn.rollback()
            else:
                id_exemplar, prevista = linha
                hoje = date.today()
                dias_atraso = max((hoje - prevista).days, 0)
                multa = dias_atraso * MULTA_POR_DIA
                cur.execute(
                    "UPDATE emprestimos SET data_devolucao=%s, multa=%s WHERE id_emprestimo=%s",
                    (hoje, multa, id_emprestimo),
                )
                cur.execute("UPDATE exemplares SET status='disponivel' WHERE id_exemplar=%s", (id_exemplar,))
                conn.commit()
                if multa:
                    flash(f"Devolvido com {dias_atraso} dia(s) de atraso. Multa: R$ {multa:.2f}.", "erro")
                else:
                    flash("Livro devolvido no prazo.", "ok")
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    return redirect(request.referrer or url_for("emprestimos"))


@app.route("/historico")
def historico():
    busca = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    periodo = request.args.get("periodo", "todos").strip()
    termo = f"%{busca}%"
    filtros_sql = ["(u.nome LIKE %s OR l.titulo LIKE %s)"]
    parametros = [termo, termo]
    if status == "aberto":
        filtros_sql.append("em.data_devolucao IS NULL AND em.data_prevista >= CURDATE()")
    elif status == "atrasado":
        filtros_sql.append("em.data_devolucao IS NULL AND em.data_prevista < CURDATE()")
    elif status == "devolvido":
        filtros_sql.append("em.data_devolucao IS NOT NULL")
    dias_periodo = {"30": 30, "90": 90, "365": 365}.get(periodo)
    if dias_periodo:
        filtros_sql.append("em.data_emprestimo >= %s")
        parametros.append(date.today() - timedelta(days=dias_periodo))
    else:
        periodo = "todos"
    movimentacoes = listar(
        f"""SELECT em.id_emprestimo, l.id_livro, l.capa_url, u.nome, l.titulo, em.data_emprestimo,
                  em.data_prevista, em.data_devolucao, em.multa,
                  em.data_devolucao IS NULL AS aberto,
                  (em.data_devolucao IS NULL AND em.data_prevista < CURDATE()) AS atrasado
             FROM emprestimos em
             JOIN usuarios u ON u.id_usuario=em.id_usuario
             JOIN exemplares ex ON ex.id_exemplar=em.id_exemplar
             JOIN livros l ON l.id_livro=ex.id_livro
            WHERE {' AND '.join(filtros_sql)}
            ORDER BY em.id_emprestimo DESC LIMIT 500""",
        tuple(parametros),
    )
    return render_template(
        "historico.html",
        movimentacoes=movimentacoes,
        busca=busca,
        status=status,
        periodo=periodo,
    )


@app.route("/multas")
def multas():
    registros = listar(
        """SELECT em.id_emprestimo, u.nome, l.titulo, em.data_prevista,
                  em.data_devolucao, em.multa,
                  CASE WHEN em.data_devolucao IS NULL AND em.data_prevista < CURDATE()
                       THEN DATEDIFF(CURDATE(), em.data_prevista) * %s
                       ELSE em.multa END AS valor_atual
             FROM emprestimos em
             JOIN usuarios u ON u.id_usuario=em.id_usuario
             JOIN exemplares ex ON ex.id_exemplar=em.id_exemplar
             JOIN livros l ON l.id_livro=ex.id_livro
            WHERE em.multa > 0 OR (em.data_devolucao IS NULL AND em.data_prevista < CURDATE())
            ORDER BY em.data_prevista""",
        (MULTA_POR_DIA,),
    )
    return render_template("multas.html", multas=registros, multa_por_dia=MULTA_POR_DIA)


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
