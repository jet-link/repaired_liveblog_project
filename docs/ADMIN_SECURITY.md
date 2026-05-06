# Admin panel access matrix (`/admin/`)

All routes use **@admin_required** ([admin_panel/decorators.py](/liveblog_project/admin_panel/decorators.py)): authenticated **and** `user.is_staff`. Non-staff users receive **403 Forbidden** (see `errors/403.html`), not a redirect to the homepage.

## Superuser-only actions

These require **@superuser_required** in addition to staff (or explicit `is_superuser` checks in backup views):

| Area | Action |
|------|--------|
| Users | Permanent deletion of deleted-user logs / purge (`deleted_users_permanent_delete`) |
| Backups | List, create, download, restore, delete, JSON status, bulk delete |

Staff without superuser cannot access backup UI or purge deleted users permanently.

## Staff audit logging

In production (`DEBUG=False`), **AdminAuditMiddleware** logs **POST/PUT/PATCH/DELETE** under `/admin/` for authenticated staff to the `security.admin` logger (user id, username, path, HTTP status).

## Destructive operations

Bulk and delete flows are expected to use **POST** with CSRF tokens from the admin templates. Review new endpoints the same way.

## Optional hardening

- **2FA** for staff (TOTP/WebAuthn) — not bundled; evaluate if threat model requires it.
- Tighten **password validators** for staff accounts (longer minimum length) via a custom user model or policy doc.
