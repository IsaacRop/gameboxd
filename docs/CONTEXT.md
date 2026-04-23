# Gameboxd — Contexto completo do projeto

> Este documento reúne toda a arquitetura, decisões técnicas, schema de banco, backlog e instruções para o Claude Code implementar o projeto do zero.

---

## 1. Visão geral

**Gameboxd** é uma plataforma social para gamers, inspirada no Letterboxd para filmes. Os usuários podem:

- Registrar jogos com status (playing, completed, dropped, want_to_play)
- Escrever reviews com nota de 1 a 5 e texto
- Seguir outros jogadores e ver feed de atividade dos amigos
- Criar listas curadas de jogos
- Descobrir games via integração com a IGDB API

---

## 2. Stack técnica

| Camada | Tecnologia | Motivo |
|---|---|---|
| Framework | Django 5 + Django REST Framework | Maduro, ORM poderoso, admin gratuito |
| Autenticação | djangorestframework-simplejwt | JWT com blacklist, HttpOnly cookie |
| Banco de dados | PostgreSQL 16 | Robusto, suporte a arrays, full-text search |
| API externa | IGDB (api.igdb.com/v4) | Catálogo completo de games via OAuth2 Twitch |
| HTTP client | httpx | Suporte assíncrono nativo, substitui requests |
| Servidor WSGI | Gunicorn | Padrão de mercado para Django em produção |
| Proxy reverso | Nginx | Serve estáticos, rate limiting, SSL termination |
| Containerização | Docker + Docker Compose | Ambientes idênticos dev/prod |
| Arquivos estáticos | Whitenoise | Serve estáticos sem Nginx em dev |
| Imagens | Pillow | Redimensionar avatares |
| Filtros | django-filter | Filtros declarativos na API |
| Documentação | drf-spectacular | Swagger/OpenAPI automático |
| Testes | pytest-django + factory_boy | Fixtures legíveis, cobertura fácil |
| Linting | ruff | Substitui flake8 + black, muito mais rápido |
| Monitoramento | Sentry | Captura de erros em produção |
| Profiling | django-silk | Detectar queries N+1 em dev |

---

## 3. Arquitetura da aplicação

```
Browser
  │
  ▼
Nginx (porta 80/443)
  ├── /static/  →  arquivos estáticos (servidos direto)
  ├── /media/   →  uploads de usuários (servidos direto)
  └── /api/*    →  proxy para Gunicorn (rate limit em /api/auth/)
                       │
                       ▼
                  Gunicorn (WSGI)
                       │
                       ▼
                  Django Application
                  ┌─────────────────────────────────────┐
                  │  URLs → Views → Serializers → Models│
                  │                                     │
                  │  apps/users    (auth, perfil, follow)│
                  │  apps/games    (catálogo, IGDB sync) │
                  │  apps/reviews  (notas, likes)        │
                  │  apps/activity (feed, logs, listas)  │
                  └─────────────────────────────────────┘
                       │                    │
                       ▼                    ▼
                  PostgreSQL           IGDB API
                  (banco local)    (catálogo externo)
```

### Fluxo de autenticação JWT

1. `POST /api/auth/token/` com email + senha → retorna `access` (5min) + `refresh` (7d)
2. Access token armazenado em `HttpOnly cookie` (protegido contra XSS)
3. Requests autenticados: header `Authorization: Bearer <access_token>`
4. Access expirado → `POST /api/auth/token/refresh/` com refresh token → novo access
5. Logout → `POST /api/auth/logout/` → refresh adicionado à blacklist (`OutstandingToken`)

---

## 4. Estrutura de pastas do projeto

```
gameboxd/
├── config/
│   ├── __init__.py
│   ├── urls.py              # roteamento global
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py          # configurações comuns
│       ├── dev.py           # DEBUG=True, silk, django-extensions
│       └── prod.py          # HTTPS, HSTS, Sentry
│
├── apps/
│   ├── users/
│   │   ├── models.py        # User customizado (AbstractBaseUser)
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── permissions.py   # IsOwnerOrReadOnly
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── urls/
│   │   │   ├── auth.py      # /api/auth/*
│   │   │   └── users.py     # /api/users/*
│   │   └── migrations/
│   │
│   ├── games/
│   │   ├── models.py        # Game (espelho do IGDB)
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services.py      # IGDBClient (httpx)
│   │   ├── filters.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── migrations/
│   │
│   ├── reviews/
│   │   ├── models.py        # Review, Like
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── filters.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── migrations/
│   │
│   └── activity/
│       ├── models.py        # Log, List, ListGame, Activity
│       ├── serializers.py
│       ├── views.py
│       ├── signals.py       # auto-cria Activity ao salvar Log/Review/Follow
│       ├── admin.py
│       ├── tests.py
│       ├── urls/
│       │   ├── logs.py      # /api/logs/*
│       │   ├── lists.py     # /api/lists/*
│       │   ├── feed.py      # /api/feed/*
│       │   └── health.py    # /api/health/*
│       └── migrations/
│
├── static/
├── media/
├── templates/
├── nginx/
│   └── nginx.conf
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── docs/
│   ├── CONTEXT.md           # este arquivo
│   └── BACKLOG.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── pytest.ini
```

