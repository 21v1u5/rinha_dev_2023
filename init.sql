
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS pessoas (
    id UUID PRIMARY KEY,
    apelido VARCHAR(32) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    nascimento DATE NOT NULL,
    stack TEXT, -- Armazenaremos a stack como string separada por espaço/vírgula para busca
    -- Coluna gerada para busca rápida que concatena tudo
    busca TEXT GENERATED ALWAYS AS (
        nome || ' ' || apelido || ' ' || COALESCE(stack, '')
    ) STORED
);

-- Índice de busca por similaridade/trigrama
CREATE INDEX IF NOT EXISTS idx_pessoas_busca_gist ON pessoas USING gist (busca gist_trgm_ops);