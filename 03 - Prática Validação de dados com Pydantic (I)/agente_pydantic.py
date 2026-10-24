import re
from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)

PADRAO_ACAO = re.compile(r"Action:\s*([\w -]+?)\s*:\s*(.+)")


class Ferramenta(str, Enum):
    WEB_SEARCH = "web_search"
    LOOK_WEB_PAGE = "look_web_page"

class ConfigAgente(BaseModel):
    modelo: str = Field(default="openai/gpt-oss-120b", frozen=True)
    api_key: SecretStr = Field(exclude=True)
    max_iteracoes: int = Field(default=15)

class Acao(BaseModel):
    ferramenta: Ferramenta
    entrada: str

    @model_validator(mode="before")
    @classmethod
    def ler_texto(cls, dados):
        if isinstance(dados, str):
            achou = PADRAO_ACAO.search(dados)
            if not achou:
                raise ValueError("Texto sem 'Action: tool: entrada'")
            return {"ferramenta": achou.group(1), "entrada": achou.group(2)}
        return dados

    @field_validator("ferramenta", mode="before")
    @classmethod
    def normalizar_ferramenta(cls, v):
        if isinstance(v, str):
            return v.strip().lower().replace(" ", "_")
        return v

    @field_validator("entrada")
    @classmethod
    def limpar_entrada(cls, v: str) -> str:
        v = v.strip().removesuffix("PAUSE").strip().strip("\"'")
        if not v:
            raise ValueError("A entrada de ferramenta vazia")
        return v

    @model_validator(mode="after")
    def checar_url(self):

        if self.ferramenta is Ferramenta.LOOK_WEB_PAGE and not self.entrada.startswith("http"):
            raise ValueError("look_web_page precisa de um link")
        return self

class Observacao(BaseModel):
    ferramenta: Ferramenta
    resultado: str

    @field_serializer("resultado", when_used="json")
    def encurtar(self, v: str) -> str:
        if len(v) <= 50:
            return v 
        else:
            return v[:50]


def validar(entrada) -> None:
    try:
        acao = Acao.model_validate(entrada)
        print(acao)
    except ValidationError as e:
        print("invalido:")
        for erro in e.errors():
            print(erro["msg"])


def main() -> None:

    exemplos ={ 
        "acao_certa": "Thought: preciso pesquisar Action: web_search: Quem ganhou as eleiçoes de 2022? PAUSE",
        "ferramenta_diferente": "Action: Web Search: Quem ganhou as eleiçoes de 2022 PAUSE",
        "dict": {"ferramenta": "look_web_page", "entrada": "https://eleicoes2022.dev"},
        "ferramenta_inexistente": "Action: google: Quem ganhou as eleiçoes de 2022?",
        "url_invalida": "Action: look_web_page: Quem ganhou as eleiçoes de 2022?",
        "entrada_vazia": 'Action: web_search: ""',
        "sem_formato": "Lula da Silva ganhou as eleiçoes de 2022."
    }
    for entrada in exemplos.values():
        validar(entrada)

    acao = Acao.model_validate(exemplos["acao_certa"])
    print(acao.model_dump())
    print(acao.model_dump(mode="json"))
    print(acao.model_dump_json())

    obs = Observacao.model_validate({"ferramenta": acao.ferramenta, "resultado": "texto " * 15})
    print(obs.model_dump())
    print(obs.model_dump_json())

    config = ConfigAgente(api_key="chave")
    print(config)
    print(config.model_dump())


if __name__ == "__main__":
    main()