---

## 5. Schema do banco de dados (ERD)

### Tabela: `users_user`
```
id            UUID PK
username      VARCHAR(150) UNIQUE
email         VARCHAR(254) UNIQUE
password_hash VARCHAR
avatar        VARCHAR (path)
bio           TEXT
created_at    TIMESTAMP
```

### Tabela: `games_game`
```
id           UUID PK
igdb_id      INTEGER UNIQUE
title        VARCHAR(255)
slug         VARCHAR(255) UNIQUE
cover_url    VARCHAR
genres       VARCHAR[] (array)
release_year INTEGER
synced_at    TIMESTAMP
```

### Tabela: `reviews_review`
```
id               UUID PK
user_id          FK → users_user
game_id          FK → games_game
rating           DECIMAL(2,1)  -- 1.0 a 5.0, passo 0.5
body             TEXT
contains_spoiler BOOLEAN
created_at       TIMESTAMP
updated_at       TIMESTAMP
UNIQUE(user_id, game_id)
```

### Tabela: `reviews_like`
```
id          UUID PK
user_id     FK → users_user
review_id   FK → reviews_review
created_at  TIMESTAMP
UNIQUE(user_id, review_id)
```

### Tabela: `activity_log`
```
id          UUID PK
user_id     FK → users_user
game_id     FK → games_game
status      VARCHAR  -- playing | completed | dropped | want_to_play
played_date DATE (nullable)
created_at  TIMESTAMP
UNIQUE(user_id, game_id)
```

### Tabela: `activity_list`
```
id          UUID PK
user_id     FK → users_user
title       VARCHAR(255)
description TEXT
is_public   BOOLEAN
created_at  TIMESTAMP
```

### Tabela: `activity_listgame`
```
id       UUID PK
list_id  FK → activity_list
game_id  FK → games_game
position INTEGER
UNIQUE(list_id, game_id)
```

### Tabela: `users_follow`
```
id           UUID PK
follower_id  FK → users_user
following_id FK → users_user
created_at   TIMESTAMP
UNIQUE(follower_id, following_id)
CHECK(follower_id != following_id)
```

### Tabela: `activity_activity`
```
id          UUID PK
user_id     FK → users_user
verb        VARCHAR  -- reviewed | logged | liked | followed | listed
object_type VARCHAR  -- game | review | user | list
object_id   UUID
created_at  TIMESTAMP
```

---

## 6. Endpoints completos da API

### Autenticação
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/api/auth/register/` | Não | Cadastro |
| POST | `/api/auth/token/` | Não | Login → access + refresh |
| POST | `/api/auth/token/refresh/` | Não | Renovar access token |
| POST | `/api/auth/logout/` | Sim | Blacklist do refresh token |

### Usuários
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/api/users/{username}/` | Não | Perfil público |
| GET | `/api/users/me/` | Sim | Meu perfil |
| PATCH | `/api/users/me/` | Sim | Editar meu perfil |
| GET | `/api/users/me/export/` | Sim | Exportar dados (LGPD) |
| GET | `/api/users/{username}/stats/` | Não | Estatísticas do perfil |
| GET | `/api/users/{username}/logs/` | Não | Logs públicos |
| POST | `/api/users/{username}/follow/` | Sim | Seguir |
| DELETE | `/api/users/{username}/follow/` | Sim | Deixar de seguir |
| GET | `/api/users/{username}/followers/` | Não | Seguidores |
| GET | `/api/users/{username}/following/` | Não | Seguindo |

