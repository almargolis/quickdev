# QuickDev Quickstart: Build Your First Application

This guide walks you through building a multi-user todo application using QuickDev. By the end, you'll have a working app with a REST API, web forms, and MCP server access — all generated from a single data definition file.

## Prerequisites

- Python 3.10+
- Familiarity with Python and basic SQL concepts
- No Flask experience required (QuickDev generates the Flask code for you)

## Step 1: Define Your Data

The foundation of every QuickDev application is a **pdict data specification**. This is a Python module that describes your database tables using `pdict` objects from `qdbase`. Everything else — the database schema, REST API endpoints, web forms, and MCP tools — is generated from this single definition.

Create a file called `data_spec.py`:

```python
from qdbase import pdict

db_dict = pdict.DbDictDb()

# --- people table ---
people = db_dict.add_table(pdict.DbDictTable("people"))
people.add_column(pdict.Text("name",
    is_create_required=True,
    max_length=100,
    rest_label="Full Name"))
people.add_column(pdict.Text("email",
    is_create_required=True,
    max_length=200,
    is_unique=True,
    rest_label="Email Address"))
people.add_column(pdict.Text("role",
    default_value="member",
    choices=["admin", "member"],
    rest_label="Role"))
people.add_index("idx_people_email", column_names="email", is_unique=True)

# --- tasks table ---
tasks = db_dict.add_table(pdict.DbDictTable("tasks"))
tasks.add_column(pdict.Text("title",
    is_create_required=True,
    max_length=200,
    rest_label="Task Title"))
tasks.add_column(pdict.Text("description",
    max_length=2000,
    allow_nulls=True,
    form_widget="textarea",
    rest_label="Description"))
tasks.add_column(pdict.Text("status",
    default_value="todo",
    choices=["todo", "in_progress", "done"],
    is_filterable=True,
    rest_label="Status"))
tasks.add_column(pdict.Text("priority",
    default_value="medium",
    choices=["low", "medium", "high"],
    is_filterable=True,
    is_sortable=True,
    rest_label="Priority"))
tasks.add_column(pdict.Number("assigned_to",
    foreign_key=pdict.ForeignKey(people.columns["id"]),
    allow_nulls=True,
    is_filterable=True,
    rest_label="Assigned To"))
tasks.add_column(pdict.TimeStamp("due_date",
    allow_nulls=True,
    is_sortable=True,
    rest_label="Due Date"))
tasks.add_column(pdict.TimeStamp("created_at",
    default_value=pdict.ColumnName("CURRENT_TIMESTAMP"),
    is_read_only=True,
    is_sortable=True,
    rest_label="Created"))
```

### What's happening here

**`DbDictDb`** is a container for all your tables. It can generate the full set of SQL `CREATE TABLE` statements with `db_dict.sql_create_list()`.

**`DbDictTable`** defines a table. By default, `is_rowid_table=True` adds an auto-increment `id` column as the primary key.

**Column types** map to SQLite types:
- `Text` — TEXT with NOCASE collation
- `Number` — INTEGER
- `TimeStamp` — TIMESTAMP

**Each column has two kinds of metadata:**

1. **Database metadata** controls the SQL schema:
   - `allow_nulls` — whether the column accepts NULL (default: `False`)
   - `is_unique` — adds a UNIQUE constraint
   - `default_value` — default value in the schema. Use `pdict.ColumnName("CURRENT_TIMESTAMP")` for SQL expressions that should not be quoted.

2. **REST/form metadata** controls how qdrestful and qdforms present the column:
   - `is_create_required` — the field must be provided when creating a record
   - `choices` — restricts values to a list; renders as a dropdown in forms
   - `form_widget` — overrides the auto-detected form widget (e.g., `"textarea"`)
   - `is_filterable` / `is_sortable` — enables filtering and sorting in the API
   - `rest_label` — human-readable label for forms and MCP tool descriptions
   - `max_length`, `min_length`, `max_value`, `min_value` — validation constraints
   - `is_read_only` — the field cannot be set via API (e.g., auto-generated timestamps)

**Foreign keys** link tables together. `tasks.assigned_to` references `people.id`, so every task can be assigned to a person. In the web forms, this will render as a popup lookup.

### Verify your data spec

You can verify that your definitions produce valid SQL:

```python
python3 -c "
from data_spec import db_dict
for sql in db_dict.sql_create_list():
    print(sql)
"
```

