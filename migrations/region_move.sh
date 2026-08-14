#!/usr/bin/env bash
# Move the database to a Neon project in another region.
#
# The server is in Oracle Cloud Sydney and the database was in AWS us-east-1:
# ~205ms per round trip, which is most of every request. Sydney to Sydney is a
# couple of milliseconds. A Neon project's region can't be changed, so this
# copies into a new project and switches over.
#
# Run it from a machine with pg_dump/pg_restore matching the server version
# (18.x). Nothing here prints a connection string or a password.
#
# Usage:
#   cp migrations/region_move.env.example ~/.config/pg_backup/region_move.env
#   # fill in OLD_URL and NEW_URL (direct endpoints, NOT -pooler), chmod 600
#   ./migrations/region_move.sh dump      # take a dump of the old project
#   ./migrations/region_move.sh roles     # create bgl_* roles in the new project
#   ./migrations/region_move.sh restore   # load the dump into the new project
#   ./migrations/region_move.sh verify    # compare the two, in detail
#
# Then update DATABASE_URL on the server and restart. The old project is left
# untouched, so rolling back is just putting the old URL back.

set -euo pipefail

ENV_FILE="${REGION_MOVE_ENV:-$HOME/.config/pg_backup/region_move.env}"
[ -r "$ENV_FILE" ] || { echo "Missing $ENV_FILE — see region_move.env.example"; exit 1; }
# shellcheck disable=SC1090
. "$ENV_FILE"

: "${OLD_URL:?OLD_URL not set}"
: "${NEW_URL:?NEW_URL not set}"
: "${BGL_APP_PASSWORD:?BGL_APP_PASSWORD not set}"

OUT_DIR="${OUT_DIR:-$HOME/pg_region_move}"
DUMP="$OUT_DIR/boardgames.dump"
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

# A pooled endpoint can't hold the session state pg_dump needs, and Neon's docs
# say to use the direct one. Catch it here rather than halfway through.
for u in "$OLD_URL" "$NEW_URL"; do
    case "$u" in
        *-pooler.*) echo "Use the DIRECT endpoint, not -pooler, for dump/restore."; exit 1;;
    esac
done

case "${1:-}" in

dump)
    echo "Dumping the old project..."
    # Custom format so the restore can be ordered and repeated.
    pg_dump --format=custom --no-privileges=false --verbose \
            --file="$DUMP" "$OLD_URL" 2>&1 | tail -5
    chmod 600 "$DUMP"
    echo "Wrote $DUMP ($(du -h "$DUMP" | cut -f1))"
    ;;

roles)
    # Roles live in the cluster, not the database, so they are NOT in the dump.
    # They have to exist before the restore or every GRANT and every CREATE
    # POLICY naming them fails — and a policy that fails to restore means no
    # row-level security, silently.
    echo "Creating roles in the new project..."
    psql --quiet --no-psqlrc "$NEW_URL" <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgl_app') THEN
        CREATE ROLE bgl_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgl_ai') THEN
        CREATE ROLE bgl_ai NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgl_ai_owner') THEN
        CREATE ROLE bgl_ai_owner NOLOGIN;
    END IF;
END
\$\$;
ALTER ROLE bgl_app WITH PASSWORD '${BGL_APP_PASSWORD}';
-- The app role must NOT bypass RLS; that is the whole isolation model.
ALTER ROLE bgl_app  NOBYPASSRLS;
ALTER ROLE bgl_ai   NOBYPASSRLS;
ALTER ROLE bgl_ai_owner NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO bgl_app, bgl_ai, bgl_ai_owner;
SQL
    echo "Roles ready."
    ;;

restore)
    [ -r "$DUMP" ] || { echo "No dump at $DUMP — run 'dump' first."; exit 1; }
    echo "Restoring into the new project..."
    # Not --no-owner: neondb_owner exists in both projects, and the two
    # SECURITY DEFINER credit functions must stay owned by a BYPASSRLS role or
    # Stripe payments stop crediting. Errors are shown, not swallowed.
    pg_restore --dbname="$NEW_URL" --no-comments --verbose "$DUMP" 2>&1 \
        | grep -viE 'processing|creating|setting|launching|finished' | tail -20 || true
    echo "Restore finished — run 'verify' before switching anything over."
    ;;

