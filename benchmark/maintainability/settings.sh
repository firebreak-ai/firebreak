# Sourced by the kit's shell scripts: where the kit, its data folder and the outside checkouts are.
# Sets K (the kit), LOCAL (K/local: data and runs, ignored by git) and REPO (the Firebreak repository the kit sits in).
# Each setting is taken from the environment, else from local/settings.env (NAME=value lines; see settings.example.env).
K="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOCAL="$K/local"; REPO="$(cd "$K/../.." && pwd)"
if [ -f "$LOCAL/settings.env" ]; then
  while IFS='=' read -r k v; do case $k in ''|\#*) ;; *) [ -n "${!k:-}" ] || export "$k=$v";; esac; done < "$LOCAL/settings.env"
fi
need() { local v; for v in "$@"; do [ -n "${!v:-}" ] || { echo "$v is not set: put it in $LOCAL/settings.env (see settings.example.env)" >&2; exit 2; }; done; }
