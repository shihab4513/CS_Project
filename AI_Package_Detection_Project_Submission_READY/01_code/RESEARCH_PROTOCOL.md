# Revised Research Protocol

## Research Position

This project does not claim that combining static analysis, dynamic analysis,
and LLMs is new. MalOSS, Amalfi, DySec, and SpiderScan already demonstrate
complementary forms of multi-stage package analysis. The project evaluates a
specific operational question that remains difficult to compare across this
literature: how should a cross-ecosystem npm/PyPI detector allocate expensive
dynamic analysis, record evidence provenance, and handle disagreement between
static and dynamic signals?

## Field-Level Gaps

1. **Comparable cross-ecosystem evidence.** Ladisa et al. use a shared static
   feature space for npm and PyPI, whereas DySec collects PyPI eBPF telemetry and
   SpiderScan models npm behavior graphs. These evidence types are not directly
   comparable. This project uses a normalized evidence schema for package name,
   ecosystem, source findings, process events, file events, network events, and
   collection conditions. It reports results per ecosystem and per direction of
   static transfer.

2. **Triage cost and abstention.** MalOSS and Amalfi show the value of scalable
   screening, while DySec and SpiderScan show the value of deeper behavioral
   inspection. A registry workflow must also quantify how many packages enter
   the expensive stage, how long that stage takes, and what happens when evidence
   is incomplete. The policy in `src/triage.py` queues uncertain static cases,
   preserves low-risk uncertainty, and requires human review for high risk or
   modality disagreement.

3. **Behavior coverage and evasion.** Install-time monitoring can miss delayed,
   environment-gated, or dependency-triggered behavior. Graph matching can miss
   behavior that has no close known graph. The project records trace-collection
   limitations, performs no claim of complete coverage, and treats a clean trace
   as incomplete evidence rather than proof of benignness.

4. **Auditable use of LLMs.** SpiderScan and LAMPS show that LLMs can recognize
   APIs and improve contextual review. Their use does not eliminate the need for
   provenance, reproducible prompts, and abstention. This project gives the LLM
   only cited static and dynamic evidence, forbids claims of unobserved behavior,
   and keeps numerical scores and human review separate from the LLM explanation.

5. **Generalization measurement.** A random combined split can conceal poor
   transfer across ecosystems. `evaluate_static_transfer.py` reports NPM-to-PyPI
   and PyPI-to-NPM results separately. Later evaluation should additionally use
   time- or campaign-separated samples where reliable labels are available.

## Experiment Matrix

| Experiment | Question | Required output |
| --- | --- | --- |
| Static baseline | How does the released feature model perform on a fixed split? | Accuracy, precision, recall, F1, ROC-AUC, confusion matrix |
| Static transfer | Does static evidence transfer in both directions? | NPM-to-PyPI and PyPI-to-NPM metrics |
| Dynamic trace collection | What install-time behavior is observed in an isolated VM? | Normalized trace JSON, collection conditions, duration |
| Triage analysis | How much work moves to dynamic review and when do modalities disagree? | Queue rate, review rate, disagreement rate, analysis time |
| Evidence-grounded review | Can a reviewer understand why a case was referred? | Immutable source/trace references and bounded LLM prompt |
| Target-label efficiency | How many labels from a new ecosystem are needed before source-ecosystem transfer adds little? | Multi-seed F1, ROC-AUC, PR-AUC curves and source-data gain by budget |

## Current Verified Result

Using the released dataset and a Random Forest fallback with seed 42, the
leave-one-ecosystem-out evaluation gave F1 = 0.2016 for NPM-to-PyPI and F1 =
0.3154 for PyPI-to-NPM. These values are not deployment estimates and should
not be compared directly with the paper's combined-split results. They show why
the project must report directional transfer rather than only a combined score.

## Key References

- Duan, R., Alrawi, O., Kasturi, R. P., Elder, R., Saltaformaggio, B., and Lee,
  W. (2021). Towards Measuring Supply Chain Attacks on Package Managers for
  Interpreted Languages. *Proceedings of the Network and Distributed System
  Security Symposium (NDSS 2021).* 
- Sejfia, A., and Schafer, M. (2022). Practical Automated Detection of Malicious
  npm Packages. *Proceedings of the 44th International Conference on Software
  Engineering (ICSE 2022).* 
- Ladisa, P., Ponta, S. E., Ronzoni, N., Martinez, M., and Barais, O. (2023).
  On the Feasibility of Cross-Language Detection of Malicious Packages in npm
  and PyPI. *Proceedings of the Annual Computer Security Applications Conference
  (ACSAC 2023).* 
- Huang, Y., et al. (2024). SpiderScan: Practical Detection of Malicious NPM
  Packages Based on Graph-Based Behavior Modeling and Matching. *Proceedings of
  the 39th IEEE/ACM International Conference on Automated Software Engineering
  (ASE 2024).* https://doi.org/10.1145/3691620.3695492
- Mehedi, S. T., Islam, C., Ramachandran, G., and Jurdak, R. (2026). DySec: A
  Machine Learning-Based Dynamic Analysis for Detecting Malicious Packages in
  PyPI Ecosystem. *IEEE Transactions on Information Forensics and Security,* 21,
  1316-1331. https://doi.org/10.1109/TIFS.2026.3654388
- Zeshan, M. U., Ibiyo, M., Di Sipio, C., Nguyen, P. T., and Di Ruscio, D.
  (2026). Many Hands Make Light Work: An LLM-Based Multi-Agent System for
  Detecting Malicious PyPI Packages. *Journal of Systems and Software.*