This should output `CREATE TABLE` statements for both tables, a `CREATE INDEX` for the email index, and a `FOREIGN KEY` clause on the tasks table.

## Step 2: Create Your API

With your data spec defined, you can stand up a full REST API by writing a small Flask app factory. The `qdrestful` package reads your pdict definitions and auto-generates CRUD endpoints for every table.

### Install dependencies

```bash
pip install flask flask-login flask-sqlalchemy
pip install -e /path/to/quickdev/qdbase
pip install -e /path/to/qdflask-repo/qdflask
pip install -e /path/to/qdflask-repo/qdflaskauth
pip install -e /path/to/qdflask-repo/qdflaskapi
pip install -e /path/to/qdflask-repo/qdrestful
```

### Write the app factory

Create `app.py`:

```python
from flask import Flask

from qdflask import init_qdflask
from qdflaskauth import init_qdflaskauth
from qdflaskapi import init_qdflaskapi
from qdrestful import init_qdrestful

from data_spec import db_dict


def create_app(config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///passwords.db'
    app.config['QDRESTFUL_DB_DICT'] = db_dict

    if config:
        app.config.update(config)

    # Initialize in priority order
    init_qdflask(app)
    init_qdflaskauth(app, roles=['admin', 'member'])
    init_qdflaskapi(app, config={'enabled': True})
    init_qdrestful(app, config={
        'enabled': True,
        'db_type': 'sqlite',
        'sqlite_fpath': 'todo_data.db',
        'url_prefix': '/api',
    })

    @app.route('/')
    def index():
        return {'status': 'ok', 'tables': list(db_dict.tables.keys())}

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5555)
```

### What this gives you

The key line is `app.config['QDRESTFUL_DB_DICT'] = db_dict`. When `init_qdrestful()` runs, it reads your pdict definitions and generates these endpoints for **each table**:

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/{table}` | List records (paginated, filterable, sortable) |
| `GET` | `/api/{table}/{id}` | Get a single record |
| `POST` | `/api/{table}` | Create a record |
| `PUT` | `/api/{table}/{id}` | Full update |
| `PATCH` | `/api/{table}/{id}` | Partial update |
| `DELETE` | `/api/{table}/{id}` | Delete a record |
| `GET` | `/api/{table}/_schema` | Table schema (columns, types, constraints) |

### Initialization order matters

The packages must be initialized in priority order:

1. **qdflask** (priority 10) — SQLAlchemy database and User model
2. **qdflaskauth** (priority 15) — Flask-Login and role-based access
3. **qdflaskapi** (priority 25) — API key authentication
4. **qdrestful** (priority 30) — REST API from pdict

Each layer builds on the previous one. All REST endpoints require authentication (session login or API key).

### Try it out

Start the server:

```bash
python app.py
```

Log in as the auto-created admin user (username: `admin`, password: `admin`):

```bash
# Log in (saves session cookie)
curl -c cookies.txt -X POST http://localhost:5555/auth/login \
  -d 'username=admin&password=admin' -L
```

Then use the API:

```bash
# Create a person
curl -b cookies.txt -X POST http://localhost:5555/api/people \
  -H 'Content-Type: application/json' \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# Create a task assigned to that person
curl -b cookies.txt -X POST http://localhost:5555/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title": "Write docs", "priority": "high", "assigned_to": 1}'

# List tasks, filtered by status
curl -b cookies.txt 'http://localhost:5555/api/tasks?status=todo'

# Sort tasks by priority (descending)
curl -b cookies.txt 'http://localhost:5555/api/tasks?sort=-priority'

# Update a task's status
curl -b cookies.txt -X PATCH http://localhost:5555/api/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"status": "done"}'
```

### What pdict metadata controls

Your column metadata from Step 1 is enforced automatically:

- **`is_create_required`** — POST returns 400 if the field is missing
- **`choices`** — POST/PUT/PATCH return 400 for values not in the list
- **`is_read_only`** — PATCH/PUT return 400 if you try to set the field
- **`is_filterable`** — the column can be used as a query parameter on GET
- **`is_sortable`** — the column can be used in the `sort` parameter
- **`max_length`** — enforced on create and update
- **Foreign keys** — enforced by SQLite; invalid references return 400
- **`is_unique`** — enforced by SQLite; duplicates return 400

### Two databases

Notice the app has two database configurations:

- `SQLALCHEMY_DATABASE_URI` — used by qdflask for user accounts and auth (SQLAlchemy)
- `sqlite_fpath` in the qdrestful config — used for your application data (qdsqlite)

This separation is intentional: the auth system uses SQLAlchemy, while your business data uses qdsqlite (driven by pdict). They don't interfere with each other.

## Step 3: Add Web Forms

The `qdforms` package reads the same pdict definitions and generates web-based list views and CRUD forms for every table. It uses JavaScript to call the REST API you set up in Step 2 — no additional backend code needed.

### Add qdforms to your app

Install qdforms:

```bash
pip install -e /path/to/qdflask-repo/qdforms
```

Add two lines to `app.py`:

```python
from qdforms import init_qdforms

