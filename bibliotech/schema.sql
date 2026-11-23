CREATE DATABASE IF NOT EXISTS bibliotech
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE bibliotech;

CREATE TABLE IF NOT EXISTS livros (
  id_livro INT UNSIGNED NOT NULL AUTO_INCREMENT,
  titulo VARCHAR(255) NOT NULL,
  categoria VARCHAR(120) NULL,
  ano_publicacao SMALLINT UNSIGNED NULL,
  isbn VARCHAR(20) NULL,
  editora VARCHAR(180) NULL,
  descricao TEXT NULL,
  capa_url VARCHAR(1000) NULL,
  PRIMARY KEY (id_livro),
  KEY idx_livros_titulo (titulo),
  KEY idx_livros_categoria (categoria),
  KEY idx_livros_isbn (isbn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS autores (
  id_autor INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nome VARCHAR(180) NOT NULL,
  PRIMARY KEY (id_autor),
  UNIQUE KEY uq_autores_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS livro_autor (
  id_livro INT UNSIGNED NOT NULL,
  id_autor INT UNSIGNED NOT NULL,
  PRIMARY KEY (id_livro, id_autor),
  CONSTRAINT fk_livro_autor_livro FOREIGN KEY (id_livro)
    REFERENCES livros (id_livro) ON DELETE CASCADE,
  CONSTRAINT fk_livro_autor_autor FOREIGN KEY (id_autor)
    REFERENCES autores (id_autor) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS usuarios (
  id_usuario INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nome VARCHAR(180) NOT NULL,
  email VARCHAR(254) NULL,
  telefone VARCHAR(40) NULL,
  PRIMARY KEY (id_usuario),
  KEY idx_usuarios_nome (nome),
  KEY idx_usuarios_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS exemplares (
  id_exemplar INT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_livro INT UNSIGNED NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'disponivel',
  PRIMARY KEY (id_exemplar),
  KEY idx_exemplares_livro_status (id_livro, status),
  CONSTRAINT fk_exemplar_livro FOREIGN KEY (id_livro)
    REFERENCES livros (id_livro) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS emprestimos (
  id_emprestimo INT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_usuario INT UNSIGNED NOT NULL,
  id_exemplar INT UNSIGNED NOT NULL,
  data_emprestimo DATE NOT NULL,
  data_prevista DATE NOT NULL,
  data_devolucao DATE NULL,
  multa DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (id_emprestimo),
  KEY idx_emprestimos_abertos (data_devolucao, data_prevista),
  KEY idx_emprestimos_usuario (id_usuario),
  KEY idx_emprestimos_exemplar (id_exemplar),
  CONSTRAINT fk_emprestimo_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
  CONSTRAINT fk_emprestimo_exemplar FOREIGN KEY (id_exemplar)
    REFERENCES exemplares (id_exemplar) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bibliotecarios (
  id_bibliotecario INT UNSIGNED NOT NULL AUTO_INCREMENT,
  nome VARCHAR(180) NOT NULL,
  usuario VARCHAR(80) NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  administrador TINYINT(1) NOT NULL DEFAULT 0,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_bibliotecario),
  UNIQUE KEY uq_bibliotecarios_usuario (usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reservas (
  id_reserva INT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_usuario INT UNSIGNED NOT NULL,
  id_livro INT UNSIGNED NOT NULL,
  id_emprestimo INT UNSIGNED NULL,
  data_reserva DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) NOT NULL DEFAULT 'aguardando',
  PRIMARY KEY (id_reserva),
  KEY idx_reservas_fila (id_livro, status, data_reserva),
  KEY idx_reservas_usuario (id_usuario, status),
  CONSTRAINT fk_reserva_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuarios (id_usuario) ON DELETE RESTRICT,
  CONSTRAINT fk_reserva_livro FOREIGN KEY (id_livro)
    REFERENCES livros (id_livro) ON DELETE RESTRICT,
  CONSTRAINT fk_reserva_emprestimo FOREIGN KEY (id_emprestimo)
    REFERENCES emprestimos (id_emprestimo) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