### Games
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/api/games/` | Não | Listar com filtros |
| GET | `/api/games/{slug}/` | Não | Detalhe do game |
| GET | `/api/games/search/?q=` | Não | Buscar na IGDB |
| GET | `/api/games/recommended/` | Sim | Recomendações personalizadas |
| GET | `/api/games/{slug}/reviews/` | Não | Reviews do game |

### Reviews
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/api/reviews/` | Sim | Criar review |
| GET | `/api/reviews/` | Não | Listar reviews |
| PATCH | `/api/reviews/{id}/` | Sim (dono) | Editar |
| DELETE | `/api/reviews/{id}/` | Sim (dono) | Deletar |
| POST | `/api/reviews/{id}/like/` | Sim | Curtir |
| DELETE | `/api/reviews/{id}/like/` | Sim | Descurtir |

### Logs
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/api/logs/` | Sim | Registrar jogo |
| GET | `/api/logs/` | Sim | Meus logs |
| PATCH | `/api/logs/{id}/` | Sim (dono) | Atualizar status |
| DELETE | `/api/logs/{id}/` | Sim (dono) | Remover |

### Listas
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/api/lists/` | Sim | Criar lista |
| GET | `/api/lists/` | Não | Listar públicas |
| PATCH | `/api/lists/{id}/` | Sim (dono) | Editar |
| DELETE | `/api/lists/{id}/` | Sim (dono) | Deletar |
| POST | `/api/lists/{id}/games/` | Sim (dono) | Adicionar game |
| DELETE | `/api/lists/{id}/games/{game_id}/` | Sim (dono) | Remover game |

