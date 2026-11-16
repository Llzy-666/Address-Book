# Code Standards

Conventions this project follows. Both members agreed to these before writing any code,
so that the two branches could be merged without reformatting each other's work.

## 1. Language and naming

| Item | Rule |
| --- | --- |
| Back end language | Python 3.10+ |
| Front end language | ES6 JavaScript, no transpiler |
| Python naming | `snake_case` for functions and variables, `PascalCase` only for classes, `UPPER_CASE` for module-level constants |
| JS naming | `camelCase` for variables and functions, `UPPER_CASE` for module constants |
| CSS naming | BEM-style: `.block`, `.block__element`, `.block--modifier` |
| JSON fields | `camelCase` in every request and response body |

No abbreviations outside the ones already common in the domain (`api`, `db`, `id`, `url`).

## 2. Python (back end)

### 2.1 Layout

- `app.py` only assembles the application: registers blueprints, enables CORS, serves
  static files, installs error handlers. **No business logic lives here.**
- `api/` holds blueprints. One blueprint per concern: `contacts` and `excel_io`.
- `utils/` holds pure functions with no Flask imports, so they can be unit tested
  without an application context.
- `db.py` owns the connection factory and schema. It is the only module that opens a
  SQLite connection directly for writing; blueprints call `db.get_connection()`.

### 2.2 Functions and docstrings

- One public function per endpoint, short and single purpose.
- Every endpoint function has a Chinese docstring stating what it does and what it
  returns.
- Private helpers start with an underscore (`_serialize`, `_validate_payload`).

### 2.3 Constants instead of magic values

Length limits, error codes, type enums, and the Excel header are module-level constants:

```python
NAME_MAX_LENGTH = 50
VALUE_MAX_LENGTH = 200
METHOD_TYPES = ("phone", "email", "wechat", "address", "other")
CODE_HEADER_MISMATCH = 1001
```

Nothing in the codebase compares against a bare `50` or `"phone"`.

### 2.4 Database rules

- **No ORM.** Plain `sqlite3` with `sqlite3.Row` as the row factory.
- Every statement is parameterized. String concatenation into SQL is forbidden, including
  for `LIKE` patterns (the pattern is bound, not interpolated).
- `PRAGMA foreign_keys = ON` is executed on every connection, because SQLite scopes that
  setting per connection, not per database.
- Multi-row writes run inside one transaction; on failure the code rolls back explicitly
  and returns `1002`.

### 2.5 Error handling

- Business failures return HTTP 200 with `{"code": <non-zero>, "message": "..."}`.
- Unexpected exceptions are caught at the endpoint, rolled back, and converted to the same
  envelope — never an HTML traceback.
- Application-level handlers cover 404, 405, 413, and 500.

### 2.6 Style

- PEP 8: four-space indentation, two blank lines between top-level definitions, lines
  kept under ~100 characters.
- Imports grouped as: standard library, third party, then project modules.
- No wildcard imports.

## 3. JavaScript (front end)

- Three layers, in this order in `app.js`:
  1. `request()` — the only place that touches `fetch` and the response envelope;
  2. the render layer — pure functions that turn data into DOM;
  3. the event layer — event listeners that read state, call the API, then re-render.
- No global variables except the `state` object and the `el` DOM cache, both scoped inside
  an IIFE.
- DOM is built with `textContent` or escaped interpolation; user-supplied strings are never
  concatenated into HTML unescaped.
- Every request goes through `request()`, so loading states, error toasts, and envelope
  unwrapping are implemented once.
- No `console.log` left in committed code.

## 4. CSS

- All colours, radii, spacing, and transitions come from custom properties declared in
  `:root`. No hard-coded hex values outside that block.
- One accent colour for the whole product.
- Class names follow BEM; no inline `style` attributes in HTML.
- Breakpoints are declared once, at the bottom of the file: `1024px` and `767px`.

## 5. HTML

- Semantic elements (`header`, `main`, `section`, `article`, `aside`, `footer`).
- Every form control has a `<label>` or an `aria-label`.
- Dialogs use `role="dialog"` with `aria-modal="true"` and `aria-labelledby`.
- Icons are inline SVG with `aria-hidden="true"`; no external CDN, so the page works
  offline.

## 6. Git conventions

### 6.1 Branches

| Branch | Purpose |
| --- | --- |
| `main` | Always runnable. Only receives merges. |
| `feature/backend` | Back-end work (Zhang Xinyang) |
| `feature/frontend` | Front-end work (Liu Ruizhi) |

### 6.2 Commits

Conventional Commits with a Chinese subject line:

```
feat: 联系人 CRUD、多联系方式与收藏接口
fix: 修复 hidden 属性被 display 覆盖导致弹窗常驻
docs: 接口文档、Excel 格式说明与冒烟测试
chore: 初始化仓库与项目骨架
```

- One commit per coherent unit of work; a commit must leave the project runnable.
- Subject line under 50 characters, imperative mood, no trailing period.
- Body (optional) explains *why*, not *what* — the diff already shows the what.

### 6.3 Pull requests

- Each feature branch merges into `main` with `--no-ff`, so the branch point stays visible
  in the history.
- Before merging: run `python tests/smoke_test.py` against a running server. A merge that
  breaks an endpoint is not merged.
- No force push to `main`.

## 7. File ownership

To avoid conflicts the two members kept disjoint file sets:

| Owner | Files |
| --- | --- |
| Back end | `app.py`, `db.py`, `seed.py`, `api/`, `utils/`, `tests/` |
| Front end | `static/` |
| Shared (changes announced first) | `README.md`, `docs/`, `requirements.txt`, `.gitignore` |

Neither member edited the other's files. This is why both branches merged without a single
conflict.

## 8. Testing

- `tests/smoke_test.py` must pass before any merge to `main`.
- Every new endpoint gets at least one assertion in the smoke test.
- The Excel round-trip test (export → wipe → import → compare) is a required regression
  check; if it fails, the import/export work is not done.

## 9. Documentation

- Every endpoint change updates the matching section of `README.md`.
- Any change to the Excel header or the response envelope requires agreement from both
  members first, because it breaks the other side.