# After init_qdrestful (priority 35):
init_qdforms(app, config={
    'enabled': True,
    'url_prefix': '/forms',
})
```

That's it. No templates to write, no form classes to define.

### What you get

Browse to `http://localhost:5555/forms/` after starting the app. You'll see:

- **Index page** — cards linking to each table's list view
- **List views** — paginated tables with column sorting and a delete button per row
- **Add forms** — one per table, with the correct input widgets
- **Edit forms** — pre-populated with the record's current values, plus a Delete button
- **FK popup** — click "Browse..." on a foreign key field to search and select from the related table

### How pdict drives the forms

Your column metadata from Step 1 controls which HTML widget each field uses:

| pdict definition | Form widget |
|-----------------|-------------|
| `Text` | `<input type="text">` |
| `Text` with `max_length > 200` | `<textarea>` |
| `Text` with `form_widget="textarea"` | `<textarea>` (explicit override) |
| `Text` or `Number` with `choices=[...]` | `<select>` dropdown |
| `Number` | `<input type="number">` |
| `TimeStamp` | `<input type="datetime-local">` |
| Column with `foreign_key` | Number input + "Browse..." button |
| Column with `is_read_only=True` | Display-only (no input) |

Other metadata carries through to the HTML:

- `is_create_required` adds a `*` required marker and the `required` attribute
- `max_length` sets the HTML `maxlength` attribute
- `min_value` / `max_value` set `min` / `max` on number inputs
- `rest_label` becomes the field label (falls back to the column name)
- `placeholder` sets the HTML placeholder text

### Customizing per-table

You can optionally control which columns appear and in what order:

```python
app.config['QDFORMS_TABLE_CONFIGS'] = {
    'tasks': {
        'title': 'Task Tracker',              # Page title
        'list_columns': ['title', 'status', 'priority', 'assigned_to'],
        'form_columns': ['title', 'description', 'status', 'priority',
                         'assigned_to', 'due_date'],
        'display_column': 'title',            # Shown in FK popups
        'default_sort': '-priority',          # Default list sort
        'per_page': 50,                       # Rows per page
    },
}
```

If you don't provide `QDFORMS_TABLE_CONFIGS`, all columns are shown in definition order.

### Architecture note

qdforms is a pure UI layer. It has no database access of its own. All data operations go through qdrestful's REST API via browser JavaScript:

```
Browser → qdforms HTML/JS → fetch('/api/tasks') → qdrestful → qdsqlite → SQLite
```

This means validation happens in two places: client-side in the browser (from the HTML attributes) and server-side in qdrestful (from the pdict metadata). Both are driven by the same pdict definitions.

## Step 4: Add Authentication

If you followed Step 2, authentication is already wired in. The `app.py` you created calls `init_qdflaskauth()` and `init_qdflaskapi()`, which set up session-based login and API key authentication. All REST endpoints and web forms require authentication — no additional code needed.

This step explains what those packages do and how to use them.

### What you get automatically

When the app starts for the first time, `init_qdflaskauth()` creates an admin user (`admin`/`admin`) if no users exist. You'll see this in the console:

```
Created initial admin user (admin/admin) - change password after first login
```

The authentication stack provides:

| Feature | Package | What it does |
|---------|---------|--------------|
| **User model** | qdflask | `User` table in SQLAlchemy with username, password hash, role |
| **Login/logout** | qdflaskauth | `/auth/login` and `/auth/logout` routes with session cookies |
| **User management** | qdflaskauth | `/auth/users` admin page to add, edit, and deactivate users |
| **Role-based access** | qdflaskauth | Each user has a role (e.g., `admin`, `member`) |
| **API keys** | qdflaskapi | Bearer token authentication for programmatic API access |