### Feed e utilitários
| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/api/feed/` | Sim | Feed dos seguidos |
| GET | `/api/users/{username}/activity/` | Não | Atividade pública |
| GET | `/api/health/` | Não | Health check da app |
| GET | `/api/health/db/` | Não | Health check do banco |
| GET | `/api/schema/` | Não | OpenAPI YAML |
| GET | `/api/docs/` | Não | Swagger UI |

---

## 7. Segurança — camadas de defesa

### Camada 1 — Rede (Nginx)
- HTTPS / TLS 1.3 obrigatório em produção
- HSTS com `max-age=31536000; includeSubDomains; preload`
- Rate limiting: `limit_req_zone` → 5 req/min por IP em `/api/auth/`
- CORS: `CORS_ALLOWED_ORIGINS` explícito, nunca `CORS_ALLOW_ALL_ORIGINS = True`

### Camada 2 — Autenticação (JWT)
- `access token`: TTL 5 minutos
- `refresh token`: TTL 7 dias, armazenado em `HttpOnly cookie`
- `token_blacklist` ativado — logout invalida o refresh no banco
- `ROTATE_REFRESH_TOKENS = True` — a cada refresh, novo par de tokens

### Camada 3 — Autorização (DRF Permissions)
- `IsAuthenticated` em todas as views de escrita
- `IsOwnerOrReadOnly` customizado: leitura livre, escrita/delete só para dono
- Object-level permissions via `get_object()` com `check_object_permissions()`

### Camada 4 — Validação de entrada
- Nunca usar `request.data` direto nos models — sempre via serializer
- DRF serializers rejeitam campos extras automaticamente
- Validação de tipo de arquivo e tamanho máximo em uploads (Pillow)
- ORM do Django protege contra SQL injection por padrão

### Camada 5 — Proteções nativas Django (settings/prod.py)
```python
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
```

### Camada 6 — Banco de dados
- Usuário PostgreSQL dedicado com permissão apenas nas tabelas da app (sem SUPERUSER)
- Credenciais somente em variáveis de ambiente (`.env`), nunca no código
- Backup criptografado agendado

---

## 8. Backlog completo

### Funcionalidades principais (implementar primeiro)

#### [P-01] Setup inicial do projeto Django
**Prioridade:** Alta

**User story:** Como dev, preciso de um projeto Django configurado com DRF, JWT, PostgreSQL e estrutura de apps antes de qualquer desenvolvimento.

**Tarefas para o Claude Code:**
- Criar projeto com `django-admin startproject config .`
- Criar apps: users, games, reviews, activity
- Configurar `settings/base.py`, `settings/dev.py`, `settings/prod.py`
- Configurar `django-environ` para variáveis de ambiente (`.env`)
- Instalar e configurar djangorestframework + simplejwt + cors-headers
- Configurar psycopg3 + banco PostgreSQL local
- Criar `Dockerfile` + `docker-compose.yml` (web, db, nginx)
- Configurar `pytest-django` + `ruff` + `pre-commit`

---

#### [P-02] Autenticação de usuários (registro e login)
**Prioridade:** Alta  
**Endpoints:** `POST /api/auth/register/`, `POST /api/auth/token/`, `POST /api/auth/token/refresh/`, `POST /api/auth/logout/`

**User story:** Como visitante, quero me cadastrar e fazer login para acessar a plataforma.

**Tarefas para o Claude Code:**
- Model `User` customizado (`AbstractBaseUser`) com username, email, avatar, bio
- `RegisterSerializer` com validação de senha forte
- View de registro — `POST /api/auth/register/`
- Configurar simplejwt: access 5min, refresh 7d, HttpOnly cookie
- Ativar `token_blacklist` para logout real
- Endpoint `POST /api/auth/logout/` que adiciona token à blacklist
- Testes: registro duplicado, senha fraca, login inválido

**Dependências:** `djangorestframework-simplejwt`, `rest_framework_simplejwt.token_blacklist`

---

#### [P-03] Perfil do usuário
**Prioridade:** Alta  
**Endpoints:** `GET /api/users/{username}/`, `GET /api/users/me/`, `PATCH /api/users/me/`

**User story:** Como usuário, quero ver e editar meu perfil com avatar, bio e estatísticas de jogos.

**Tarefas para o Claude Code:**
- `UserProfileSerializer` (campos públicos)
- `UserUpdateSerializer` (apenas dono)
- View `GET /api/users/{username}/` — perfil público
- View `GET+PATCH /api/users/me/` — perfil autenticado
- Upload de avatar com Pillow (redimensionar para 200x200)
- Campos calculados: total de jogos, reviews, seguidores
- Permission `IsOwnerOrReadOnly` customizada
- Testes: acesso público, edição por não-dono bloqueada

**Dependências:** `Pillow`, `django-storages` (opcional para S3)

---

#### [P-04] Catálogo de games (integração IGDB)
**Prioridade:** Alta  
**Endpoints:** `GET /api/games/`, `GET /api/games/{slug}/`, `GET /api/games/search/?q=`

**User story:** Como usuário, quero buscar qualquer game pelo nome e ver sua página com capa, gênero e ano.

**Tarefas para o Claude Code:**
- Criar serviço `IGDBClient` com `httpx` (autenticação OAuth2 Twitch)
- Management command `sync_game {igdb_id}` para importar game
- Model `Game`: igdb_id, title, slug, cover_url, genres[], release_year, synced_at
- View `GET /api/games/search/?q=` — busca na IGDB e persiste resultado
- View `GET /api/games/{slug}/` — detalhe do game local
- View `GET /api/games/` — listagem com filtros (gênero, ano)
- Cache de 24h nos resultados da IGDB com `django-cache`
- Testes: busca sem resultado, game já persistido, falha da API

**Dependências:** `IGDB API (api.igdb.com/v4)`, `httpx`, `Twitch OAuth2`

---

#### [P-05] Registro de jogo (Log)
**Prioridade:** Alta  
**Endpoints:** `POST /api/logs/`, `GET /api/logs/`, `PATCH /api/logs/{id}/`, `DELETE /api/logs/{id}/`

**User story:** Como usuário, quero registrar os jogos que joguei, estou jogando ou quero jogar.

**Tarefas para o Claude Code:**
- Model `Log`: user, game, status (playing/completed/dropped/want_to_play), played_date
- `LogSerializer` com validação de status
- `LogViewSet` com filter por status e game
- Impedir log duplicado (`unique_together`: user + game)
- Ao criar/atualizar log, disparar sinal para criar `Activity`
- Endpoint `GET /api/users/{username}/logs/` — logs públicos
- Testes: log duplicado, troca de status, delete

**Dependências:** `django-filter`

---

#### [P-06] Reviews (notas e resenhas)
**Prioridade:** Alta  
**Endpoints:** `POST /api/reviews/`, `GET /api/reviews/`, `PATCH /api/reviews/{id}/`, `DELETE /api/reviews/{id}/`, `GET /api/games/{slug}/reviews/`

**User story:** Como usuário, quero escrever uma review com nota (1-5) e texto, e ver reviews de outros sobre o mesmo game.

**Tarefas para o Claude Code:**
- Model `Review`: user, game, rating (DecimalField 1-5, passo 0.5), body, contains_spoiler
- `ReviewSerializer` com validação de rating
- Uma review por usuário por game (`unique_together`)
- `ReviewViewSet` com ordering por data e nota
- View `GET /api/games/{slug}/reviews/`
- Anotação de média de rating por game (`Avg`)
- Testes: review duplicada, rating inválido, edição por não-dono

**Dependências:** `Django ORM Aggregation (Avg, Count)`

---

### Funcionalidades secundárias (fase 2)

#### [S-01] Sistema de follows
**Prioridade:** Média  
**Endpoints:** `POST /api/users/{username}/follow/`, `DELETE /api/users/{username}/follow/`, `GET /api/users/{username}/followers/`, `GET /api/users/{username}/following/`

**Tarefas para o Claude Code:**
- Model `Follow`: follower (FK User), following (FK User), `unique_together`
- Impedir auto-follow (`follower != following`)
- Views de follow/unfollow, followers e following
- `UserMiniSerializer` para listas compactas
- Testes: auto-follow, follow duplicado, unfollow sem follow

---

#### [S-02] Likes em reviews
**Prioridade:** Média  
**Endpoints:** `POST /api/reviews/{id}/like/`, `DELETE /api/reviews/{id}/like/`

**Tarefas para o Claude Code:**
- Model `Like`: user, review, `unique_together`
- Views de like/unlike
- Contador de likes anotado no `ReviewSerializer`
- Campo `is_liked_by_me` no serializer (quando autenticado)
- Testes: like duplicado, unlike sem like

---

#### [S-03] Listas customizadas de jogos
**Prioridade:** Média  
**Endpoints:** `POST /api/lists/`, `PATCH /api/lists/{id}/`, `POST /api/lists/{id}/games/`, `DELETE /api/lists/{id}/games/{game_id}/`

**Tarefas para o Claude Code:**
- Models `List` e `ListGame` (com campo `position` para ordenação)
- CRUD de listas com `ListViewSet`
- Adicionar/remover games da lista
- Reordenação via PATCH com array de positions
- Listas públicas visíveis sem autenticação
- Testes: lista privada, reordenação, game duplicado

---

#### [S-04] Feed de atividade
**Prioridade:** Média  
**Endpoints:** `GET /api/feed/`, `GET /api/users/{username}/activity/`

**Tarefas para o Claude Code:**
- Model `Activity`: user, verb, object_type, object_id, created_at
- Signal handlers: criar Activity ao salvar Log, Review, Like, Follow
- View `GET /api/feed/` — atividade dos seguidos (paginada por cursor)
- Serializer polimórfico para diferentes tipos de Activity
- Paginação por cursor (mais eficiente que offset para feeds)
- Testes: feed vazio, múltiplos tipos de evento

**Dependências:** `Django Signals`, `cursor pagination (DRF)`

---

#### [S-05] Paginação, filtros e busca global
**Prioridade:** Média

**Tarefas para o Claude Code:**
- `FilterSet` para games: genre, release_year, ordering
- `FilterSet` para reviews: rating, game, ordering (data, likes)
- Busca de usuários por username com `icontains`
- `PageNumberPagination` padrão (20 itens) + `CursorPagination` para feed
- Testes: filtros combinados, ordenação, busca sem resultado

**Dependências:** `django-filter`, `DRF pagination`

---

### Diferenciais (fase 3)

#### [D-01] Documentação automática (Swagger/OpenAPI)
**Endpoints:** `GET /api/schema/`, `GET /api/docs/`

**Tarefas:**
- Configurar `drf-spectacular`
- Anotar ViewSets com `@extend_schema`
- Documentar schemas de erro (400, 401, 403, 404)
- Gerar `openapi.yaml` para versionamento

---

#### [D-02] Rate limiting por usuário e IP
**Tarefas:**
- `AnonRateThrottle` (100/day), `UserRateThrottle` (1000/day)
- `LoginRateThrottle` customizado (5/min por IP) em `/auth/token/`
- Nginx `limit_req_zone` para `/api/auth/`
- Header `Retry-After` no 429

---

#### [D-03] Recomendações de games
**Endpoint:** `GET /api/games/recommended/`

**Tarefas:**
- Agregar gêneros mais frequentes nos Logs do usuário
- Query: games com esses gêneros que o usuário ainda não logou
- Fallback para games populares se sem logs
- Cache de 1h por usuário

---

#### [D-04] Estatísticas do perfil
**Endpoint:** `GET /api/users/{username}/stats/`

**Tarefas:**
- Total logs, reviews, média rating, top 3 gêneros
- Distribuição por ano de lançamento
- Histograma de ratings (1–5)
- Cache invalidado ao criar Log ou Review

---

#### [D-05] Exportação de dados (LGPD)
**Endpoint:** `GET /api/users/me/export/`

**Tarefas:**
- JSON completo: perfil, logs, reviews, listas, follows
- Throttle: 1 exportação por hora
- `Content-Disposition: attachment`

---

#### [D-06] Health check e monitoramento
**Endpoints:** `GET /api/health/`, `GET /api/health/db/`

**Tarefas:**
- Health check de app e banco
- Integrar Sentry em produção
- django-silk em dev para profiling de queries N+1
- Logging estruturado em JSON para produção

---

## 9. Ferramentas e dependências

### requirements/base.txt
```
Django>=5.0,<6.0
djangorestframework>=3.15,<4.0
django-cors-headers>=4.3,<5.0
django-environ>=0.11,<1.0
django-filter>=23.5,<25.0
djangorestframework-simplejwt>=5.3,<6.0
psycopg[binary]>=3.1,<4.0
httpx>=0.27,<1.0
Pillow>=10.3,<11.0
drf-spectacular>=0.27,<1.0
whitenoise>=6.6,<7.0
```

### requirements/dev.txt
```
-r base.txt
pytest>=8.1,<9.0
pytest-django>=4.8,<5.0
pytest-cov>=5.0,<6.0
factory-boy>=3.3,<4.0
faker>=25.0,<26.0
ruff>=0.4,<1.0
pre-commit>=3.7,<4.0
django-silk>=5.1,<6.0
django-extensions>=3.2,<4.0
ipython>=8.24,<9.0
```

### requirements/prod.txt
```
-r base.txt
gunicorn>=22.0,<23.0
sentry-sdk[django]>=2.3,<3.0
python-json-logger>=2.0,<3.0
```

---

## 10. Variáveis de ambiente (.env)

```env
# Django
SECRET_KEY=gere-com-get_random_secret_key()
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Banco
DATABASE_URL=postgres://gameboxd:gameboxd@db:5432/gameboxd

