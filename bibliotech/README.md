# BiblioTech

Sistema de gerenciamento de biblioteca em Flask e MySQL. Os registros existentes são mantidos pela migração aditiva; faça uma cópia de segurança antes de alterar o banco.

## Requisitos

- Python 3.10 ou superior
- MySQL 8.0 ou compatível

## Instalação

Abra o PowerShell nesta pasta e crie/ative um ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure o MySQL:

1. Para uma instalação nova, execute `schema.sql` no MySQL Workbench ou importe-o pelo PowerShell com `cmd /c "mysql -u root -p < schema.sql"`.
2. Para uma base criada pela versão anterior do BiblioTech, primeiro faça backup; depois execute `migration.sql` no Workbench ou com `cmd /c "mysql -u root -p bibliotech < migration.sql"`. A migração adiciona os campos ausentes e amplia tamanhos de colunas sem apagar cadastros.
3. Opcionalmente, execute `seed.sql` no Workbench ou com `cmd /c "mysql -u root -p bibliotech < seed.sql"` para incluir os livros de exemplo. O script não duplica livros existentes com os mesmos títulos e só cria exemplares quando o título ainda não possui exemplares.

## Configuração

Defina as variáveis de ambiente antes de iniciar. Exemplo no PowerShell (ajuste usuário, senha e chave):

```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "sua-senha-do-mysql"
$env:MYSQL_DATABASE = "bibliotech"
$env:SECRET_KEY = "use-uma-chave-aleatoria-longa"
$env:PRAZO_DIAS = "7"
$env:MULTA_POR_DIA = "1.00"
$env:FLASK_DEBUG = "false"
```

`MYSQL_PASSWORD` pode ficar vazio se o MySQL local não exigir senha. Não use a chave secreta de desenvolvimento em produção.

## Executar

Depois de executar `migration.sql` (ou `schema.sql` em uma instalação nova), crie a primeira conta administradora. O comando solicita o nome, usuário e senha sem exibir a senha na tela:

```powershell
python -m flask --app app criar-admin
```

Com o ambiente virtual ativado e as variáveis configuradas no mesmo terminal, inicie o sistema:

```powershell
python app.py
```

Abra <http://127.0.0.1:5000> e entre com a conta criada. Funcionários adicionais e suas permissões são gerenciados na opção **Equipe** por uma conta administradora. Reservas são registradas na fila e atendidas ou canceladas manualmente pela equipe. Os formulários protegidos usam token CSRF de sessão.

## Arquivos principais

- `app.py`: rotas Flask, validação e operações de biblioteca.
- `config.py`: configuração por variáveis de ambiente.
- `database.py`: conexão MySQL.
- `schema.sql`: estrutura para uma instalação nova.
- `migration.sql`: migração aditiva para a estrutura legada desta aplicação.
- `seed.sql`: conjunto opcional de livros demonstrativos.
- `templates/`: páginas HTML.
- `static/style.css` e `static/img/capa_padrao.svg`: estilos e capa genérica.
