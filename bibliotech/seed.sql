USE bibliotech;

INSERT INTO livros (titulo, categoria, ano_publicacao, isbn, editora, descricao)
SELECT novos.titulo, novos.categoria, novos.ano_publicacao, novos.isbn, novos.editora, novos.descricao
FROM (
  SELECT 'Dom Casmurro' AS titulo, 'Literatura brasileira' AS categoria, 1899 AS ano_publicacao, NULL AS isbn, 'Companhia das Letras' AS editora, 'Um dos romances mais conhecidos de Machado de Assis, narrado por Bento Santiago.' AS descricao
  UNION ALL SELECT 'O Cortiço', 'Literatura brasileira', 1890, NULL, 'Companhia das Letras', 'Romance naturalista de Aluísio Azevedo sobre a vida em um cortiço carioca.'
  UNION ALL SELECT 'A Hora da Estrela', 'Literatura brasileira', 1977, NULL, 'Rocco', 'A trajetória de Macabéa, uma jovem nordestina vivendo no Rio de Janeiro.'
  UNION ALL SELECT 'O Hobbit', 'Fantasia', 1937, NULL, 'HarperCollins', 'Bilbo Bolseiro parte em uma jornada inesperada pela Terra-média.'
  UNION ALL SELECT 'Frankenstein', 'Terror e ficção científica', 1818, NULL, 'DarkSide Books', 'O clássico de Mary Shelley sobre criação, ciência e responsabilidade.'
  UNION ALL SELECT 'Assassinato no Expresso do Oriente', 'Suspense', 1934, NULL, 'L&PM', 'Hercule Poirot investiga um crime a bordo de um trem isolado pela neve.'
  UNION ALL SELECT 'Duna', 'Ficção científica', 1965, NULL, 'Aleph', 'Uma saga de intriga política e sobrevivência no planeta desértico Arrakis.'
  UNION ALL SELECT 'A Ilha do Tesouro', 'Aventura', 1883, NULL, 'Martin Claret', 'Aventura clássica de Robert Louis Stevenson em busca de um tesouro pirata.'
  UNION ALL SELECT 'O Pequeno Príncipe', 'Infantil', 1943, NULL, 'Agir', 'Uma fábula poética sobre amizade, afeto e olhar o mundo com imaginação.'
  UNION ALL SELECT 'Quarto de Despejo', 'Memórias', 1960, NULL, 'Ática', 'Diário de Carolina Maria de Jesus sobre a vida na favela do Canindé.'
  UNION ALL SELECT 'Orgulho e Preconceito', 'Romance', 1813, NULL, 'Martin Claret', 'Jane Austen retrata relações, escolhas e costumes da sociedade inglesa.'
  UNION ALL SELECT 'O Iluminado', 'Terror', 1977, NULL, 'Suma', 'Uma família passa o inverno isolada em um hotel com um passado sombrio.'
  UNION ALL SELECT 'Sapiens', 'História', 2011, NULL, 'Companhia das Letras', 'Uma síntese da história da humanidade, de Yuval Noah Harari.'
  UNION ALL SELECT 'Código Limpo', 'Tecnologia', 2008, NULL, 'Alta Books', 'Práticas e princípios para escrever software legível e sustentável.'
  UNION ALL SELECT 'Python Fluente', 'Programação', 2015, NULL, 'Novatec', 'Conceitos e recursos da linguagem Python apresentados em profundidade.'
  UNION ALL SELECT 'A Máquina do Tempo', 'Ficção científica', 1895, NULL, 'Principis', 'H. G. Wells imagina uma viagem para um futuro distante.'
  UNION ALL SELECT 'Coraline', 'Fantasia', 2002, NULL, 'Intrínseca', 'Uma menina encontra uma versão inquietante de sua própria casa.'
  UNION ALL SELECT 'Capitães da Areia', 'Literatura brasileira', 1937, NULL, 'Companhia das Letras', 'Jorge Amado narra a vida de um grupo de meninos em Salvador.'
  UNION ALL SELECT 'O Nome da Rosa', 'Suspense histórico', 1980, NULL, 'Record', 'Um frade investiga mortes misteriosas em uma abadia medieval.'
  UNION ALL SELECT 'A Bolsa Amarela', 'Infantil', 1976, NULL, 'Casa Lygia Bojunga', 'Uma menina guarda desejos e descobertas em uma bolsa amarela.'
) AS novos
WHERE NOT EXISTS (SELECT 1 FROM livros l WHERE l.titulo = novos.titulo);