### Two authentication paths

Every qdrestful endpoint accepts either form of authentication:

1. **Session login** — Log in at `/auth/login`, and the session cookie authenticates subsequent requests. Used by browsers and qdforms.

2. **API key (Bearer token)** — Send an `Authorization: Bearer <key>` header. Used by scripts, CI/CD, and AI agents.

```
Browser → /auth/login → session cookie → /api/tasks → qdrestful
Script  → Authorization: Bearer <key>  → /api/tasks → qdrestful
```

If neither is present, the endpoint returns `401 Authentication required`.

### Try session authentication

Start the app and log in:

```bash
python app.py
```

```bash
# Log in (saves session cookie)
curl -c cookies.txt -X POST http://localhost:5555/auth/login \
  -d 'username=admin&password=admin' -L

# Use the session cookie for API calls
curl -b cookies.txt http://localhost:5555/api/tasks

# Log out
curl -b cookies.txt http://localhost:5555/auth/logout -L
```

Or open `http://localhost:5555/auth/login` in a browser.

### Try API key authentication

API keys are managed through the REST API (session login required to generate them):

```bash
# Log in first
curl -c cookies.txt -X POST http://localhost:5555/auth/login \
  -d 'username=admin&password=admin' -L

# Generate an API key
curl -b cookies.txt -X POST http://localhost:5555/api/keys \
  -H 'Content-Type: application/json' \
  -d '{"purpose": "CLI access"}'
# Response: {"id": 1, "key": "abc123...", "purpose": "CLI access", ...}
```

Save the `key` value — it's only shown once. Then use it without a session:

```bash
# Use Bearer token (no cookies needed)
curl -H 'Authorization: Bearer abc123...' \
  http://localhost:5555/api/tasks

# Create a record via API key
curl -H 'Authorization: Bearer abc123...' \
  -H 'Content-Type: application/json' \
  -X POST http://localhost:5555/api/people \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

### Managing users

The admin can manage users at `/auth/users` (browser login required):

- **Add users** — Set username, password, role, and API key permission
- **Edit users** — Change role, reset password, toggle API key generation
- **Deactivate users** — Deactivated users cannot log in or use API keys

Roles are defined in your `init_qdflaskauth()` call:

```python
init_qdflaskauth(app, roles=['admin', 'member'])
```

By default, all authenticated users (any role) can read and write all tables. To restrict access by role, use `QDRESTFUL_TABLE_CONFIGS`:

```python
app.config['QDRESTFUL_TABLE_CONFIGS'] = {
    'people': {
        'read_roles': ['admin', 'member'],
        'write_roles': ['admin'],         # only admins can create/edit people
        'delete_roles': ['admin'],        # only admins can delete people
    },
}
```

### API key permissions

By default, only users explicitly granted permission can generate API keys. The auto-created admin user has this permission. For other users, the admin can toggle it in the user management UI.

To let all users generate keys, change the qdflaskapi config:

```python
init_qdflaskapi(app, config={
    'enabled': True,
    'all_users_can_generate_api_keys': True,
})
```

### API key management endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/keys` | List your API keys (admins can filter by `?user_id=N`) |
| `POST` | `/api/keys` | Generate a new key. Body: `{"purpose": "...", "expires_at": "ISO8601"}` |
| `POST` | `/api/keys/{id}/hold` | Suspend a key (status → hold) |
| `POST` | `/api/keys/{id}/activate` | Reactivate a held key |
| `DELETE` | `/api/keys/{id}` | Permanently delete a key |

### How it fits together

The full `app.py` from Step 2 already includes all the auth wiring. Here's the initialization order and what each layer adds:

```python
init_qdflask(app)                              # 1. SQLAlchemy + User model
init_qdflaskauth(app, roles=['admin', 'member']) # 2. Login + roles
init_qdflaskapi(app, config={'enabled': True})   # 3. API keys
init_qdrestful(app, config={...})                # 4. REST API (auth-protected)
init_qdforms(app, config={...})                  # 5. Web forms (login-protected)
```

Each layer builds on the previous one. The order matters — qdrestful needs qdflaskauth and qdflaskapi to be initialized first so its endpoints can check for valid sessions and API keys.

## Step 5: Enable MCP for AI Agents

