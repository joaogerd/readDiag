 No código **read_prepbufr.f90**, o campo que vira o `iuse` nos DataFrames é a variável **`usage`**; já o **`iusev`** (uso efetivo na análise) **não é definido aqui**: ele é decidido mais adiante no fluxo do GSI (setup/analysis) depois de todos os checks.

A seguir, o resumo objetivo.

# Como o `read_prepbufr` define o `iuse` (variável `usage`)

Logo que a observação é lida, `usage` começa em **0** (elegível a uso). Depois, uma série de regras o alteram para códigos específicos. Eis todas as atribuições explícitas que aparecem no arquivo:

| `iuse`            | Quando o código atribui                                                                                                                | Por quê / interpretação prática                                                                                                                          |                                                        |                                                      |         |                                     |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------- | ------- | ----------------------------------- |
| **0**             | Inicialização (`usage = 0`)                                                                                                            | “candidato a uso” (passou os gates iniciais)                                                                                                             |                                                        |                                                      |         |                                     |
| **100**           | `icuse(nc) <= 0`                                                                                                                       | ConvInfo impede uso (configuração)                                                                                                                       |                                                        |                                                      |         |                                     |
| **100**           | `qm == 15` **ou** `12` **ou** `9`                                                                                                      | *PrepBUFR QM* marcando não-uso/lista de rejeição/hold-out                                                                                                |                                                        |                                                      |         |                                     |
| **101**           | `qm >= lim_qm`                                                                                                                         | *Quality mark* do elemento excedeu o limite (p.ex. 8 se `diag_preselect`, senão 4)                                                                       |                                                        |                                                      |         |                                     |
| **102**           | `convobs` **e** `pqm(k) >= lim_qm`                                                                                                     | *Program/event mark* (PQM) excedeu o limite                                                                                                              |                                                        |                                                      |         |                                     |
| **100**           | `(192 ≤ kx ≤ 195) e psob`                                                                                                              | Regra especial p/ certos KX de pressão superficial (monitorar)                                                                                           |                                                        |                                                      |         |                                     |
| **100**           | `regional e kx==227 e obsdat(1,k) < 400`                                                                                               | Vento MAP acima de 400 mb → monitorar (regional)                                                                                                         |                                                        |                                                      |         |                                     |
| **100**           | `kx==188 e psob e 8º char do sid == 'x'`                                                                                               | Mesonet SLP com ID problemático → monitorar                                                                                                              |                                                        |                                                      |         |                                     |
| **103**           | `gustob` **ou** `visob` **ou** `tdob` **ou** `pmob` **ou** `mxtmob` **ou** `mitmob` **ou** `howvob` **ou** `cldchob` com dado presente | Campos “auxiliares” (rajada, visibilidade, Td, precip, T máx/min, onda, base de nuvem) não são assimilados por este leitor → marcar como “não usar aqui” |                                                        |                                                      |         |                                     |
| **115**           | \`                                                                                                                                     | u                                                                                                                                                        | <0.01`**e**`                                           | v                                                    | <0.01\` | Vento “calmo demais” (sanity check) |
| **116**           | `Td < min(-40 °C, T-10 °C)`                                                                                                            | Td irrealisticamente baixo                                                                                                                               |                                                        |                                                      |         |                                     |
| **117**           | `(T - Td) > 70 °C`                                                                                                                     | Depressão de ponto de orvalho irreal                                                                                                                     |                                                        |                                                      |         |                                     |
| **118**           | `Td > 32.2 °C (90 °F)`                                                                                                                 | Td irrealisticamente alto                                                                                                                                |                                                        |                                                      |         |                                     |
| **= ncmiter(nc)** | *cross-validation por grupos*: `ncnumgrp(nc) > 0` **e** `mod(ndata+1,ncnumgrp)==ncgroup-1`                                             | “hold-out”/validação cruzada (o valor é o índice do grupo/iter); usado para excluir grupos específicos                                                   |                                                        |                                                      |         |                                     |
| **via rotina**    | \`if ((kx>129 && kx<140)                                                                                                               |                                                                                                                                                          | (kx>229 && kx<240)) call get\_aircraft\_usagerj(...)\` | Aeronaves passam por lógica dedicada de rejeição/uso |         |                                     |

Observações úteis do próprio arquivo:

* Há trechos onde **afinam `lim_qm`** (limites de QM) conforme o tipo de variável e o modo (`diag_preselect` ativa o limite 8, senão 4).
* Em trechos de *thinning*, usam a condição `usage < 100` para considerar o ponto “elegível” ao processo — então **qualquer código ≥100 é “não usar/monitorar”** (e não entra em thinning).
* Existem tratamentos específicos por KX/variável (ex.: superfície, MAP wind, Mesonet, camadas de nuvem) além dos *quality marks* genéricos.

# Relação prática `iuse` × `iusev`

* **`iuse` (do `read_prepbufr`)**: “pré-análise”, controla se o dado segue adiante. Pela tua amostra, ele aparece exatamente como acima (0, 100, 101, 102, 103, 115–118, etc.).
* **`iusev` (na análise / rdiagbuf(12))**: “pós-setup/análise”. Em geral:

  * `iusev = +1` quando o dado é de fato **assimilado**; típico quando `iuse == 0` **e** ele passa pelos checks do setup/análise (thinning, *buddy check*, outlier/resíduo, etc.).
  * `iusev = -1` quando o dado é **monitorado** (não assimilado); típico quando `iuse ∈ {100,101,102,103,115–118,...}` ou quando a análise decide descartar por outros motivos (mesmo que `iuse==0`).

> Em outras palavras: **`iuse` codifica o “por quê” do não-uso** em estágio de leitura/QC grosso; **`iusev` é a decisão final da análise**.

# Para o teu pacote (`readDiag`)

Para facilitar a vida do grupo (e não “caçar” significados no Fortran):

1. **Adicionou um decodificador de `iuse`** (análogo ao que fizemos para `pbqc`), por exemplo:

   * `0: "usable"`
   * `100: "not-used: config/QM(9/12/15)/regras especiais"`
   * `101: "not-used: element QM ≥ lim_qm"`
   * `102: "not-used: PQM ≥ lim_qm"`
   * `103: "not-used: aux field (gust/vis/td/pm/maxT/minT/wave/ceil)"`
   * `115–118: "not-used: sanity checks (vento ~0; Td muito baixo/alto; depressão >70°C)"`
   * `ncmiter(nc): "hold-out/cross-validation (grupo {valor})"`
   * `outros`: “code {valor}”.

2. **Filtro canônico** nos plots/scripts:

   * “usados (pré-análise)”: `iuse == 0`
   * “monitorados/não usados”: `iuse >= 100`
   * “usados (análise)”: `iusev == 1`
   * “monitorados (análise)”: `iusev == -1`

3. **Relatórios**: mostrar `value_counts()` de `iuse` com **legenda** (e de `iusev` quando houver), para rapidamente entender por que dados caíram fora.



