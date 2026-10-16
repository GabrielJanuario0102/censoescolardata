
import sqlite3
from pathlib import Path

import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CSV = BASE_DIR / "Tabela_Matricula_2025_V2.csv"
BANCO_DADOS = BASE_DIR / "../censoescolarapi/censoescolar.db"

# Paginação
TAMANHO_PAGINA = 10_000

ESTADOS = [
    "AL", "BA", "CE", "MA", "PB",
    "PE", "PI", "RN", "SE",
    "ES", "MG", "RJ", "SP",
]

MAPEAMENTO = {
    "NO_ENTIDADE": "no_entidade",
    "CO_ENTIDADE": "co_entidade",
    "NO_UF": "no_uf",
    "SG_UF": "sg_uf",
    "CO_UF": "co_uf",
    "NO_MUNICIPIO": "no_municipio",
    "CO_MUNICIPIO": "co_municipio",
    "NU_ANO_CENSO": "nu_ano_censo",
    "NO_REGIAO": "no_regiao",
    "CO_REGIAO": "co_regiao",
    "QT_MAT_BAS": "qt_mat_bas",
    "QT_MAT_INF": "qt_mat_inf",
    "QT_MAT_FUND": "qt_mat_fund",
    "QT_MAT_MED": "qt_mat_med",
    "QT_MAT_PROF": "qt_mat_prof",
    "QT_MAT_EJA": "qt_mat_eja",
    "QT_MAT_ESP": "qt_mat_esp",
}

COLUNAS_CSV = list(MAPEAMENTO.keys())
COLUNAS_BANCO = list(MAPEAMENTO.values())


SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS tb_instituicao_ensino (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_entidade TEXT NOT NULL,
    co_entidade INTEGER NOT NULL UNIQUE,
    no_uf TEXT NOT NULL,
    sg_uf TEXT NOT NULL,
    co_uf INTEGER NOT NULL,
    no_municipio TEXT NOT NULL,
    co_municipio INTEGER NOT NULL,
    no_mesorregiao TEXT DEFAULT NULL,
    co_mesorregiao INTEGER DEFAULT NULL,
    no_microrregiao TEXT DEFAULT NULL,
    co_microrregiao INTEGER DEFAULT NULL,
    nu_ano_censo INTEGER NOT NULL,
    no_regiao TEXT,
    co_regiao INTEGER,
    qt_mat_bas INTEGER DEFAULT 0,
    qt_mat_inf INTEGER DEFAULT 0,
    qt_mat_fund INTEGER DEFAULT 0,
    qt_mat_med INTEGER DEFAULT 0,
    qt_mat_prof INTEGER DEFAULT 0,
    qt_mat_eja INTEGER DEFAULT 0,
    qt_mat_esp INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
"""


SQL_INSERIR = f"""
INSERT INTO tb_instituicao_ensino (
    {", ".join(COLUNAS_BANCO)}
)
VALUES (
    {", ".join(["?"] * len(COLUNAS_BANCO))}
)
ON CONFLICT(co_entidade) DO UPDATE SET
    {", ".join(
        f"{coluna} = excluded.{coluna}"
        for coluna in COLUNAS_BANCO
        if coluna != "co_entidade"
    )};
"""


def importar_csv():
    if not ARQUIVO_CSV.exists():
        raise FileNotFoundError(
            f"Arquivo CSV não encontrado: {ARQUIVO_CSV}"
        )

    total_lido = 0
    total_filtrado = 0

    with sqlite3.connect(BANCO_DADOS) as conexao:
        conexao.execute(SQL_CRIAR_TABELA)

        leitor = pd.read_csv(
            ARQUIVO_CSV,
            sep=";",
            usecols=COLUNAS_CSV,
            chunksize=TAMANHO_PAGINA,
            encoding="latin1",
            low_memory=False,
        )
        for numero_pagina, pagina in enumerate(leitor, start=1):
            total_lido += len(pagina)

            ano = pd.to_numeric(
                pagina["NU_ANO_CENSO"],
                errors="coerce",
            )

            pagina["SG_UF"] = (
                pagina["SG_UF"]
                .astype("string")
                .str.strip()
                .str.upper()
            )

            pagina = pagina[
                (ano == 2025)
                & pagina["SG_UF"].isin(ESTADOS)
            ].copy()

            if pagina.empty:
                print(f"Página {numero_pagina}: nenhum registro elegível.")
                continue

            # Renomeia as colunas para corresponder ao SQLite
            pagina = pagina.rename(columns=MAPEAMENTO)

            # Converte campos textuais
            for coluna in [
                "no_entidade",
                "no_uf",
                "sg_uf",
                "no_municipio",
            ]:
                pagina[coluna] = pagina[coluna].astype("string")

            # Converte os campos numéricos preservando NULL
            colunas_numericas = [
                "co_entidade",
                "co_uf",
                "co_municipio",
                "nu_ano_censo",
                "co_regiao",
                "qt_mat_bas",
                "qt_mat_inf",
                "qt_mat_fund",
                "qt_mat_med",
                "qt_mat_prof",
                "qt_mat_eja",
                "qt_mat_esp",
            ]

            for coluna in colunas_numericas:
                pagina[coluna] = pd.to_numeric(
                    pagina[coluna],
                    errors="coerce",
                ).astype("Int64")


            pagina["no_mesorregiao"] = None
            pagina["co_mesorregiao"] = None
            pagina["no_microrregiao"] = None
            pagina["co_microrregiao"] = None

            pagina = pagina[COLUNAS_BANCO]

            pagina = pagina.astype(object).where(
                pagina.notna(), None
            )

            registros = list(
                pagina.itertuples(index=False, name=None)
            )

            conexao.executemany(SQL_INSERIR, registros)
            conexao.commit()

            total_filtrado += len(registros)

            print(
                f"Página {numero_pagina}: "
                f"{len(registros)} registros processados."
            )

    print("\nImportação concluída!")
    print(f"Linhas lidas: {total_lido}")
    print(f"Linhas filtradas e processadas: {total_filtrado}")
    print(f"Banco de dados: {BANCO_DADOS}")


if __name__ == "__main__":
    importar_csv()
