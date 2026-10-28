Leia o artigo abaixo e registre o carrossel chamando a ferramenta `registrar_carrossel`.

O carrossel resume UM assunto (o artigo inteiro), em até 10 slides: capa, de 4 a 6 pontos, fechamento "Em resumo" e chamada final para ler o artigo.

Como fazer
- `category`: ciencia, curiosidades, misterios, tecnologia ou outros. Use a categoria sugerida pelo site (`categoria_do_site`) quando fizer sentido.
- `cover_title`: título da capa, fiel ao artigo, sem exagero, até 90 caracteres. Pode ser mais direto e sóbrio que o título original.
- `hook`: primeira linha da legenda, até 140 caracteres, que desperte interesse sem prometer mais do que o artigo mostra.
- `points`: de 4 a 6 pontos na ordem lógica do artigo (o que é / o que foi descoberto / como / por que importa / limites ou dúvidas). Cada um tem `heading` (até 55 caracteres) e `text` (até 250 caracteres, 2 a 3 frases curtas).
- `takeaway`: a ideia central em até 230 caracteres, para o slide "Em resumo".
- `hashtags`: 5 a 8, em português, relacionadas ao tema (sem espaços, sem a palavra "hoje").
- `health_disclaimer`: true se o tema envolver saúde, medicamentos, nutrição ou tratamentos.
- `risk`: "alto" se algum ponto exigir detalhes gráficos, tratar tema proibido, dar conselho médico ou não puder ser resumido com segurança; "medio" se houver tema sensível ou afirmações incertas tratadas com cuidado; "baixo" nos demais. Explique em `reasons`.
