USE bibliotech;

DELIMITER $$
DROP PROCEDURE IF EXISTS bibliotech_add_column_if_missing$$
CREATE PROCEDURE bibliotech_add_column_if_missing(
  IN p_table VARCHAR(64),
  IN p_column VARCHAR(64),
  IN p_definition VARCHAR(255)
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM information_schema.columns
     WHERE table_schema = DATABASE()
       AND table_name = p_table
       AND column_name = p_column
  ) THEN
    SET @migration_sql = CONCAT(
      'ALTER TABLE `', REPLACE(p_table, '`', '``'),
      '` ADD COLUMN `', REPLACE(p_column, '`', '``'), '` ', p_definition
    );
    PREPARE migration_statement FROM @migration_sql;
    EXECUTE migration_statement;
    DEALLOCATE PREPARE migration_statement;
  END IF;
END$$
DELIMITER ;

CALL bibliotech_add_column_if_missing('livros', 'isbn', 'VARCHAR(20) NULL');
CALL bibliotech_add_column_if_missing('livros', 'editora', 'VARCHAR(180) NULL');
CALL bibliotech_add_column_if_missing('livros', 'descricao', 'TEXT NULL');
CALL bibliotech_add_column_if_missing('livros', 'capa_url', 'VARCHAR(1000) NULL');
CALL bibliotech_add_column_if_missing('usuarios', 'email', 'VARCHAR(254) NULL');
CALL bibliotech_add_column_if_missing('usuarios', 'telefone', 'VARCHAR(40) NULL');

DROP PROCEDURE bibliotech_add_column_if_missing;

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
  KEY idx_livro_autor_autor (id_autor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE livros
  MODIFY COLUMN titulo VARCHAR(255) NOT NULL,
  MODIFY COLUMN categoria VARCHAR(120) NULL;

ALTER TABLE autores
  MODIFY COLUMN nome VARCHAR(180) NOT NULL;

ALTER TABLE usuarios
  MODIFY COLUMN nome VARCHAR(180) NOT NULL,
  MODIFY COLUMN email VARCHAR(254) NULL,
  MODIFY COLUMN telefone VARCHAR(40) NULL;

CREATE TABLE IF NOT EXISTS bibliotecarios (
  id_bibliotecario INT NOT NULL AUTO_INCREMENT,
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
  id_reserva INT NOT NULL AUTO_INCREMENT,
  id_usuario INT NOT NULL,
  id_livro INT NOT NULL,
  id_emprestimo INT NULL,
  data_reserva DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(20) NOT NULL DEFAULT 'aguardando',
  PRIMARY KEY (id_reserva),
  KEY idx_reservas_fila (id_livro, status, data_reserva),
  KEY idx_reservas_usuario (id_usuario, status),
  KEY idx_reservas_emprestimo (id_emprestimo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
