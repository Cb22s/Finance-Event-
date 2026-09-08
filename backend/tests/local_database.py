"""PostgreSQL-backed test adapter for the subset of PostgREST used by routes."""
import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def ident(value):
    if not re.fullmatch(r'[a-z_][a-z_0-9]*', value):
        raise ValueError(value)
    return '"' + value + '"'


class LocalDatabase:
    def __init__(self):
        self.process = subprocess.Popen(
            ['node', str(ROOT / 'backend/tests/postgres_bridge.mjs')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, encoding='utf-8')
        self.call("""CREATE ROLE anon; CREATE ROLE authenticated;
            CREATE ROLE service_role BYPASSRLS;
            CREATE SCHEMA auth;
            CREATE TABLE auth.users(id uuid PRIMARY KEY, email text, raw_user_meta_data jsonb);
            CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql AS
            'SELECT nullif(current_setting(''request.jwt.claim.sub'', true), '''')::uuid';""", exec=True)

    def call(self, sql, params=None, exec=False):
        self.process.stdin.write(json.dumps(dict(sql=sql, params=params or [], exec=exec)) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('PostgreSQL test process stopped')
        result = json.loads(line)
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result['result']

    def install(self):
        self.call((ROOT / 'supabase.sql').read_text(encoding='utf-8'), exec=True)

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=20)
        self.process.stdout.close()

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, args):
        def execute():
            placeholders = ','.join(f'{ident(k)} => ${i}' for i, k in enumerate(args, 1))
            params = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in args.values()]
            result = self.call(f'SELECT public.{ident(name)}({placeholders}) AS value', params)
            return SimpleNamespace(data=result['rows'][0]['value'])
        return SimpleNamespace(execute=execute)


class Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.mode, self.columns, self.rows = 'select', '*', None
        self.filters, self.ordering, self.maximum = [], [], None
        self.conflict = None

    def select(self, columns='*'):
        self.columns = columns
        return self

    def insert(self, rows):
        self.mode, self.rows = 'insert', rows
        return self

    def upsert(self, rows, on_conflict='user_id'):
        self.mode, self.rows, self.conflict = 'insert', rows, on_conflict
        return self

    def update(self, rows):
        self.mode, self.rows = 'update', rows
        return self

    def delete(self):
        self.mode = 'delete'
        return self

    def eq(self, key, value):
        self.filters.append((key, '=', value))
        return self

    def neq(self, key, value):
        self.filters.append((key, '!=', value))
        return self

    def order(self, key, desc=False):
        self.ordering.append(ident(key) + (' DESC' if desc else ' ASC'))
        return self

    def limit(self, value):
        self.maximum = int(value)
        return self

    def execute(self):
        params = []

        def bind(value):
            params.append(json.dumps(value) if isinstance(value, (dict, list)) else value)
            return f'${len(params)}'

        table = 'public.' + ident(self.name)
        if self.mode == 'insert':
            rows = self.rows if isinstance(self.rows, list) else [self.rows]
            keys = list(rows[0])
            values = ','.join('(' + ','.join(bind(row[k]) for k in keys) + ')' for row in rows)
            sql = f'INSERT INTO {table} ({",".join(map(ident, keys))}) VALUES {values}'
            if self.conflict:
                sql += ' ON CONFLICT (' + ','.join(map(ident, self.conflict.split(','))) + ') DO UPDATE SET '
                sql += ','.join(f'{ident(k)}=EXCLUDED.{ident(k)}' for k in keys)
        elif self.mode == 'update':
            sql = f'UPDATE {table} SET ' + ','.join(f'{ident(k)}={bind(v)}' for k, v in self.rows.items())
        elif self.mode == 'delete':
            sql = f'DELETE FROM {table}'
        else:
            # PostgREST embeds users(name); reproduce that one route contract.
            cols = self.columns.replace('users(name)', "(SELECT json_build_object('name',name) FROM public.users WHERE id=user_id) AS users")
            sql = f'SELECT {cols} FROM {table}'
        if self.filters:
            sql += ' WHERE ' + ' AND '.join(f'{ident(k)} {op} {bind(v)}' for k, op, v in self.filters)
        if self.ordering:
            sql += ' ORDER BY ' + ','.join(self.ordering)
        if self.maximum is not None:
            sql += f' LIMIT {self.maximum}'
        if self.mode != 'select':
            sql += ' RETURNING *'
        return SimpleNamespace(data=self.db.call(sql, params)['rows'])