# IGDB (https://dev.twitch.tv/console)
IGDB_CLIENT_ID=seu-client-id
IGDB_CLIENT_SECRET=seu-client-secret

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=5
REFRESH_TOKEN_LIFETIME_DAYS=7

# Sentry (produção)
# SENTRY_DSN=https://...@sentry.io/...
```

---

## 11. Comandos úteis

```bash
# Subir ambiente de desenvolvimento
docker compose up --build

# Rodar migrations
docker compose exec web python manage.py migrate

# Criar superusuário
docker compose exec web python manage.py createsuperuser

# Rodar testes
docker compose exec web pytest

# Testes com cobertura
docker compose exec web pytest --cov=apps --cov-report=html

# Linting
ruff check .
ruff format .

# Shell do Django
docker compose exec web python manage.py shell_plus

# Ver queries SQL geradas
docker compose exec web python manage.py shell_plus --print-sql

# Importar game da IGDB
docker compose exec web python manage.py sync_game 1234
```

---

## 12. Ordem de implementação recomendada para o Claude Code

Dentro de cada fase, sempre seguir: `models.py → serializers.py → views.py → urls.py → tests.py`

### Fase 1 — MVP
1. [P-01] Setup do projeto (Dockerfile, settings, apps)
2. [P-02] Autenticação (User model, JWT, register, login, logout)
3. [P-03] Perfil (view pública, edição, avatar)
4. [P-04] Catálogo de games + integração IGDB
5. [P-05] Registro de jogo (Log)
6. [P-06] Reviews e notas

### Fase 2 — Social
7. [S-01] Follows
8. [S-02] Likes
9. [S-03] Listas
10. [S-04] Feed de atividade
11. [S-05] Filtros e busca

### Fase 3 — Diferenciais
12. [D-01] Swagger/OpenAPI
13. [D-02] Rate limiting robusto
14. [D-03] Recomendações
15. [D-04] Estatísticas
16. [D-05] Exportação LGPD
17. [D-06] Health check e monitoramento

---

## 13. Prompt inicial para o Claude Code

Ao abrir o projeto no Claude Code (`cd gameboxd && claude`), use este prompt:

```
Você está implementando o projeto Gameboxd — um Letterboxd para video games.

Leia o arquivo docs/CONTEXT.md para entender toda a arquitetura, schema de banco, 
endpoints e backlog antes de começar qualquer implementação.

Comece pela issue [P-01] — Setup inicial do projeto Django.

Regras:
1. Sempre escreva testes para cada feature antes de avançar para a próxima
2. Siga a ordem: models.py → serializers.py → views.py → urls.py → tests.py
3. Use ruff para lint após cada arquivo criado
4. Nunca use request.data diretamente nos models — sempre passe pelo serializer
5. Confirme comigo após concluir cada issue antes de iniciar a próxima
```