The `qdrestful` package includes a built-in MCP (Model Context Protocol) server that exposes your pdict tables as tools. AI agents — such as Claude in Claude Desktop or any MCP-compatible client — can use these tools to read and write your application data.

The MCP server generates tools directly from the same pdict definitions you created in Step 1. No additional configuration or tool definitions needed.

### What tools are generated

For each table in your pdict definition, the MCP server generates 6 tools:

| Tool | Description |
|------|-------------|
| `describe_{table}` | Return the table schema (columns, types, constraints, FK info) |
| `list_{table}` | List/search records with filtering, sorting, and pagination |
| `get_{table}` | Get a single record by ID |
| `create_{table}` | Create a new record |
| `update_{table}` | Update an existing record |
| `delete_{table}` | Delete a record by ID |

For the todo app, that's 12 tools: `describe_people`, `list_people`, `get_people`, `create_people`, `update_people`, `delete_people`, and the same 6 for `tasks`.

### How pdict drives the tool schemas

Your column metadata controls the generated tool parameter schemas:

- **`is_create_required`** → parameter is marked `required` in the create tool
- **`is_filterable`** → column appears as a filter parameter in the list tool
- **`is_sortable`** → column is listed in the sort parameter description
- **`is_read_only`** → column excluded from create and update tools
- **`rest_label`** → used as the parameter description in tool schemas
- **`foreign_key`** → included in describe output so the agent understands table relationships

### Launch the MCP server

The MCP server runs as a standalone stdio process. It connects directly to the same SQLite database as the REST API:

```bash
python -m qdrestful.mcp_server \
    --db-type sqlite \
    --db-path todo_data.db \
    --pdict-module data_spec \
    --pdict-attr db_dict
```

Arguments:

| Argument | Description |
|----------|-------------|
| `--db-type` | `sqlite` or `mariadb` (default: `sqlite`) |
| `--db-path` | Path to the SQLite database file |
| `--pdict-module` | Python module containing the pdict definition (dotted path) |
| `--pdict-attr` | Attribute name for the `DbDictDb` object (default: `db_dict`) |

The server reads JSON-RPC messages from stdin and writes responses to stdout, following the MCP protocol (version `2024-11-05`).

### Configure Claude Desktop

To connect the todo app's MCP server to Claude Desktop, add it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todo": {
      "command": "python",
      "args": [
        "-m", "qdrestful.mcp_server",
        "--db-path", "/path/to/todo_data.db",
        "--pdict-module", "data_spec",
        "--pdict-attr", "db_dict"
      ],
      "cwd": "/path/to/todo",
      "env": {
        "PYTHONPATH": "/path/to/quickdev/qdbase/src:/path/to/qdflask-repo/qdrestful/src:/path/to/todo"
      }
    }
  }
}
```

Replace `/path/to/` with actual paths to your installations. The `PYTHONPATH` must include `qdbase`, `qdrestful`, and your application directory.

### Configure Claude Code

For Claude Code, add the MCP server to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "todo": {
      "command": "python",
      "args": [
        "-m", "qdrestful.mcp_server",
        "--db-path", "/path/to/todo_data.db",
        "--pdict-module", "data_spec",
        "--pdict-attr", "db_dict"
      ],
      "cwd": "/path/to/todo",
      "env": {
        "PYTHONPATH": "/path/to/quickdev/qdbase/src:/path/to/qdflask-repo/qdrestful/src:/path/to/todo"
      }
    }
  }
}
```

### Example MCP interaction

Once configured, an AI agent can interact with your data:

```
Agent: "Show me all high-priority tasks"
→ calls list_tasks(priority="high")
→ returns paginated task list

Agent: "Create a task to review the API docs, assigned to Alice"
→ calls list_people(name="Alice") to find Alice's ID
→ calls create_tasks(title="Review API docs", assigned_to=1)
→ returns the created task with ID and timestamp

Agent: "Mark task 3 as done"
→ calls update_tasks(id=3, status="done")
→ returns the updated task
```

### MCP and REST share the same database

The MCP server connects to the same SQLite file as the REST API. Records created through the MCP server are immediately visible through the REST API and web forms, and vice versa.

```
Claude Desktop → MCP server → qdsqlite → todo_data.db
Browser        → qdforms JS → qdrestful → qdsqlite → todo_data.db
Script         → REST API   → qdrestful → qdsqlite → todo_data.db
```

