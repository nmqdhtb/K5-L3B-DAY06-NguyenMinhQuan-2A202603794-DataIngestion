"""Persistent PostgreSQL/pgvector store, exact cosine search, atomic snapshot upsert."""
import math
from typing import Any
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int, model_signature: dict,
                 schema: str = 'day6_pipeline') -> None:
        if not isinstance(dimensions, int) or not 1 <= dimensions <= 16000:
            raise ValueError('Invalid vector dimensions')
        if not model_signature:
            raise ValueError('Model signature is required to prevent mixed embedding spaces')
        self.database_url, self.dimensions = database_url, dimensions
        self.model_signature = model_signature
        self.schema = schema
        self.table = sql.Identifier(schema, 'chunks')
        self.config = sql.Identifier(schema, 'embedding_config')

    def connect(self):
        return psycopg.connect(self.database_url, connect_timeout=5)

    def create_schema(self) -> None:
        with self.connect() as conn:
            conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            conn.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(self.schema)))
            conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS {} (id integer PRIMARY KEY CHECK(id=1), signature jsonb NOT NULL)').format(self.config))
            signature = {**self.model_signature, 'dimensions': self.dimensions}
            conn.execute(sql.SQL('INSERT INTO {} VALUES (1,%s) ON CONFLICT DO NOTHING').format(self.config), (Jsonb(signature),))
            saved = conn.execute(sql.SQL('SELECT signature FROM {} WHERE id=1 FOR UPDATE').format(self.config)).fetchone()[0]
            if saved != signature:
                raise ValueError('Database model signature differs; use a new schema for a new model')
            conn.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS {} (
                strategy text NOT NULL, chunk_id text NOT NULL, document_id text NOT NULL,
                source text NOT NULL, page integer NOT NULL, text text NOT NULL,
                metadata jsonb NOT NULL, embedding vector({}) NOT NULL,
                PRIMARY KEY(strategy, chunk_id))''').format(self.table, sql.Literal(self.dimensions)))

    def _vector(self, vector):
        if len(vector) != self.dimensions:
            raise ValueError('Vector dimension mismatch')
        values = [float(v) for v in vector]
        if not all(math.isfinite(v) for v in values) or not any(values):
            raise ValueError('Vector must be finite and nonzero')
        return '[' + ','.join(map(str, values)) + ']'

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Replace the complete strategy snapshot atomically, deleting obsolete IDs."""
        if strategy not in ('A', 'B', 'C') or len(chunks) != len(vectors):
            raise ValueError('Invalid strategy or mismatched chunk/vector counts')
        ids = [c.chunk_id for c in chunks]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate chunk IDs')
        rows = [(strategy, c.chunk_id, c.document_id, c.source, c.page, c.text,
                 Jsonb(c.metadata), self._vector(v)) for c, v in zip(chunks, vectors)]
        with self.connect() as conn:
            # Serialize complete-snapshot ingestion; failed writes roll back deletions too.
            conn.execute(sql.SQL('LOCK TABLE {} IN EXCLUSIVE MODE').format(self.table))
            with conn.cursor() as cur:
                cur.executemany(sql.SQL('''INSERT INTO {} VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)
                    ON CONFLICT(strategy,chunk_id) DO UPDATE SET
                    document_id=EXCLUDED.document_id, source=EXCLUDED.source, page=EXCLUDED.page,
                    text=EXCLUDED.text, metadata=EXCLUDED.metadata, embedding=EXCLUDED.embedding''').format(self.table), rows)
            conn.execute(sql.SQL('DELETE FROM {} WHERE strategy=%s AND NOT (chunk_id = ANY(%s::text[]))').format(self.table), (strategy, ids))

    def count(self, strategy):
        with self.connect() as conn:
            return conn.execute(sql.SQL('SELECT count(*) FROM {} WHERE strategy=%s').format(self.table), (strategy,)).fetchone()[0]

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if strategy not in ('A', 'B', 'C') or not isinstance(top_k, int) or top_k < 1:
            raise ValueError('Invalid strategy/top_k')
        vector = self._vector(query_vector)
        conditions = [sql.SQL('strategy=%s')]
        params = [vector, strategy]
        for name, condition in (filters or {}).items():
            if name not in ('verse_start', 'verse_end') or not isinstance(condition, dict) or len(condition) != 1:
                raise ValueError('Unsupported metadata filter')
            op, value = next(iter(condition.items()))
            if op not in ('lte', 'gte') or type(value) is not int:
                raise ValueError('Unsupported filter operator/value')
            conditions.append(sql.SQL('(metadata->>%s)::integer {} %s').format(sql.SQL('<=' if op == 'lte' else '>=')))
            params.extend([name, value])
        params.append(top_k)
        query = sql.SQL('''SELECT chunk_id, document_id, source, page, text, metadata,
            embedding <=> %s::vector AS distance FROM {} WHERE {}
            ORDER BY distance, chunk_id LIMIT %s''').format(self.table, sql.SQL(' AND ').join(conditions))
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(chunk_id=r[0], document_id=r[1], source=r[2], page=r[3], text=r[4],
                     metadata=r[5], distance=float(r[6]), score=1-float(r[6])) for r in rows]
