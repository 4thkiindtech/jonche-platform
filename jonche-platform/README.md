# JONCHE Platform — Monorepo

> Unified luxury sneaker brand command center.

```
jonche-platform/
├── apps/
│   ├── web/          # Flask frontend (HTML dashboard)
│   └── api/          # Flask REST API (drops, members, certs)
├── packages/
│   ├── ui/           # Shared HTML/CSS components
│   ├── config/       # Shared config (env, constants)
│   └── types/        # Shared Python type definitions
├── .github/
│   └── workflows/    # CI/CD pipelines
├── Makefile          # Dev shortcuts
└── pyproject.toml    # Root project config
```

## Quickstart

```bash
# Install all dependencies
make install

# Run everything locally
make dev

# Run tests
make test

# Deploy to PythonAnywhere
make deploy
```

## Apps

| App | Port | Description |
|-----|------|-------------|
| `web` | 5000 | Dashboard frontend |
| `api` | 5001 | REST API backend |

## Phases

- [x] Phase 1 — Drops + checkout lock + raffle
- [x] Phase 1.5 — Preorder intent capture
- [ ] Phase 2 — Retailer portal (full retailer-facing UI/workflows)
- [x] Phase 3 — VIP membership (accounts + tiers)
- [ ] Phase 4 — Custom builder
- [x] Phase 5 — Analytics + certificates