INSERT IGNORE INTO autores (nome) VALUES
  ('Machado de Assis'), ('Aluísio Azevedo'), ('Clarice Lispector'), ('J. R. R. Tolkien'),
  ('Mary Shelley'), ('Agatha Christie'), ('Frank Herbert'), ('Robert Louis Stevenson'),
  ('Antoine de Saint-Exupéry'), ('Carolina Maria de Jesus'), ('Jane Austen'), ('Stephen King'),
  ('Yuval Noah Harari'), ('Robert C. Martin'), ('Luciano Ramalho'), ('H. G. Wells'),
  ('Neil Gaiman'), ('Jorge Amado'), ('Umberto Eco'), ('Lygia Bojunga');

INSERT IGNORE INTO livro_autor (id_livro, id_autor)
SELECT l.id_livro, a.id_autor
FROM (
  SELECT 'Dom Casmurro' titulo, 'Machado de Assis' autor
  UNION ALL SELECT 'O Cortiço', 'Aluísio Azevedo'
  UNION ALL SELECT 'A Hora da Estrela', 'Clarice Lispector'
  UNION ALL SELECT 'O Hobbit', 'J. R. R. Tolkien'
  UNION ALL SELECT 'Frankenstein', 'Mary Shelley'
  UNION ALL SELECT 'Assassinato no Expresso do Oriente', 'Agatha Christie'
  UNION ALL SELECT 'Duna', 'Frank Herbert'
  UNION ALL SELECT 'A Ilha do Tesouro', 'Robert Louis Stevenson'
  UNION ALL SELECT 'O Pequeno Príncipe', 'Antoine de Saint-Exupéry'
  UNION ALL SELECT 'Quarto de Despejo', 'Carolina Maria de Jesus'
  UNION ALL SELECT 'Orgulho e Preconceito', 'Jane Austen'
  UNION ALL SELECT 'O Iluminado', 'Stephen King'
  UNION ALL SELECT 'Sapiens', 'Yuval Noah Harari'
  UNION ALL SELECT 'Código Limpo', 'Robert C. Martin'
  UNION ALL SELECT 'Python Fluente', 'Luciano Ramalho'
  UNION ALL SELECT 'A Máquina do Tempo', 'H. G. Wells'
  UNION ALL SELECT 'Coraline', 'Neil Gaiman'
  UNION ALL SELECT 'Capitães da Areia', 'Jorge Amado'
  UNION ALL SELECT 'O Nome da Rosa', 'Umberto Eco'
  UNION ALL SELECT 'A Bolsa Amarela', 'Lygia Bojunga'
) rel
JOIN livros l ON l.titulo = rel.titulo
JOIN autores a ON a.nome = rel.autor;

INSERT INTO exemplares (id_livro, status)
SELECT l.id_livro, 'disponivel'
FROM livros l
JOIN (
  SELECT 'Dom Casmurro' titulo, 3 quantidade
  UNION ALL SELECT 'O Cortiço', 2
  UNION ALL SELECT 'A Hora da Estrela', 2
  UNION ALL SELECT 'O Hobbit', 3
  UNION ALL SELECT 'Frankenstein', 1
  UNION ALL SELECT 'Assassinato no Expresso do Oriente', 2
  UNION ALL SELECT 'Duna', 2
  UNION ALL SELECT 'A Ilha do Tesouro', 1
  UNION ALL SELECT 'O Pequeno Príncipe', 3
  UNION ALL SELECT 'Quarto de Despejo', 2
  UNION ALL SELECT 'Orgulho e Preconceito', 2
  UNION ALL SELECT 'O Iluminado', 2
  UNION ALL SELECT 'Sapiens', 1
  UNION ALL SELECT 'Código Limpo', 2
  UNION ALL SELECT 'Python Fluente', 2
  UNION ALL SELECT 'A Máquina do Tempo', 1
  UNION ALL SELECT 'Coraline', 2
  UNION ALL SELECT 'Capitães da Areia', 2
  UNION ALL SELECT 'O Nome da Rosa', 1
  UNION ALL SELECT 'A Bolsa Amarela', 2
) quantidades ON quantidades.titulo = l.titulo
WHERE NOT EXISTS (SELECT 1 FROM exemplares ex WHERE ex.id_livro = l.id_livro);
