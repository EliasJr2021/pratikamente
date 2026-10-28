# Pratikamente — carrossel diário no Instagram

Automação que lê os artigos de **pratikamente.com.br** (do mais antigo para o mais recente), usa o **Claude** para resumir cada artigo e revisá-lo, monta um carrossel de até 10 slides (1080×1350) e publica na conta do Instagram do Pratikamente, **um por dia**.

Cada carrossel resume **um único assunto** (o artigo inteiro):

| Slide | Conteúdo |
|---|---|
| 1 · Capa | imagem do artigo (inteira, sem recorte) + título fiel ao texto + categoria |
| 2 a 7 | de 4 a 6 **pontos** do artigo, numerados (título curto + 2 ou 3 frases) |
| penúltimo | **Em resumo**: a ideia central |
| último | chamada para ler o artigo completo no site + @ da conta |

A legenda traz o gancho, a lista de pontos, o link do artigo (com UTM), o aviso informativo e hashtags.

Funciona em **modo manual** no início: cada carrossel vira um Issue com pré-visualização e só é publicado quando você comenta `/aprovar`.

```
prepare.yml (diário) → site → Claude (resume + revisa) → Pillow (slides) → branch `media`
      → Issue "[Aprovar]" → você comenta /aprovar → publish.yml → Instagram
refresh-token.yml (semanal) renova o token do Instagram
```

Este projeto é **independente** do História em Dia: repositório, segredos, token, fila e estado separados.

## Segurança — leia primeiro
- **Nunca cole chaves ou tokens em chats, e-mails ou no código.** Eles só entram em *Settings › Secrets and variables › Actions*.
- O repositório é **público**. Os segredos ficam fora do código.
- Só comentários do **dono** do repositório aprovam publicações (`author_association == OWNER`).
- Defina um **limite de gasto** na conta da API Anthropic.

## Passo a passo

### 1. Criar o repositório (conta EliasJr2021)
1. Em https://github.com/new: nome **`pratikamente`**, **Public**, sem README/.gitignore/licença.
2. Na pasta do projeto:
   ```bash
   git init -b main
   git add .
   git commit -m "Projeto Pratikamente"
   git remote add origin https://github.com/EliasJr2021/pratikamente.git
   git push -u origin main
   ```
3. *Settings › Actions › General › Workflow permissions* → **Read and write permissions** → Save.

### 2. Instagram do Pratikamente
Pré-requisito: a conta é **Profissional** e **pública**.

**Opção A (recomendada): usar o mesmo app da Meta do História em Dia**
1. Em https://developers.facebook.com/apps abra o app que você já criou › **Use cases › Customize › API setup with Instagram Login**.
2. Em **Generate access tokens**, clique em **Add account** › **Continue**.
3. Na janela do Instagram, **confirme qual conta está logada**: se aparecer @historia.em.diaa, use *Não é você?* (ou abra em janela anônima) e entre na conta do **Pratikamente**. Clique em **Save** e **Got it**.
4. Clique em **Generate token** ao lado da conta do Pratikamente e copie o token → segredo **`IG_TOKEN_INICIAL`** deste repositório.
5. Se o painel não permitir uma segunda conta, crie um segundo app com os mesmos passos do História em Dia.

O token de cada conta é diferente. **Não** reutilize o token do História em Dia.

### 3. Segredos deste repositório (*Settings › Secrets and variables › Actions › Secrets*)
| Segredo | Como obter |
|---|---|
| `ANTHROPIC_API_KEY` | Pode ser a mesma do outro projeto ou uma chave nova (mais fácil separar custos) |
| `IG_TOKEN_INICIAL` | Token do passo 2 (conta do Pratikamente) |
| `STATE_KEY` | **Nova** chave: `pip install cryptography && python scripts/gerar_chave.py` |
| `IG_USER_ID` | Opcional; deixe em branco (o robô usa `me`) |

