#!/usr/bin/env python3
"""
Migration script to encrypt plaintext API keys in providers table.

Usage:
    python scripts/encrypt_api_keys.py [--dry-run] [--key ENV_KEY_NAME]

Environment variables:
    API_KEY_ENCRYPTION_KEY: Fernet encryption key (base64 encoded)
    DATABASE_URL: PostgreSQL connection URL
"""

import argparse
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.fernet import Fernet


def get_fernet_from_env(env_key: str = "API_KEY_ENCRYPTION_KEY") -> Fernet | None:
    key = os.getenv(env_key)
    if not key:
        print(f"Error: {env_key} not set in environment")
        return None
    try:
        key_bytes = base64.urlsafe_b64decode(key.encode("utf-8"))
        return Fernet(key_bytes)
    except Exception as e:
        print(f"Error: invalid encryption key: {e}")
        return None


def encrypt_value(value: str, fernet: Fernet) -> str:
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def is_encrypted(value: str) -> bool:
    if not value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
        return len(decoded) >= 32
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Encrypt plaintext API keys")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying"
    )
    parser.add_argument(
        "--key",
        default="API_KEY_ENCRYPTION_KEY",
        help="Env var name for encryption key",
    )
    args = parser.parse_args()

    fernet = get_fernet_from_env(args.key)
    if not fernet:
        sys.exit(1)

    import psycopg
    from psycopg.rows import dict_row

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pg_host = os.getenv("PG_HOST", "localhost")
        pg_port = os.getenv("PG_PORT", "5432")
        pg_user = os.getenv("PG_USER", "postgres")
        pg_password = os.getenv("PG_PASSWORD", "")
        pg_database = os.getenv("PG_DATABASE", "model_gateway")
        db_url = (
            f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        )

    try:
        conn = psycopg.connect(db_url, row_factory=dict_row)
    except Exception as e:
        print(f"Error: cannot connect to database: {e}")
        sys.exit(1)

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, api_key FROM providers WHERE api_key IS NOT NULL AND api_key != ''"
            )
            rows = cur.fetchall()

    if not rows:
        print("No providers with API keys found")
        return

    changes = []
    for row in rows:
        api_key = row["api_key"]
        if is_encrypted(api_key):
            print(
                f"Provider {row['name']} (id={row['id']}): already encrypted, skipping"
            )
            continue
        encrypted = encrypt_value(api_key, fernet)
        changes.append((row["id"], row["name"], api_key, encrypted))

    if not changes:
        print("All API keys are already encrypted")
        return

    print(f"\nFound {len(changes)} providers with plaintext API keys:")
    for id_, name, plaintext, encrypted in changes:
        masked = (
            plaintext[:8] + "..." + plaintext[-4:]
            if len(plaintext) > 12
            else plaintext[:4] + "..."
        )
        print(f"  - {name} (id={id_}): {masked}")

    if args.dry_run:
        print("\n[DRY RUN] No changes applied")
        return

    print("\nEncrypting API keys...")
    with conn:
        with conn.cursor() as cur:
            for id_, name, plaintext, encrypted in changes:
                cur.execute(
                    "UPDATE providers SET api_key = %s WHERE id = %s", (encrypted, id_)
                )
                print(f"  - {name} (id={id_}): encrypted")

    print(f"\nDone! {len(changes)} API keys encrypted")


if __name__ == "__main__":
    main()