All three access paths share the same database and the same pdict constraints (required fields, choices, FK integrity, unique constraints).

### Enabling MCP in the Flask config

If you want to flag MCP as enabled in the Flask app config (useful for admin dashboards or status pages), add `mcp_enabled` to the qdrestful config:

```python
init_qdrestful(app, config={
    'enabled': True,
    'db_type': 'sqlite',
    'sqlite_fpath': 'todo_data.db',
    'url_prefix': '/api',
    'mcp_enabled': True,
})
```

This stores `QDRESTFUL_MCP_ENABLED = True` in the Flask config but does not launch the MCP server — the server runs as a separate process.

## Step 6: Package and Deploy

In Steps 1-5 you built the todo app by hand-writing an `app.py` that calls each `init_*` function in the right order. This works for development, but for deployment you want a reproducible installation that:

- Creates a virtual environment automatically
- Installs all packages in the correct order
- Generates the Flask app factory from package declarations
- Writes a WSGI entry point for Apache/Gunicorn
- Creates all required directories (conf/, conf/db/, etc.)
- Captures every configuration decision in a file for reproduction

QuickDev's `qdboot` system does all of this from a single `bootstrap.toml` file.

### Step 6a: Structure your app as an installable package

First, restructure your project so `qdstart` can discover and install it:

```
todo/
├── setup.py
├── bootstrap.toml
├── app.py                     # (development server, kept for convenience)
└── todo/
    ├── __init__.py            # init function for qdstart
    ├── data_spec.py           # pdict definitions (moved here)
    └── qd_conf.toml           # package configuration
```

**`todo/__init__.py`** — Declares a Flask init function that wires your pdict into the app:

```python
__version__ = '0.1.0'

def init_todo(app):
    from todo.data_spec import db_dict
    app.config['QDRESTFUL_DB_DICT'] = db_dict

    @app.route('/')
    def index():
        return {'status': 'ok', 'tables': list(db_dict.tables.keys())}
```

**`todo/qd_conf.toml`** — Tells qdstart about your init function and pre-supplies answers for the framework packages your app requires:

```toml
[flask.init_function]
module = "todo"
function = "init_todo"
priority = 5

[answers.qdflaskauth]
enabled = true
roles = "admin, member"

[answers.qdflaskapi]
enabled = true

[answers.qdrestful]
enabled = true
db_type = "sqlite"
sqlite_fpath = "<site_dpath>/conf/db/todo_data.db"
url_prefix = "/api"

[answers.qdforms]
enabled = true
url_prefix = "/forms"
```

Key points:
- `priority = 5` ensures `init_todo` runs before any framework packages (qdflask is 10, qdrestful is 30)
- The `[answers.*]` sections pre-supply configuration so the installer doesn't prompt for them
- `<site_dpath>` is a placeholder that resolves to the actual installation directory at install time

**`setup.py`** — Makes the package pip-installable:

```python
from setuptools import setup, find_packages
setup(
    name='todo',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['qdbase'],
    package_data={'todo': ['qd_conf.toml']},
)
```

### Step 6b: Create bootstrap.toml

`bootstrap.toml` is the single source of truth for reproducing the installation. It specifies the site directory, repository locations, and all configuration answers:

```toml
[site]
site_dpath = "/var/www/todo"
qdsite_prefix = "todo"
python = "python3"

[repos]
paths = [
    "e::/path/to/quickdev",
    "e::/path/to/qdflask-repo",
    "e::/path/to/todo",
]

[answers.site]
qdsite_prefix = "todo"

[answers.denv]
FLASK_SECRET_KEY = "change-me-in-production"
MARIADB_USER = ""
MARIADB_PASSWORD = ""

[answers.qdflask]
passwordsdb_fpath = "<site_dpath>/conf/db/passwords.db"

[answers.qdflaskauth]
enabled = true
roles = "admin, member"
login_view = "auth.login"

[answers.qdflaskapi]
enabled = true
all_users_can_generate_api_keys = false
is_api = false

[answers.qdrestful]
enabled = true
db_type = "sqlite"
sqlite_fpath = "<site_dpath>/conf/db/todo_data.db"
url_prefix = "/api"
mcp_enabled = true
mcp_port = "8765"
mariadb_host = ""
mariadb_port = ""
mariadb_database = ""

[answers.qdforms]
enabled = true
url_prefix = "/forms"

[answers.qdcomments]
enabled = false

[answers.qdflaskemail]
enabled = false

[answers.qdimages]
enabled = false
```