### 4. Variáveis (*Variables*)
| Variável | Padrão | Uso |
|---|---|---|
| `IG_HANDLE` | `@pratikamente.ofc` | @ da conta; aparece no rodapé dos slides (só defina se mudar) |
| `APPROVAL_MODE` | `manual` | `auto` publica sem aprovação quando a revisão está ok |
| `AI_IMAGE_NOTICE` | `false` | `true` se as imagens dos artigos são geradas por IA: acrescenta o aviso e marca o post (`is_ai_generated`) |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | `claude-haiku-5-5` reduz o custo |
| `MAX_SLIDES` | `10` | de 5 a 10 |
| `MIN_TEXT_CHARS` | `1500` | texto mínimo do artigo para gerar o carrossel |
| `SITE_BASE` | `https://pratikamente.com.br` | |
| `MEDIA_BASE_URL` | `raw.githubusercontent.com/…/media` | não precisa de GitHub Pages |

### 5. Fase 0 — testes de viabilidade
*Actions › Fase 0 - testes de viabilidade › Run workflow*, marcando **media** e **instagram**. Confira no log da etapa **Testes**:
- API REST do site com a contagem de artigos e a lista por categoria;
- os artigos mais antigos e mais recentes (a fila começa pelos mais antigos);
- capas utilizáveis e tamanho do texto com `fonte: rest` (≥ 1.500 caracteres) e a prévia do texto;
- URL pública da imagem de teste como `image/jpeg`;
- `username` da conta do Pratikamente e cota de publicação.

### 6. Semana de aprovação manual
1. *Actions › Preparar carrossel › Run workflow* (depois roda sozinho todo dia às 15:00 UTC = 12:00 em Recife).
2. Chega um Issue “[Aprovar] …” com os slides e a legenda (editável no próprio Issue).
3. Comente **`/aprovar`** para publicar ou **`/rejeitar`** para pular o artigo.
4. Itens marcados **retido** foram sinalizados pela revisão automática; leia o motivo antes de aprovar.

**Critério para ligar o modo automático:** 7 posts, pelo menos 6 aprovados sem edição, zero falhas e nenhum conteúdo inadequado. Então defina `APPROVAL_MODE=auto`. Casos de risco continuam exigindo aprovação.

## Regras de conteúdo (prompts/sistema.md)
- Só o que está no artigo; sem fatos, números ou citações novos; incertezas preservadas.
- Títulos precisos, sem sensacionalismo, mesmo que o título original do site seja chamativo.
- **Mistérios e paranormal:** sempre como hipótese, relato ou lenda, nunca como fato comprovado.
- **Saúde:** sem conselho médico, tratamento ou dose; aviso “não substitui orientação de um profissional de saúde” na legenda e no último slide.
- **Temas sensíveis** (suicídio, violência, tragédias): tom sóbrio, sem detalhes de métodos.
- Sem expressões temporais (“hoje”, “recentemente”), pois os artigos podem ser antigos.
- Sem cópia de trechos longos; produtos citados sem tom de propaganda.

## Verificações automáticas
- O robô **não gera carrossel** se o texto do artigo tiver menos de 1.500 caracteres (abre um Issue `falha`).
- O texto vem da API REST do site; a raspagem do HTML é só reserva.
- Posts como “Olá, mundo!” são ignorados.
- Capas em qualquer proporção (1:1, 3:2, 16:9) entram inteiras, sem recorte. Sem capa, usa-se uma capa tipográfica; para trocar a imagem, coloque `overrides/<slug>.jpg`.

## Problemas comuns
| Sintoma | Causa provável |
|---|---|
| Erro de permissão ao publicar | Conta fora do app da Meta ou permissão `instagram_business_content_publish` ausente |
| `username` errado na Fase 0 | O token foi gerado para outra conta; gere de novo logado na conta certa |
| “As imagens não ficaram públicas a tempo” | Defina `MEDIA_BASE_URL` para outra hospedagem |
| Issue com rótulo `falha` | Veja o log; comente `/aprovar` para tentar de novo |
| Cron parou depois de semanas | Repositórios públicos sem atividade por 60 dias perdem agendamentos; o commit semanal do token evita isso |

## Desenvolvimento
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
Fontes: Anton e Lato (SIL Open Font License; licenças em `assets/fonts`).
