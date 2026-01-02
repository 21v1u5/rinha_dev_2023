import os
import asyncio
import uuid
from datetime import date
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException, Response, Query
from pydantic import BaseModel, Field, validator
import asyncpg
import orjson
from fastapi.responses import ORJSONResponse

app = FastAPI(default_response_class=ORJSONResponse)

# Pool de conexões global
pool = None

@app.on_event("startup")
async def startup():
    global pool
    # O host 'db' é o nome do serviço no docker-compose
    pool = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL"),
        min_size=10,
        max_size=20
    )

class PessoaSchema(BaseModel):
    apelido: str = Field(..., max_length=32)
    nome: str = Field(..., max_length=100)
    nascimento: date
    stack: Optional[List[str]] = None

    @validator('stack')
    def validate_stack(cls, v):
        if v is not None:
            if not all(isinstance(i, str) and len(i) <= 32 for i in v):
                # Erro 400 se os elementos não forem strings
                raise ValueError()
        return v

@app.post("/pessoas", status_code=201)
async def create_pessoa(p: PessoaSchema, response: Response):
    p_id = str(uuid.uuid4())
    stack_str = ",".join(p.stack) if p.stack else None
    
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO pessoas (id, apelido, nome, nascimento, stack) VALUES ($1, $2, $3, $4, $5)",
                p_id, p.apelido, p.nome, p.nascimento, stack_str
            )
        response.headers["Location"] = f"/pessoas/{p_id}"
        return {"id": p_id}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=422, detail="Apelido já existe")

@app.get("/pessoas/{p_id}")
async def get_pessoa(p_id: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, apelido, nome, nascimento, stack FROM pessoas WHERE id = $1", p_id)
        if not row:
            raise HTTPException(status_code=404)
        
        # Converte stack de volta para lista
        res = dict(row)
        res['stack'] = res['stack'].split(',') if res['stack'] else None
        return res

@app.get("/pessoas")
async def search_pessoas(t: str = Query(None)):
    if not t:
        raise HTTPException(status_code=400)
    
    async with pool.acquire() as conn:
        # Busca usando o índice GIST que criamos no init.sql
        rows = await conn.fetch(
            "SELECT id, apelido, nome, nascimento, stack FROM pessoas WHERE busca ILIKE $1 LIMIT 50",
            f"%{t}%"
        )
        return [
            {**dict(r), "stack": r['stack'].split(',') if r['stack'] else None}
            for r in rows
        ]

@app.get("/contagem-pessoas")
async def count_pessoas():
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(1) FROM pessoas")
        return Response(content=str(count), media_type="text/plain")