The `e::` prefix on repo paths means editable install (`pip install -e`). Remove it for production deployments where you want packages copied into the venv.

### Step 6c: Generate the boot files

Run `qdbootstrap.py` to generate the boot script and flattened answer file:

```bash
python qdbootstrap.py --generate -t /path/to/todo
```

This creates two files in your project directory:

- **`qdboot.sh`** — Shell script with `plan` and `make` commands
- **`qdboot_answers.toml`** — Flattened answers from bootstrap.toml (consumed by qdstart)

### Step 6d: Preview the installation

Run the plan command to see what qdstart will do without actually doing it:

```bash
sh qdboot.sh plan
```

The plan shows:
- All configuration questions and their answer sources (constant, from CLI, will be prompted)
- Which packages will be installed
- Which packages are disabled

If any questions show as "Will be prompted", add their answers to `bootstrap.toml` and regenerate the boot files.

### Step 6e: Install

```bash
sh qdboot.sh make
```

This runs `qdstart.py`, which:

1. Creates the site directory and `conf/` subdirectories
2. Creates a virtual environment (`todo.venv`)
3. Processes all configuration questions (using pre-supplied answers)
4. Installs all enabled packages via pip
5. Generates `qd_create_app.py` — the Flask app factory
6. Generates `wsgi.py` — the WSGI entry point
7. Saves all configuration to `conf/*.toml` files

### What gets generated

After installation, the site directory looks like:

```
/var/www/todo/
├── qd_create_app.py        # Generated Flask app factory
├── wsgi.py                 # Generated WSGI entry point
├── venv -> todo.venv/...   # Symlink to venv activate script
├── todo.venv/              # Virtual environment
└── conf/
    ├── site.toml           # Site identity
    ├── repos.db            # Package/question database
    ├── qdrestful.toml      # qdrestful config (resolved paths)
    ├── qdflask.toml        # qdflask config
    ├── qdflaskauth.toml    # Auth config
    ├── qdflaskapi.toml     # API key config
    ├── qdforms.toml        # Forms config
    ├── denv.toml           # Environment secrets
    └── db/
        ├── passwords.db    # User accounts (created on first run)
        └── todo_data.db    # Application data (created on first run)
```

The generated `qd_create_app.py` calls init functions in priority order:

```python
def qd_init_app(app):
    # Priority 5: todo
    from todo import init_todo
    init_todo(app)

    # Priority 10: qdflask
    from qdflask import init_qdflask
    init_qdflask(app, db_path='/var/www/todo/conf/db/passwords.db')

    # Priority 15: qdflaskauth
    from qdflaskauth import init_qdflaskauth
    init_qdflaskauth(app, enabled=True, roles=['admin', 'member'], login_view='auth.login')

    # Priority 25: qdflaskapi
    # Priority 30: qdrestful (with full config dict)
    # Priority 35: qdforms
```

Notice that `<site_dpath>` has been resolved to the actual installation path.

### Step 6f: Run the generated app

For development:

```bash
cd /var/www/todo
source venv
python qd_create_app.py
```

For production with Gunicorn:

```bash
cd /var/www/todo
source venv
gunicorn 'qd_create_app:create_app()'
```

For Apache with mod_wsgi, point to `wsgi.py`.

### Reproducing the installation

To install on a different machine, copy `bootstrap.toml` and run:

```bash
python qdbootstrap.py --generate -t /path/to/todo
sh qdboot.sh make
```

All answers are captured in `bootstrap.toml`, so the installation is fully non-interactive.

### How it compares to the hand-written app.py

| | Hand-written `app.py` | Generated `qd_create_app.py` |
|--|----------------------|------------------------------|
| Init function calls | Written manually | Generated from `qd_conf.toml` declarations |
| Priority ordering | You track it | Automatic from declared priorities |
| Config values | Hardcoded in Python | Resolved from `bootstrap.toml` answers |
| Database paths | Relative paths | Full resolved paths from `<site_dpath>` |
| Adding a new package | Edit `app.py` | Add a `qd_conf.toml` to the package; re-run `qdstart` |
| Reproducibility | Manual | `bootstrap.toml` captures everything |

The hand-written `app.py` is still useful for development and testing. The generated `qd_create_app.py` is for deployment.