verify)
    echo "Comparing old and new..."
    SQL_CHECKS=$(cat <<'SQL'
SELECT 'tables', count(*)::text FROM information_schema.tables
  WHERE table_schema='public' AND table_type='BASE TABLE'
UNION ALL SELECT 'views', count(*)::text FROM information_schema.views WHERE table_schema='public'
UNION ALL SELECT 'rls_enabled', count(*)::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relrowsecurity
UNION ALL SELECT 'rls_forced', count(*)::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relforcerowsecurity
UNION ALL SELECT 'policies', count(*)::text FROM pg_policy
UNION ALL SELECT 'secdef_fns', count(*)::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.prosecdef
UNION ALL SELECT 'imperium_invoker',
  coalesce((SELECT array_to_string(reloptions,',') FROM pg_class WHERE relname='imperium'),'MISSING')
UNION ALL SELECT 'games', count(*)::text FROM games
UNION ALL SELECT 'users', count(*)::text FROM users
UNION ALL SELECT 'rulebooks', count(*)::text FROM rulebooks
UNION ALL SELECT 'sleeping_gods', count(*)::text FROM sleeping_gods
UNION ALL SELECT 'sleeping_gods_totems', count(*)::text FROM sleeping_gods_totems
UNION ALL SELECT 'ai_usage', count(*)::text FROM ai_usage
UNION ALL SELECT 'credit_purchases', count(*)::text FROM credit_purchases
UNION ALL SELECT 'bgl_app_can_login',
  coalesce((SELECT rolcanlogin::text FROM pg_roles WHERE rolname='bgl_app'),'MISSING')
UNION ALL SELECT 'bgl_app_bypassrls',
  coalesce((SELECT rolbypassrls::text FROM pg_roles WHERE rolname='bgl_app'),'MISSING')
UNION ALL SELECT 'games_grants_to_bgl_app',
  coalesce((SELECT string_agg(privilege_type,',' ORDER BY privilege_type)
            FROM information_schema.role_table_grants
            WHERE grantee='bgl_app' AND table_name='games'),'NONE')
ORDER BY 1;
SQL
)
    old=$(psql --quiet --no-psqlrc --tuples-only --no-align --field-separator='|' \
                "$OLD_URL" -c "$SQL_CHECKS")
    new=$(psql --quiet --no-psqlrc --tuples-only --no-align --field-separator='|' \
                "$NEW_URL" -c "$SQL_CHECKS")

    printf '  %-26s %-22s %-22s %s\n' CHECK OLD NEW ''
    fail=0
    while IFS='|' read -r key oldval; do
        newval=$(printf '%s\n' "$new" | awk -F'|' -v k="$key" '$1==k{print $2}')
        mark='ok'
        if [ "$oldval" != "$newval" ]; then mark='<-- DIFFERS'; fail=1; fi
        printf '  %-26s %-22s %-22s %s\n' "$key" "$oldval" "$newval" "$mark"
    done <<< "$old"

    echo
    echo "Row-level security actually applies as bgl_app:"
    PGPASSWORD="$BGL_APP_PASSWORD" psql --quiet --no-psqlrc --tuples-only --no-align \
        "$(printf '%s' "$NEW_URL" | sed -E 's#://[^@]+@#://bgl_app@#')" <<'SQL' || fail=1
SELECT 'as user 1: ' || count(*) FROM (
    SELECT set_config('app.user_id','1',false)) s, games;
SELECT 'as user 999: ' || count(*) FROM (
    SELECT set_config('app.user_id','999',false)) s, games;
SQL

    echo
    if [ "$fail" -eq 0 ]; then
        echo "All checks match. Safe to switch DATABASE_URL on the server."
    else
        echo "SOMETHING DIFFERS — do not switch over until it is explained."
        exit 1
    fi
    ;;

*)
    sed -n '2,26p' "$0"
    exit 1
    ;;
esac
