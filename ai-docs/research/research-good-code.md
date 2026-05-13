# Research: Positive Software Development Practices for AI-Agent Guidance

This document synthesizes research from five parallel investigations into authoritative sources on software development practices, with the goal of identifying the most critical elements for guiding AI agents toward "good code." Good code here means: (1) functional as intended **and** (2) easy to change.

This is research and synthesis only — no prescriptive Firebreak instructions are drafted yet. Sources are retained throughout.

The five streams investigated:
- **Stream A — Changeability canon:** Fowler, Beck, Ousterhout
- **Stream B — Clean Code / OO design:** Martin, Metz, Feathers, Hunt & Thomas (with critics)
- **Stream C — Empirical / at-scale:** DORA / Accelerate, SPACE, DevEx, Software Engineering at Google, Lehman's laws, defect-prediction research, Code Red
- **Stream D — Contrarian / pragmatic:** Carmack, Muratori, Hillel Wayne, Dan Luu, Larson, Orosz, Will, Blow
- **Stream E — AI-specific SWE:** Anthropic engineering writing, Willison, Karpathy, Yegge, Litt, Husain, Hashimoto, Ronacher, SWE-agent, Cognition, Aider

---

## I. Cross-Stream Synthesis

### A. What All Five Streams Agree On

Five claims survive every authority, every critic, and the empirical literature.

**1. Software cost is dominated by change cost, not initial-build cost.**
- Canon: Fowler's design-stamina hypothesis (`is-quality-worth-cost.html`); Beck's `cost(software) ≈ coupling`; Ousterhout's "working isn't good enough."
- Empirical: Code Red — low-quality code takes 124% longer per change, has 15× more defects, and generates 9× greater cycle-time variance (Tornhill & Borg 2022).
- Clean Code: Martin's "code is read more often than written"; Metz "the purpose of design is to allow you to do design later."
- Contrarian: Larson's "managing technical quality" treats quality as a continuous organizational concern; Luu's "culture matters" finds bug rates dominated by ownership/review enforcement, not initial cleverness.
- AI: Cherny's "cost per reliable change" as the optimization target.

**2. Coupling is the principal change-tax.**
- Canon: Beck's Constantine's Equivalence — "cost(software) ≈ coupling" — is the cleanest articulation.
- Empirical: DORA finds loose-coupling architecture predicts elite delivery performance; Briand & Wüst find CBO (coupling between objects) and RFC are the strongest fault predictors among code-structure metrics; Hyrum's Law shows coupling escapes formal contracts at scale.
- Clean Code: SOLID's Dependency Inversion, Metz's "depend on things that change less often than you do," Hunt/Thomas's orthogonality, Feathers's seams.
- Contrarian: Carmack's "hidden state is where bugs live," Will's critique of fine-grained encapsulation as state-hiding rather than state-managing, Wayne's specifications-as-coupling-disclosure.
- AI: parallel implementations and context rot are coupling failures (Anthropic, Cognition).

**3. Small, reversible, frequent change beats big-bang.**
- Canon: Beck's tidyings, Fowler's opportunistic refactoring (each change "too small to be worth doing"), Ousterhout's "complexity is incremental."
- Empirical: DORA — elite performers achieve high deploy frequency *and* low change-fail rate; Google's trunk-based development at monorepo scale; Nagappan & Ball — relative churn predicts defects, but the *pattern* of bursts matters more.
- Clean Code: Boy Scout Rule, Metz's Flocking Rules, Feathers' sprout method.
- Contrarian: Larson's "lightweight first, escalate later," Luu's small-frequent-change discipline.
- AI: Anthropic's checkpoint discipline, Hashimoto's session-bounded build pattern, single-purpose subagent runs.

**4. Verification / feedback loops are load-bearing.**
- Canon: Beck's TDD-as-design-pressure, Fowler on tests enabling continuous refactoring, Ousterhout (despite TDD skepticism) on continuous evolution.
- Empirical: DevEx finds feedback-loop latency statistically dominates raw "talent" or "effort" in predicting team output; SPACE multi-dimensional measurement.
- Clean Code: Feathers — testability *is* design feedback ("the deep synergy between testability and good design").
- Contrarian: Wayne's specifications produce evidence about design before code; Luu's "code review as enforcement, not advisory."
- AI: Anthropic — verification gate is "the single highest-leverage thing you can do." Hamel's evals as design pressure.

**5. Friction in the feedback loop dominates raw effort.**
- Empirical: This is the headline finding of DevEx (Noda, Storey, Forsgren, Greiler 2023) and SPACE (Forsgren et al. 2021); Lehman's Law IV (conservation of organizational stability) supports it from a different angle.
- Canon: Beck's `cost(change) = cost(understand) + cost(modify) + cost(validate) + cost(deploy)` — every term is feedback friction.
- Contrarian: Larson's bias-to-experimentation, Luu's normalization-of-deviance, Wayne's design-verification-before-implementation.
- AI: cost per reliable change (Cherny); Anthropic's emphasis on context rot and verification gates is the same claim — friction in the loop is what kills agent productivity.

These five findings are the most defensible foundation for any positive-practices guide. They survive the strongest critics in every camp.

### B. Where the Streams Disagree

Several claims are contested across streams, often with empirical evidence on the heterodox side.

**1. Function size.**
- Clean Code prescriptive (Martin: ≤ 20 lines; Metz: ≤ 5 lines).
- Canon split: Beck/Fowler favor small functions; Ousterhout argues "deep modules" — simple interfaces backed by substantial implementations — and explicitly opposes aggressive Extract-Method.
- **Empirical contradicts strong forms of the small-function rule:** Hatton (1997), Withrow's earlier study, and modern replications find a U-shaped relationship — defect density is *highest* in the smallest modules, drops to a minimum around 200-400 logical SLOC, then rises again. Mechanism: very small functions multiply interface surface and cross human working-memory thresholds in a different way.
- Contrarians reject strongly: Carmack's *Inlined Code Is Better Code* (2007) — "the function least likely to cause a problem is one that doesn't exist"; Muratori's compression-only-after-second-instance.
- Cross-stream verdict: extract for cohesion and naming, not for line-count.

**2. Polymorphism over conditionals.**
- Clean Code prescriptive (Martin's Code Smells chapter).
- Empirical contradicts under performance constraints: Muratori's measurements — polymorphic 35 cycles/op, switch 24, table-driven 3.0-3.5, vectorized 20-25× the polymorphic baseline.
- Canon ambivalent.
- Cross-stream verdict: polymorphism is a tool with measurable costs; "prefer it" without context is empirically unjustified.

**3. TDD strict-test-first.**
- Clean Code prescriptive (Martin's Three Rules).
- Canon strong (Beck originated it).
- Empirical: meta-analyses (Munir, Rafique, Bissi, Karac & Turhan) find quality gains shrink dramatically in high-rigor studies; the real signal is "wrote more tests at all" + "smaller increments," not test-first ordering specifically.
- Contrarians reject (Wayne — specifications find design bugs tests cannot; Luu — empirical evidence is weaker than practitioners claim).
- AI: tests-as-verification-gate, not tests-as-design.
- Cross-stream verdict: testing discipline + small batches is the real driver; the test-first ritual is weakly supported.

**4. Fine-grained encapsulation.**
- Clean Code prescriptive (SOLID, Law of Demeter).
- Contrarians reject: Carmack on hidden state, Will on encapsulation hiding rather than managing shared state, Muratori on access modifiers as bug-prevention theater.
- Canon endorses but with nuance.
- Cross-stream verdict: encapsulation is contextually valuable, dogmatically applied is harmful.

**5. DRY at first repetition.**
- Clean Code prescriptive in popular reading.
- Canon updated: Hunt & Thomas's 20th-anniversary edition narrows DRY to *knowledge* duplication, not surface duplication.
- Clean Code internal critique: Metz's "duplication is far cheaper than the wrong abstraction" (sandimetz.com 2016) and Abramov's "Goodbye, Clean Code" (overreacted.io 2020).
- Contrarians: Muratori's "no reuse until two instances," Blow "start with the specific."
- AI: parallel implementations are a known failure mode — the AI version of premature DRY violation.
- Cross-stream verdict: DRY operates on *knowledge*, applied after the abstraction's shape is observed, not predicted.

**6. Comments.**
- Clean Code: comments are failures (Martin).
- Canon: Ousterhout aggressively pro-comments (cost of missing comments 10-100× cost of incorrect ones); Beck/Fowler nuanced.
- AI shifts the calculus: persistent intent files (CLAUDE.md, AGENTS.md), docstrings, and decision rationale are *load-bearing* for agent comprehension in a way they aren't for humans who can ask each other.
- Cross-stream verdict: intent-revealing comments and persistent rationale documentation are net-positive; pure paraphrase comments are net-negative.

### C. What's Genuinely New in the AI Stream

Five concepts have no real classical analog and constitute additive guidance rather than restatement:

**1. Context as an engineered, finite, lossy resource.** "Context rot" (Anthropic) — model recall accuracy degrades as context fills — is a property of the LLM substrate, not of code. The minimum-sufficient-context discipline is genuinely new design pressure.

**2. Tool / edit-format as a measurable accuracy lever.** Aider's data-driven choice of udiff over whole-file edit format, and SWE-agent's Agent-Computer Interface paper (Yang et al., NeurIPS 2024), establish that tool-interface design is a first-order variable in agent performance — not a convenience.

**3. Eval-driven development.** Hamel Husain's discipline ("write evaluators for errors you discover, not errors you imagine") differs from TDD: failure modes are *discovered through observation* rather than pre-specified. This partially substitutes for traditional design review when iteration speed is the binding constraint.

**4. Adversarial exposure unique to LLMs.** Hallucinated package names ("slopsquatting"), the "lethal trifecta" (private data + external communication + untrusted content), and prompt injection are AI-shaped failure modes with no human-author analog.

**5. Persistent steering / intent capture.** CLAUDE.md, AGENTS.md, skills, and spec-first interview workflows treat the spec as the durable artifact and code as regenerable output. This inverts the classical artifact hierarchy.

### D. Where Empirical Data Undercuts Canonical Advice

The Stream C research is the most epistemically forceful. Several pieces of mainstream advice fail at large-N empirical replication:

- **"Functions should always be small"** — Hatton's U-shape contradicts this for the small extreme.
- **"Cyclomatic complexity is the key complexity metric"** — Graylin et al. (2009) show it correlates r > 0.9 with raw size; size alone is nearly as predictive.
- **"Heavyweight change-approval boards reduce risk"** — DORA finds the inverse correlation.
- **"Mock-heavy unit tests are best practice"** — Google's experience and the maintenance literature both retreat.
- **"TDD reduces defects 40-50%"** — true on average, but largely confounded with "wrote more tests at all"; high-rigor studies show smaller, sometimes insignificant effects.
- **"Code review catches the bugs"** — Bacchelli & Bird (ICSE 2013) show review's *realized* value is comprehension, knowledge transfer, and alternative-design generation; defect detection is real but secondary.

### E. Where Empirical Data Supports Canonical Advice

- Trunk-based development, continuous integration, small batch sizes, fast tests (DORA, Google, DevEx).
- Loose coupling (Briand/Wüst, DORA, Hyrum's Law).
- Active deprecation and migration tooling (Google ch. 15, Lehman Law II).
- Generative culture (Westrum × Accelerate).
- Hotspot-driven refactoring (Nagappan & Ball, Tornhill & Borg).

### F. The Operative Target

The single most defensible synthesis across all five streams: **the durable target is minimizing change cost — not adopting any particular tactic for doing so.** Tactics are contested; the goal is not. A guide framed in terms of changeability outcomes (coupling, knowledge duplication, dependency direction, testability, locality, feedback latency) survives the disagreements. A guide that adopts any specific tactical school's prescriptions verbatim inherits its critics.

Five additional cross-stream observations worth carrying forward:

- **Changeability is the operative quality, but it's not free.** Code that's actively changing benefits; code that's stable does not (Fowler's "repay debt where the system is changing"). Most code in a codebase is rarely changed (Code Red hotspot research). Effort should be proportional to expected change frequency.
- **The bottleneck is feedback latency, not effort.** If a positive-practices guide centers anywhere, this is the place — DevEx, SPACE, Lehman's laws, Anthropic's context-engineering, Beck's cost-of-change decomposition all converge here.
- **Hyrum's Law is load-bearing at scale.** Once an interface has many users, observable behavior — including timing, error format, log strings, allocation patterns — becomes contract. Any guidance about API design has to acknowledge this.
- **Rules without context are dangerous, and every authority says so explicitly** — including Martin and Metz, even when popular reading flattens their work into rules.
- **Code review is the binding ship-constraint.** Hashimoto, Willison, Ronacher (AI stream); Luu (contrarian stream); Bacchelli & Bird (empirical); SE@G ch. 9 (at-scale practice). This is the most uniformly endorsed practice across all five streams.

---

## II. Stream A — The Changeability Canon (Fowler, Beck, Ousterhout)

### A.1 Martin Fowler

**Core thesis.** Fowler frames changeability as an *economic* argument. His central claim, made most explicitly in "Is High Quality Software Worth the Cost?" (martinfowler.com, 2019): **"the cost of high internal quality software is negative"** because the dominant cost in software is the cost of modifying it after first delivery. Software accumulates **"cruft"** — *"deficiencies in internal quality that make it harder than it would ideally be to modify and extend the system further"* (`TechnicalDebt.html`). His Design Stamina Hypothesis (`DesignStaminaHypothesis.html`): design effort delays initial delivery, but accumulating cruft slows future delivery more steeply. The break-even arrives "within a few weeks" for typical projects.

**Top principles.**

1. **Internal quality is invisible to users but dominant in cost.** *"The cost of high internal quality software is negative."* Mechanism: cruft compounds; every change pays interest on it.
2. **Refactoring is small, behavior-preserving transformations done continuously.** *"A series of small behavior-preserving transformations, each of which 'too small to be worth doing'"* (Refactoring 2nd ed., 2018).
3. **The Two Hats — separate refactoring from feature work.** You are *either* adding a feature *or* refactoring; switch hats every few minutes but only wear one at a time.
4. **Opportunistic / preparatory refactoring** — *"make the change easy, then make the easy change."* Worked examples in `articles/preparatory-refactoring-example.html`.
5. **Code smells are detectability heuristics, not defects.** *"A surface indication that usually corresponds to a deeper problem in the system"* (`CodeSmell.html`).
6. **The Technical Debt Quadrant** — sort debt by intent and prudence; not all debt is equivalent.
7. **Repay debt where the system is changing.** *"Zero-tolerance attitude to cruft"* in active areas; stable cruft can sit.
8. **Architecture is the decisions that are hard to change.** From "Making Architecture Matter" (OSCON 2015).
9. **Six refactoring workflows weave into development:** TDD, Litter-Pickup, Comprehension, Preparatory, Planned, Long-Term.

### A.2 Kent Beck

**Core thesis.** Beck's deepest claim — sharpest in his Substack and Tidy First? (2023) — is that **coupling and cohesion are *the* design fundamentals**. *"The cost of software is dominated by the cost of maintenance, the cost of maintenance is dominated by the cost of changes that ripple through the system, and effective software design minimizes the chance of changes propagating"* (`tidyfirst.substack.com/p/coupling-and-cohesion`). Constantine's Equivalence: `cost(software) ≈ coupling`. Decomposed: `cost(change) = cost(understand) + cost(modify) + cost(validate) + cost(deploy)`. Design is *"beneficially relating elements."*

**Top principles.**

1. **Coupling is change-propagation, defined per-change.** *"Two elements are coupled with respect to a particular change if changing one element necessitates changing the other element."* Coupling is always relative to actual change patterns.
2. **Cohesion: put things that change together in one place.** *"Put all the manure in one pile."*
3. **Separate structure changes from behavior changes** — never combine in one commit. Structural changes are reversibly cheap; behavioral changes are not.
4. **Tidy first** — small reversible structural improvements before the behavior change. *"Make the change easy (warning: this may be hard), then make the easy change."* (Beck on X, Sept 25, 2012).
5. **Embrace change rather than predict it** (XP). Speculative structure has *negative* value.
6. **TDD as design pressure**, not just verification. Red-green-refactor as design loop.
7. **Code is communication first** (Implementation Patterns, 2007).
8. **Decouple only when the option has value.** Decoupling has real cost; uncertain change axes don't justify it.
9. **Incremental change over big design** — *"big changes all at once does not work."*

### A.3 John Ousterhout

**Core thesis.** *A Philosophy of Software Design* (2nd ed., 2021): **complexity is the enemy, complexity is incremental, hide it behind deep modules.** Complexity is *"anything related to the structure of a software system that makes it hard to understand and modify the system."* Three operative symptoms: **change amplification, cognitive load, unknown unknowns.** "Strategic programming" — continual small investments in code quality — vs. "tactical programming." Recommended ~10–20% overhead with 6–12-month payoff.

**Top principles.**

1. **Three symptoms of complexity:** change amplification, cognitive load, unknown unknowns.
2. **Deep modules:** simple interface, substantial functionality. *"It's more important for a module to have a simple interface than a simple implementation."*
3. **Hide information; do not pass it through layers.** Information leakage is *de facto* coupling.
4. **Define errors out of existence.** *"Writing code that needs no exceptions to run."* Every error path is a complexity multiplier.
5. **Design it twice.** First idea optimizes for the imaginable case; comparison surfaces hidden costs.
6. **Comments capture what code cannot.** *"The cost of missing comments is easily 10–100× the cost of incorrect comments."*
7. **Strategic programming — invest 10–20% in design.** Tactical accretion produces "tactical tornadoes."
8. **Consistency creates cognitive leverage.**
9. **General-purpose modules tend to be deeper than special-purpose ones.** Counterintuitive to YAGNI.
10. **Software should be designed for ease of reading, not ease of writing.**

### A.4 Disagreements within the Canon

- **Method length.** Martin (Clean Code) prescribes very short methods. Ousterhout: *"As methods get smaller and smaller there is less and less benefit to further subdivision."* Beck/Fowler lean toward Extract-Method. The Ousterhout/Martin debate is documented at `github.com/johnousterhout/aposd-vs-clean-code`.
- **Comments.** Martin: "comments are always failures." Ousterhout: *"the cost of missing comments is easily 10–100x the cost of incorrect comments."* Fowler intermediate; Beck favors intention-revealing names but accepts comments.
- **TDD.** Ousterhout calls strict test-first *"dogmatic"* and argues it can suppress design exploration — direct contradiction of Beck.
- **Speculative design.** Beck/Fowler firmly anti-speculation (YAGNI, simplest-thing-that-works). Ousterhout's "design it twice" and preference for slightly-more-general modules sits at real tension.

### A.5 Convergences within the Canon

- Software cost is dominated by change cost, not initial-build cost.
- Internal quality is invisible to users and economically dominant.
- Complexity / cruft / coupling accumulates incrementally — disease is compounded small drift, not architectural failure.
- Continuous, small, behavior-preserving improvement is the operative practice.
- "Make the change easy, then make the easy change" is universal.
- Readers, not writers, are the audience.
- Locality of change is the operational test of good design.
- Hide what changes; expose what's stable.

### A.6 Stream A Sources

- [Is High Quality Software Worth the Cost?](https://martinfowler.com/articles/is-quality-worth-cost.html)
- [DesignStaminaHypothesis](https://martinfowler.com/bliki/DesignStaminaHypothesis.html)
- [TechnicalDebt](https://martinfowler.com/bliki/TechnicalDebt.html)
- [TechnicalDebtQuadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
- [CodeSmell](https://martinfowler.com/bliki/CodeSmell.html)
- [OpportunisticRefactoring](https://martinfowler.com/bliki/OpportunisticRefactoring.html)
- [Refactoring (2nd ed.)](https://martinfowler.com/books/refactoring.html)
- [An example of preparatory refactoring](https://martinfowler.com/articles/preparatory-refactoring-example.html)
- [Workflows of Refactoring (InfoQ)](https://www.infoq.com/news/2014/01/fowler-workflows-refactoring/)
- [Making Architecture Matter (OSCON 2015)](https://www.youtube.com/watch?v=DngAZyWMGR0)
- [Coupling and Cohesion — Kent Beck](https://tidyfirst.substack.com/p/coupling-and-cohesion)
- [Coupling — Kent Beck](https://tidyfirst.substack.com/p/coupling)
- [Cohesion — Kent Beck](https://tidyfirst.substack.com/p/cohesion)
- [Theory Outline — Kent Beck](https://tidyfirst.substack.com/p/theory-outline)
- [Change — Kent Beck](https://tidyfirst.substack.com/p/change)
- [Structure & Behavior — Kent Beck](https://tidyfirst.substack.com/p/structure-and-behavior)
- [Tidy First? (O'Reilly)](https://www.oreilly.com/library/view/tidy-first/9781098151232/)
- [Kent Beck on X: "make the change easy, then make the easy change"](https://x.com/KentBeck/status/250733358307500032)
- [Implementation Patterns (O'Reilly)](https://www.oreilly.com/library/view/implementation-patterns/9780321413093/)
- [Extreme Programming Explained, 2nd ed.](https://www.amazon.com/Extreme-Programming-Explained-Embrace-Change/dp/0321278658)
- [Working Isn't Good Enough — Ousterhout (Stanford CS190)](https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=working)
- [APoSD vs Clean Code (Ousterhout/Martin debate)](https://github.com/johnousterhout/aposd-vs-clean-code)
- [A Philosophy of Software Design (2nd ed.)](https://www.amazon.com/Philosophy-Software-Design-2nd/dp/173210221X)
- [APoSD review — Pragmatic Engineer](https://blog.pragmaticengineer.com/a-philosophy-of-software-design-review/)

---

## III. Stream B — Object-Oriented Design, Clean Code, and Legacy Practice (Martin, Metz, Feathers, Hunt & Thomas)

### B.1 Robert C. Martin

**Core thesis.** Code quality is a moral and craft obligation. *Clean Code* Ch. 1: *"Code is clean if it can be understood easily — by everyone on the team. Clean code can be read and enhanced by a developer other than its original author. With understandability comes readability, changeability, extensibility and maintainability."* Readability is the prime virtue from which maintainability, testability, extensibility follow. *Clean Architecture* extends this to system level: architectures exist to "minimize the human resources required to build and maintain the required system."

**Top principles.**

1. **Functions should be small, then smaller** — *"hardly ever 20 lines long"* (*Clean Code* Ch. 3).
2. **Functions should do one thing** — *"They should do it well. They should do it only."*
3. **Meaningful names** (Ch. 2) — reveal intent, searchable, pronounceable.
4. **The Boy Scout Rule** — *"Always leave the campground cleaner than you found it."*
5. **SOLID:** SRP, OCP, LSP, ISP, DIP.
6. **Three Rules of TDD** — failing test before production code; minimum failing test; minimum production code.
7. **Comments as failure** — *"Don't comment bad code — rewrite it."*
8. **Polymorphism over conditionals; dependency injection.**
9. **Law of Demeter** — *"don't talk to strangers."*
10. **Tests as first-class code (FIRST: Fast, Independent, Repeatable, Self-validating, Timely).**

### B.2 Critics of Clean Code

Clean Code is one of the most contested books in modern programming.

- **Casey Muratori — "Clean Code, Horrible Performance"** (computerenhance.com, 2023): polymorphic 35 cycles/op, switch 24, table-driven 3.0–3.5, vectorized 20-25× the polymorphic baseline. *"For a certain segment of the computing industry, the answer to 'why is software so slow' is in large part 'because of "clean" code'."*
- **qntm — "It's probably time to stop recommending Clean Code"** (qntm.org/clean, 2020): the *example code* is "dreadful," especially the prime-factors generator and the SetupTeardownIncluder refactor. Critiques the zero-parameter-ideal rule, anti-flag-argument dogma, the "stepdown rule" requiring narrative top-to-bottom reading, and tight coupling to a Java/OO worldview.
- **Dan Abramov — "Goodbye, Clean Code"** (overreacted.io, 2020): *"My code traded the ability to change requirements for reduced duplication, and it was not a good trade."* Cf. "The Wet Codebase" (Deconstruct 2019).
- **Hacker News / bugzmanov / community.** Recurring: function fragmentation forces "jumping"; cognitive load is redistributed not reduced; namespace pollution; unnecessary allocations; over-mocking culture (Codurance "Mocking is an Anti-Pattern"; Thoughtworks "Mockists Are Dead"). bugzmanov's *Clean Code Critique* (2024 review of 2nd ed.) charges Martin "refuses to internalize substantive critiques."
- **Brian Will — "Object-Oriented Programming is Bad"** (YouTube 2016): not a direct Clean Code critique but intersects.
- **Partial defenders.** Evan Teran shows `std::variant`/`std::visit` recovers most performance while staying "clean."

### B.3 Sandi Metz

**Core thesis.** Make object-oriented design *teachable* and relocate "good design" from intuition to predictable mechanics. *"The purpose of design is to allow you to do design later, and its primary goal is to reduce the cost of change."*

**Top principles.**

1. **The Four (later Five) Rules** — classes ≤ 100 lines; methods ≤ 5 lines; ≤ 4 parameters; controllers instantiate one object; views see one instance variable. Fifth rule: break any rule with peer-justified rationale.
2. **"Duplication is far cheaper than the wrong abstraction."** ("The Wrong Abstraction," sandimetz.com 2016). *"When the abstraction is wrong, the fastest way forward is back."*
3. **The Squint Test** — defocus eyes; shape changes flag conditional/loop nests; color changes flag mixed abstraction levels.
4. **Depend on things that change less often than you do** (POODR Ch. 3).
5. **Single Responsibility at the class level** — *"do the smallest possible useful thing."*
6. **Message-based design** — design objects by messages, not data; tell, don't ask.
7. **Shameless Green / "quick green excuses all sins"** (99 Bottles of OOP, 2nd ed. 2020).
8. **Flocking Rules** — find things most alike; find smallest difference; make simplest change that removes that difference.

### B.4 Michael Feathers

**Core thesis.** *"Legacy code is code without tests."* (WELC, 2004). Reframes legacy from "old" to "unsafe to modify." Synergy thesis (NDC 2010 talk): qualities that make code testable are the same that make it changeable.

**Top principles.**

1. **Seams** — *"a place where you can alter behavior in your program without editing in that place"* (preprocessing, link, object).
2. **Characterization tests** — pin actual behavior, not desired behavior.
3. **Legacy Code Change Algorithm:** identify change points → find seams → break dependencies → write tests → make changes → refactor.
4. **Sprout method / sprout class** — new behavior in new method/class, called from legacy.
5. **Wrap method / wrap class** — preserve call-site contract while composing new behavior.
6. **A unit test is not a unit test if** it touches DB/network/filesystem, can't run with others concurrently, or requires environment.
7. **Wrap third-party libraries** — boundary seams; insulate from API churn; substitute in tests.
8. **Testability *is* design feedback.**

### B.5 Andy Hunt & Dave Thomas (Pragmatic Programmer)

**Core thesis.** 20th-anniversary edition (2019) introduces ETC — "Easier to Change" — as the organizing principle. "Good Design Is Easier to Change Than Bad Design" (Tip 14).

**Top principles.**

1. **DRY (Tip 15)** — *"Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."* 20th-ed clarification: about *knowledge*, not lines of code.
2. **Orthogonality (Tip 17)** — changes in one don't affect others.
3. **Tracer Bullets (Tip 20)** — runnable end-to-end skeleton; iterate.
4. **Don't Live with Broken Windows (Tip 5).**
5. **Decoupled Code Is Easier to Change (Tip 44; Tip 46 "no more than one dot").**
6. **There Are No Final Decisions / Reversibility (Tip 18).**
7. **Refactor Early, Refactor Often (Tip 65).**
8. **Good-Enough Software** — negotiated quality.
9. **Knowledge Portfolio (Tip 9).**

### B.6 Disagreements within Stream B

- **Strictness of rules.** Martin prescriptive/moralized; Metz tighter but explicitly heuristic with break-with-justification clause; Hunt/Thomas tips with rationales; Feathers offers algorithm for safely changing code, almost no aesthetic rules.
- **Source of design improvement.** Martin: principles applied. Feathers: tests demanded. Metz operationally aligned with Feathers.
- **DRY.** Martin unqualified. Metz: "duplication is far cheaper than the wrong abstraction." Hunt/Thomas converge with Metz in 20th-ed.
- **Polymorphism vs. conditionals.** Martin near-absolute. Critics show this is wrong when virtual dispatch dominates.
- **Mocking.** Live disagreement (Martin → London school heavy mocks; Feathers/Beck → classicist real-collaborator-where-possible).

### B.7 Convergences within Stream B

- Code is read more than written; readability is first criterion.
- Coupling is the enemy of change.
- Small, single-purpose units beat large, multi-purpose ones (size definitions vary).
- Tests are inseparable from good design.
- Continuous small improvement beats big rewrites.
- Rules are scaffolding for judgment.

### B.8 Stream B Sources

- [Clean Code summary (Wojteklu gist)](https://gist.github.com/wojteklu/73c6914cc446146b8b533c0988cf8d29)
- [Clean Code (Amazon)](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [SOLID — Wikipedia](https://en.wikipedia.org/wiki/SOLID)
- [Boy Scout Rule — 97 Things](https://www.oreilly.com/library/view/97-things-every/9780596809515/ch08.html)
- [Casey Muratori — Clean Code, Horrible Performance](https://www.computerenhance.com/p/clean-code-horrible-performance)
- [SE Radio 577: Casey Muratori on Clean Code](https://se-radio.net/2023/08/se-radio-577-casey-muratori-on-clean-code-horrible-performance/)
- [Evan Teran — Casey Muratori is wrong (but right)](https://blog.codef00.com/2023/04/13/casey-muratori-is-wrong-about-clean-code)
- [Dan Abramov — Goodbye, Clean Code](https://overreacted.io/goodbye-clean-code/)
- [Dan Abramov — The Wet Codebase (Deconstruct 2019)](https://www.deconstructconf.com/2019/dan-abramov-the-wet-codebase)
- [qntm — It's probably time to stop recommending Clean Code](https://qntm.org/clean)
- [bugzmanov — Clean Code Critique (2nd ed. review)](https://bugzmanov.github.io/cleancode-critique/clean_code_second_edition_review.html)
- [Brian Will — OOP is Bad (transcript/discussion)](https://thrawn01.org/concepts/object-oriented-programming-is-bad)
- [Sandi Metz — The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)
- [Sandi Metz — speaking page](https://sandimetz.com/speaking)
- [Sandi Metz' Rules (thoughtbot)](https://thoughtbot.com/blog/sandi-metz-rules-for-developers)
- [Ruby Rogues 87 transcript (Metz' four rules)](https://gist.github.com/henrik/4509394)
- [99 Bottles of OOP](https://sandimetz.com/99bottles)
- [Refactoring with the Squint Test](https://frontendatscale.com/issues/6/)
- [POODR notes](https://github.com/serodriguez68/poodr-notes)
- [Working Effectively with Legacy Code (Amazon)](https://www.amazon.com/Working-Effectively-Legacy-Michael-Feathers/dp/0131177052)
- [Understand Legacy Code — WELC key points](https://understandlegacycode.com/blog/key-points-of-working-effectively-with-legacy-code/)
- [Michael Feathers — Deep Synergy Between Testability and Good Design (NDC)](https://www.youtube.com/watch?v=4cVZvoFGJTU)
- [Sprout Method — Agile Warrior](https://agilewarrior.wordpress.com/2010/11/19/refactoring-legacy-code-sprout-method/)
- [Pragmatic Programmer Tips (official)](https://pragprog.com/tips/)
- [TPP 20th Anniversary](https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/)
- [Tracer Bullets — TPP / artima](https://www.artima.com/articles/tracer-bullets-and-prototypes)
- [Codurance — TDD Anti-Patterns Ch. 2](https://www.codurance.com/publications/tdd-anti-patterns-chapter-2)
- [Thoughtworks — Mockists Are Dead](https://www.thoughtworks.com/insights/blog/mockists-are-dead-long-live-classicists)

---

## IV. Stream C — Empirical Evidence and At-Scale Practice

### C.1 DORA / Accelerate (Forsgren, Humble, Kim)

*Accelerate* (IT Revolution, 2018) synthesizes 4 years of State of DevOps survey data — 23,000+ responses across 2,000+ orgs. Methodologically transparent: PLS-SEM, latent-variable measurement, validity tests. Caveats: self-report data, predictive-statistical claims (not RCT counterfactual).

**Central finding.** Throughput and stability are positively correlated, not in tension. The four keys: deployment frequency, lead time for changes, change failure rate, time to restore. The 24 capabilities most strongly associated with elite performance cluster around continuous delivery, **loosely coupled architecture**, empowered teams, generative culture, monitoring/observability.

**Findings on changeability.** Tightly coupled architectures predict longer lead time and higher change-fail rate. Long-lived branches and infrequent integration correlate with higher change-fail. Low test automation and manual approval gates / external CABs correlate with *worse* stability. Pathological organizational culture (Westrum typology) predicts ~30% lower performance vs. generative cultures.

**Folk wisdom contradicted.** External CABs do *not* reduce risk. Speed does not trade off against quality at elite levels. Velocity *enables* stability via fast recovery and small batches.

**2024 update.** AI-tool adoption was associated with small estimated decrease in throughput (~1.5%) and larger decrease in stability (~7.2%) — framed cautiously.

### C.2 SPACE Framework (Forsgren, Storey, Maddila, Zimmermann, Houck, Butler 2021)

*ACM Queue* 19(1), DOI 10.1145/3454122.3454124. **Productivity cannot be captured by a single metric.** Five dimensions: Satisfaction & well-being, Performance, Activity, Communication & collaboration, Efficiency & flow. **Activity metrics in isolation (lines, commits, PRs/day) are systematically misleading** — easily gamed, poorly correlated with quality.

### C.3 DevEx (Noda, Storey, Forsgren, Greiler 2023)

*ACM Queue* 21(2), DOI 10.1145/3595878. Three dimensions correlate with throughput and quality: **feedback loops, cognitive load, flow state.** Empirical claim: friction in feedback loops (slow CI, slow tests, slow code review, slow deploys) and cognitive load (poor docs, complex setups, bad APIs) **statistically dominate raw "talent" or "effort"** in predicting team output and quality.

### C.4 Software Engineering at Google (Winters, Manshreck, Wright 2020)

Practitioner-experiential at unprecedented scale (~2 billion lines, tens of thousands of engineers). Single-organization caveat applies; no other public source documents this scale.

**Thesis (Ch. 1):** *"Software engineering is programming integrated over time."*

**Findings.**
- **Trunk-based development at scale** (Ch. 16). Long-lived branches explicitly avoided.
- **Code review** (Ch. 9): "the primary developer workflow upon which almost all other processes must hang." Small, atomic CLs preferred.
- **Testing** (Ch. 11–14): pyramid skewed strongly toward fast unit tests; mock-heavy tests treated as anti-pattern ("mocks test how something was done, not what actually happened").
- **Large-scale changes / Rosie** (Ch. 22): infrastructure to shard global refactors, route through ownership, run tests, submit atomically.
- **Deprecation** (Ch. 15): first-class engineering activity requiring discovery, migration, "backsliding prevention" (Tricorder).
- **Style guide / consistency:** strong preference for codebase-wide consistency over local optimum.

**Hyrum's Law:** *"With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody."* (hyrumslaw.com). Implication: at scale, the formal contract converges to the implementation itself.

### C.5 Lehman's Laws of Software Evolution (1980, 1996)

Most relevant:
- **I. Continuing Change** — E-type systems must be continually adapted or become progressively less satisfactory.
- **II. Increasing Complexity** — complexity increases unless explicit work maintains or reduces it.
- **IV. Conservation of Organizational Stability** — work rate is invariant; throwing headcount doesn't linearly accelerate.
- **VII. Declining Quality.**
- **VIII. Feedback System** — software evolution is multi-loop, multi-level feedback.

Herraiz et al. (2013, ACM Computing Surveys 46(2)) systematic review: some laws hold robustly on FOSS replication, others poorly.

### C.6 Defect Prediction Empirics

- **Cyclomatic complexity** correlates r > 0.9 with raw lines of code (Graylin et al. 2009; Fenton & Neil 1999). Provides little predictive power beyond size.
- **Code churn** (Nagappan & Ball, ICSE 2005): relative churn predicts defects with ~89% accuracy on Windows Server 2003. **Change bursts are stronger predictors than total churn.**
- **Coupling/cohesion** (Briand, Daly, Wüst 1998-1999): CBO, RFC, WMC outperform LCOM and DIT for fault-proneness prediction. Empirically supports DORA's loose-coupling claim at code level.
- **Function size** (Hatton 1997, Withrow): **U-shaped relationship.** Defect density highest in smallest modules, drops to minimum around 200-400 logical SLOC, rises again for very large modules. Hatton attributes small-module penalty to interface errors and human working-memory thresholds. **Directly contradicts strong forms of "functions should always be very small."**
- **Code Red** (Tornhill & Borg, TechDebt 2022, arXiv:2203.04374). 39 codebases, 30,737 files. **Low-quality code: 15× more defects, 124% longer issue resolution, 9× longer maximum cycle time, ~42% of developer time wasted.**

### C.7 Code Review at Scale (Bacchelli & Bird, ICSE 2013)

Microsoft observation, interview, survey study. **Review's stated purpose (defect detection) is not its primary realized outcome.** Dominant value is code/change understanding, knowledge transfer, alternative-design suggestion, team awareness. McIntosh et al. (2016) finds review coverage and participation correlate with reduced post-release defects, but mediated by reviewer engagement.

### C.8 TDD Meta-Analyses

- Munir et al. (IEEE TSE 40(10), 2014); Rafique & Mišić (IEEE TSE 39(6), 2013); Bissi et al. (IST 74, 2016); Karac & Turhan (IEEE Software 35(4), 2018).
- 76% report internal-quality improvement; 88% external-quality improvement; 40-50% defect-density reductions in some industrial studies.
- **Productivity split** — academic studies often show gains; ~44% of industrial studies show losses.
- **Quality gains shrink in high-rigor studies.**
- **Real driver appears to be "writing more tests at all" + "smaller increments,"** not strict test-first ordering. Test-last with comparable coverage performs similarly (Fucci et al., ESEM 2016).

### C.9 Westrum Culture × Performance

Westrum (2004). Used in *Accelerate* Ch. 3 as measurement instrument. Generative cultures predict ~30% higher organizational performance and significantly better delivery metrics. Mediating mechanism: **information flow** — relevant, timely, reaching the right person.

### C.10 Cross-Stream Convergence (within empirical findings)

1. **Loose coupling and small batch size are the two most consistently validated technical practices.**
2. **Friction in feedback loops dominates raw effort.**
3. **Complexity growth is the default; explicit work is required to fight it.**
4. **Hyrum's Law is a load-bearing constraint at scale.**

### C.11 Stream C Sources

- [DORA 2024 Report (PDF)](https://services.google.com/fh/files/misc/2024_final_dora_report.pdf)
- [DORA 2024 announcement](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report)
- [DORA Four Keys guide](https://dora.dev/guides/dora-metrics-four-keys/)
- [DORA: Generative culture capability](https://dora.dev/capabilities/generative-organizational-culture/)
- [Accelerate (IT Revolution)](https://itrevolution.com/product/accelerate/)
- [24 Key Capabilities (IT Revolution)](https://itrevolution.com/articles/24-key-capabilities-to-drive-improvement-in-software-delivery/)
- [SPACE — ACM Queue 19(1), DOI 10.1145/3454122.3454124](https://dl.acm.org/doi/10.1145/3454122.3454124)
- [SPACE on ACM Queue (open)](https://queue.acm.org/detail.cfm?id=3454124)
- [DevEx — ACM Queue 21(2), DOI 10.1145/3595878](https://dl.acm.org/doi/10.1145/3595878)
- [DevEx in Action — ACM Queue 21(6), DOI 10.1145/3639443](https://dl.acm.org/doi/10.1145/3639443)
- [Software Engineering at Google — abseil.io](https://abseil.io/resources/swe-book/)
- [SE@G ch.1](https://abseil.io/resources/swe-book/html/ch01.html)
- [SE@G ch.9 Code Review](https://abseil.io/resources/swe-book/html/ch09.html)
- [SE@G ch.15 Deprecation](https://abseil.io/resources/swe-book/html/ch15.html)
- [SE@G ch.22 Large-Scale Changes / Rosie](https://abseil.io/resources/swe-book/html/ch22.html)
- [Hyrum's Law](https://www.hyrumslaw.com/)
- [Lehman 1980 (UT Austin PDF)](https://users.ece.utexas.edu/~perry/education/SE-Intro/lehman.pdf)
- [Lehman Laws Revisited (1996)](https://www.rose-hulman.edu/class/cs/csse375-2007-08/Handouts/LawsOfSoftwareEvolutionRevisited.pdf)
- [Herraiz et al., ACM CSUR 46(2), 2013, DOI 10.1145/2543581.2543595](https://dl.acm.org/doi/10.1145/2543581.2543595)
- [Lehman's laws — Wikipedia](https://en.wikipedia.org/wiki/Lehman%27s_laws_of_software_evolution)
- [Nagappan & Ball, ICSE 2005, Code Churn (PDF)](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/icse05churn.pdf)
- [Nagappan, Ball, ICSE 2006, Mining Metrics](https://www.st.cs.uni-saarland.de/publications/files/nagappan-icse-2006.pdf)
- [Nagappan, Ball, Zeller — Change Bursts](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/bursts.pdf)
- [Code Red — arXiv:2203.04374](https://arxiv.org/abs/2203.04374)
- [Code Red, ACM TechDebt 2022, DOI 10.1145/3524843.3528091](https://dl.acm.org/doi/10.1145/3524843.3528091)
- [Bacchelli & Bird, ICSE 2013 (PDF)](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/ICSE202013-codereview.pdf)
- [Bacchelli & Bird — IEEE Xplore](https://ieeexplore.ieee.org/document/6606617/)
- [Bissi et al., IST 74, 2016](https://www.sciencedirect.com/science/article/abs/pii/S0950584916300222)
- [Munir/Rafique TDD meta-analysis](https://www.researchgate.net/publication/260649027_The_Effects_of_Test-Driven_Development_on_External_Quality_and_Productivity_A_Meta-Analysis)
- [Function-length empirical literature overview](https://softwarebyscience.com/very-short-functions-are-a-code-smell-an-overview-of-the-science-on-function-length/)
- [Westrum culture & DevOps](https://itrevolution.com/articles/westrums-organizational-model-in-tech-orgs/)

---

## V. Stream D — Contrarian and Pragmatic Voices

### D.1 John Carmack

**Thesis.** Modularity hides state, and hidden state is where bugs live. *Inlined Code Is Better Code* (2007): *"The function that is least likely to cause a problem is one that doesn't exist, which is the benefit of inlining it."* From *Functional Programming in C++* (2012): *"A large fraction of the flaws in software development are due to programmers not fully understanding all the possible states their code may execute in."*

**Top principles.**
1. **Awareness over hiding.** *"Awareness of all the code that is actually executing is important."*
2. **Sequential code should look sequential.** Disavows the small-function rule he previously endorsed.
3. **Functions should not be partially called from elsewhere.** *"Lots and lots of bugs stem from this."*
4. **Pure functions for state discipline.**
5. **Const-correctness as poor man's purity.** Mutating methods are "anti-functional behavior."
6. **Inlining + functional style** is not a contradiction — both minimize hidden state.
7. **Pragmatism over language tribalism.**

**Rejects.** Small-function dogma. Tell-don't-ask mutating-method OO. Modularity as automatic virtue.

### D.2 Casey Muratori

**Thesis.** *"It simply cannot be the case that we're willing to give up a decade or more of hardware performance just to make programmers' lives a little bit easier."* (Clean Code, Horrible Performance, 2023). Performance is a first-class correctness property of professional code.

**Top principles.**
1. **Make code usable before reusable.** *"I don't reuse anything until I have at least two instances of it occurring."* (Compression Oriented Programming).
2. **Compression over abstraction.** Don't predict reuse.
3. **Operation-major, not type-major, organization.** Tables over hierarchies enable 10–15× speedups.
4. **Granularity continuity** — never high-level functions without trivially-replaceable low-level ones.
5. **Total cost is the only metric.** "Clean" and "elegant" are decoys.
6. **Encapsulation is not a virtue per se.**
7. **CRC cards and UML are wasteful.**

**Rejects.** Polymorphism over if/else. Functions-should-be-small. DRY-as-commandment. Refactoring-first methodologies.

### D.3 Hillel Wayne

**Thesis.** Engineering is the deliberate use of techniques to produce evidence about systems before/instead of running them. *"Something becomes engineering if enough engineers say it's engineering."* (Are We Really Engineers?). *"An hour of modeling will catch issues that days of writing tests will miss."* (Business Case for Formal Methods).

**Top principles.**
1. **Design verification ≠ code verification.** Most "complex, subtle, dangerous" bugs are design bugs, unreachable by unit tests.
2. **Tests find bugs you already imagined.** Specifications examine the state space.
3. **Specification forces understanding.**
4. **Engineering identity is circumstance, not essence.**
5. **Adoption barriers are social, not technical.**
6. **Formal methods exist on a spectrum** — comprehensive testing, types, Cleanroom-style discipline get most of the value short of full proof.

**Rejects.** "TDD is design enough." Software's domain making engineering inapplicable.

### D.4 Dan Luu

**Thesis.** Empirical basis for software's most-repeated rules is weaker than practitioners assume. What predicts good output is engineering culture — ownership, quality mindset, code review enforcement — not methodology, language, or process. *"If you tell people they should do it, that helps a bit. If you enforce better practices via code review, that helps a lot."* (Normalization of deviance).

**Top principles.**
1. **Culture is the dominant variable.** Centaur, ~100 engineers: lowest serious production bug rate of any company Luu worked at, well under one per year.
2. **Empirical evidence for any practice is weak.**
3. **Tests and reasoning are complements, not substitutes.**
4. **Normalization of deviance is the silent killer.**
5. **Essential vs. accidental complexity is mostly accidental.**
6. **Boring languages are underrated for hard problems.**

**Rejects.** Methodology hype without measurement. Confident claims of large effects from typing/language/methodology choices.

### D.5 Will Larson

**Thesis.** Technical quality is a continuous organizational concern. *"Pick the cheapest, most straightforward tool likely to work."* (Managing Technical Quality).

**Top principles.**
1. **Lightweight first, escalate later.**
2. **Prefer experimentation over analysis.**
3. **Work the policy, not the exceptions.**
4. **Strategy must guide tradeoffs, not project alignment.**
5. **Top-down strategy describes wishes, not reality.**
6. **Quality decay is normal, not a crisis.** *"At a well-run and successful company, most of your previous technical decisions won't meet your current quality threshold."*
7. **Setting technical direction is product management for technology.**

### D.6 Gergely Orosz

**Thesis.** Most failure modes at senior levels are about alignment, scope, and follow-through, not technical sophistication.

**Top principles.**
1. Define Done before starting.
2. Pseudoproductivity is the enemy of impact.
3. Identify stakeholders early — upstream and downstream.
4. Document weekly wins (worklog).
5. Trade short-term urgency against long-term technical decisions deliberately.
6. Boring tech wins when you have to ship.

### D.7 Brian Will

*"OOP demands that we then organize program state manipulation into the same hierarchy, which is extremely difficult when we have a non-trivial amount of state."* Object decomposition is arbitrary; singletons are global variables in disguise. Procedural + functional > OOP.

### D.8 Jonathan Blow

*"Software is actually in decline right now."* (Preventing the Collapse of Civilization, DevGAMM 2019). Abstraction is not free; productivity per programmer approaches zero despite hardware gains because complexity grows faster than capability. Start with the specific, concrete solution.

### D.9 Convergences within Stream D

1. **Rules without context are dangerous.**
2. **Compression beats abstraction.** Build the concrete thing, notice duplication, then compress — not predict-the-abstraction-first.
3. **Hidden state is the enemy.**
4. **Evidence over taste.**
5. **Total cost is the only metric.**
6. **Code review as enforcement, not advisory.**

### D.10 Stream D Sources

- [Carmack — Inlined Code Is Better Code (2007)](http://number-none.com/blow/john_carmack_on_inlined_code.html)
- [Carmack — Functional Programming in C++](http://sevangelatos.com/john-carmack-on/)
- [Carmack on Lex Fridman #309](https://lexfridman.com/john-carmack/)
- [Muratori — Clean Code, Horrible Performance](https://www.computerenhance.com/p/clean-code-horrible-performance)
- [Muratori — Semantic Compression](https://caseymuratori.com/blog_0015)
- [Muratori — Complexity and Granularity](https://caseymuratori.com/blog_0016)
- [Muratori — Handmade Hero forum on encapsulation](https://hero.handmade.network/forums/code-discussion/t/3151-caseys_programming_methods_and_encapsulation)
- [Hillel Wayne — Are We Really Engineers?](https://www.hillelwayne.com/post/are-we-really-engineers/)
- [Hillel Wayne — Why Don't People Use Formal Methods?](https://www.hillelwayne.com/post/why-dont-people-use-formal-methods/)
- [Hillel Wayne — Business Case for Formal Methods](https://www.hillelwayne.com/post/business-case-formal-methods/)
- [Dan Luu — Culture matters](https://danluu.com/culture/)
- [Dan Luu — Testing v. informal reasoning](https://danluu.com/tests-v-reason/)
- [Dan Luu — Normalization of deviance](https://danluu.com/wat/)
- [Dan Luu — Empirical PL](https://danluu.com/empirical-pl/)
- [Dan Luu — Against essential and accidental complexity](https://danluu.com/essential-complexity/)
- [Larson — Staff Engineer book](https://staffeng.com/book/)
- [Larson — Managing Technical Quality](https://lethain.com/managing-technical-quality/)
- [Larson — Engineering strategy.](https://lethain.com/engineering-strategy/)
- [Orosz — Software Engineer's Guidebook](https://www.engguidebook.com/)
- [Orosz — Pragmatic Engineer newsletter](https://newsletter.pragmaticengineer.com/)
- [Brian Will — OOP: A Personal Disaster](https://medium.com/@brianwill/object-oriented-programming-a-personal-disaster-1b044c2383ab)
- [Brian Will — OOP Is Bad (YouTube 2016)](https://www.youtube.com/watch?v=QM1iUe6IofM)
- [Blow — Preventing the Collapse of Civilization (DevGAMM 2019)](https://www.youtube.com/watch?v=ZSRHeXYDLko)
- [Blow — Preventing Collapse transcript](https://codigoyfika.github.io/site/preventing-collapse/)

---

## VI. Stream E — AI-Specific Software Engineering

### E.1 Anthropic Public Engineering Writing

**"Building effective agents"** (Schluntz & Zhang, Dec 19 2024): three principles — **maintain simplicity, prioritize transparency, carefully craft the agent-computer interface (ACI).** Sharp distinction between *workflows* (LLMs orchestrated through predefined paths) and *agents* (LLMs dynamically directing). Six composable patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, autonomous agents.

**Claude Code best practices.** Single load-bearing claim: *"Most best practices are based on one constraint: Claude's context window fills up fast, and performance degrades as it fills."* "Give Claude a way to verify its work" is *"the single highest-leverage thing you can do."* Four-phase loop: **Explore → Plan → Implement → Commit.** Necessity Test for every CLAUDE.md line: *"Would removing this cause Claude to make mistakes? If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"*

**"Effective context engineering for AI agents"** (Sep 2025): defines context engineering as *"strategies for curating and maintaining the optimal set of tokens during LLM inference."* Names "context rot": *"as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases."*

**Schluntz SWE-bench Verified writeup** (Oct 2024): the agent that achieved 49% used **just two tools (Bash and Edit)** with deliberately short prompts. *"Our design philosophy ... was to give as much control as possible to the language model itself, and keep the scaffolding minimal."* Tool descriptions are the design surface: *"much more attention should go into designing tool interfaces for models, the same way that a large amount of attention goes into designing tool interfaces for humans."*

**Boris Cherny (Pragmatic Engineer interview).** *"Plan mode, iterating on the plan, then letting it one-shot the implementation."* Search uses *"plain glob and grep, driven by the model"* rather than vector retrieval. Optimization target: **"cost per reliable change."** Migration discipline: *"always make sure that when you start a migration, you finish the migration."* Cites Meta data: *"code quality has a measurable, double-digit-percent impact on engineering productivity."*

**Top actionable principles.**
1. **Verification gate is first-class.**
2. **Explore → Plan → Implement → Commit.**
3. **Keep context minimum-sufficient.** Prune CLAUDE.md ruthlessly; clear context between unrelated tasks.
4. **Prefer fewer, well-documented tools.**
5. **Use hooks for must-happen invariants.**
6. **Spec-first interview pattern.**

**Failure modes named, with positive flips.**
- Kitchen-sink session → `/clear` between unrelated tasks.
- Correcting over and over → after two failures, clear and re-prompt.
- Over-specified CLAUDE.md → Necessity Test on every line.
- Trust-then-verify gap → "if you can't verify it, don't ship it."
- Infinite exploration → scope investigations; subagents in separate context windows.

### E.2 Simon Willison

Treats LLM *"like a digital intern, hired to type code for me based on my detailed instructions."* Single most repeated rule: *"the one thing you absolutely cannot outsource to the machine is testing that the code actually works."*

Vibe coding distinction: *"Vibe coding is *not* the same thing as writing code with the help of LLMs!"* His professional rule: *"I won't commit any code to my repository if I couldn't explain exactly what it does to somebody else."*

Working definition: *"An LLM agent runs tools in a loop to achieve a goal."* Designing Agentic Loops (Sep 2025) — best problems have **clear success criteria** that benefit from **trial and error** (debugging, optimization, dependency upgrades, container sizing). YOLO-mode tradeoff: *"so dangerous, but it's also key to getting the most productive results"* — runs in containers/Codespaces.

**Lethal trifecta:** private data + external communication + untrusted content. Canonical framing for prompt-injection-induced exfiltration.

### E.3 Andrej Karpathy

**Vibe coding (Feb 2025):** *"embrace exponentials, and forget that the code even exists."* Appropriate for low-stakes throwaway prototyping.

**Software 3.0 (YC AI Startup School, June 2025):** prompts as new source code; English as new programming language. Notable for *qualifying* vibe coding inside a more disciplined frame — **autonomy sliders**, **faster generation–verification loops** with humans as **"quality arbiters and loop accelerators."** *"Demo is works.any(), product is works.all()."* Notes LLM "jagged intelligence" and **"anterograde amnesia"** of context-bound systems. His own AI speedups *"vanished shortly after getting local code running"* — production ecosystems *"designed for webdev experts to keep their jobs, and not accessible to AI."*

### E.4 Steve Yegge

"Cheating is all you need" (Sourcegraph, March 2023): *"LLMs aren't just the biggest change since social, mobile, or cloud — they're the biggest thing since the World Wide Web."* The data moat / context engine argument: success depends on intelligently populating the LLM's limited context window. *"The data moat is how you populate the context window."* This 2023 framing prefigured "context engineering."

### E.5 Geoffrey Litt

"Malleable software in the age of LLMs" (March 2023): chat alone is insufficient. *"Chat is an essentially limited interaction mode, regardless of the quality of the bot."* Layered model: direct manipulation in inner loop, AI-assisted tool modification in outer loop. **LLM as local developer** helping users *"grow their own capacity to work in the medium."*

### E.6 Hamel Husain

Evals as design pressure. *"Your AI Product Needs Evals"* (March 2024): *"Success with AI hinges on how fast you can iterate."*

**Top principles.**
- *"Don't rely on generic evaluation frameworks. Create an evaluation system specific to your problem."*
- *"Remove all friction from the process of looking at data."*
- *"You are doing it wrong if you aren't looking at lots of data."*
- *"Write evaluators for errors you discover, not errors you imagine."*
- Three levels: unit-test-like assertions; logged traces with human + LLM-judge review; A/B testing.
- LLM-as-judge must be custom-built and aligned to human pass/fail labels. *"Generic evaluations waste time and create false confidence."*
- Bootstrapping: *"Spend 30 minutes manually reviewing 20–50 LLM outputs"* in a notebook before building infrastructure.

**Most common AI dev mistake** (Field Guide 2025): the **"tools-first mindset"** — building dashboards/frameworks before understanding. NurtureBoss case: three error categories accounted for >60% of problems; targeted fixes lifted date-handling success from 33% → 95%.

### E.7 Practitioner Failure-Mode Reports

**Mitchell Hashimoto (Ghostty)** documents a 16-session, ~$16, ~8-hour build of a real production feature. Operating rules: *"Please don't ever ship AI-written code without a thorough manual review,"* *"I'm not shipping code I don't understand."* End-of-session ritual: *"Are there any other improvements you can see... Don't write any code"* before concluding.

**Harness engineering:** AGENTS.md updates to steer agents away from repeated errors; verification scripts so agents can validate their own work — *"give agents a way to verify [their] work so they fix [their] own mistakes."*

**Armin Ronacher (2025 series).** Most useful longitudinal failure-mode log.
- "Things That Didn't Work" (July 2025): slash commands underdelivered (`/fix-bug` no better than pasting issue URL; `/commit` "never matched my style"); hooks failed efficiency gains; sub-tasks/parallel agents created mix-of-reads-and-writes problems. Hidden risk: *"It encourages mental disengagement. When you stop thinking like an engineer, quality drops."*
- "Agent Design Is Still Hard" (Nov 2025): SDK abstractions break under real conditions; *"the differences between models are significant enough that you will need to build your own agent abstraction."* Reinforcement (re-injected reminders inside the loop) doing more heavy lifting than expected.
- "A Year of Vibes" (Dec 2025): warns against parasocial attachment to agents; unreviewed agent-generated open-source PRs are *"quite frankly an insult."*

**Drew DeVault** ("The cults of TDD and GenAI," Jan 2026): both TDD culture and AI coding agents exploit the same psychological need — the desire to feel like a great programmer. AI tooling can produce work that *looks* excellent at the artifact level while degrading underlying judgment.

### E.8 Research and Tooling

**SWE-agent** (Yang et al., NeurIPS 2024, arXiv:2405.15793): *"LM agents represent a new category of end users with their own needs and abilities, and would benefit from specially-built interfaces."* Custom Agent-Computer Interface produced SOTA results; interface design is a *first-order* variable.

**Cognition's "Don't Build Multi-Agents"** (June 2025): two principles — *"Share context, share full agent traces, not just individual messages"* and *"actions carry implicit decisions, and conflicting decisions carry bad results."* Flappy Bird parable: one sub-agent builds Mario-style background while another builds non-matching bird. *"Context Engineering is the #1 job of engineers building AI agents."* Multi-agent collaboration *"only results in fragile systems."*

**Aider** (Paul Gauthier): edit format is a tool-design choice with measurable accuracy impact. Different models pair with different formats (whole, diff, diff-fenced, udiff). Repo-map (tree-sitter + PageRank) as context-engineering primitive.

**SWE-bench Verified** (OpenAI Aug 2024): 500 human-validated GitHub-issue tasks. Anthropic 49% with Sonnet 3.5 (Oct 2024); current leaderboard ~77% with reports of >90%.

### E.9 What's Genuinely AI-Specific

- **Context as engineered, finite, lossy resource.**
- **Verification as design pressure that closes inside the agent**, not just at human review.
- **Tool-interface design for non-human consumers.**
- **Edit format as accuracy lever.**
- **Eval-driven development** — failure-mode taxonomy *discovered*, not pre-specified.
- **Spec-first / interview-first workflows.**
- **Intent capture and persistence (CLAUDE.md / AGENTS.md / skills).**
- **Agent-loop hygiene** (reinforcement, loop budgets, sub-agent context isolation).
- **Adversarial exposure** — prompt injection, lethal trifecta, slopsquatting (~20% of LLM-suggested packages were nonexistent in one 2025 study).

### E.10 What Largely Transfers from Classical Advice

- Test-first workflows, small reversible changes, low coupling, clear naming, single-responsibility — all remain valid; LLMs read surrounding code as context, so they benefit similarly to humans (or arguably more).
- Code review remains the binding ship-constraint.
- "Address root causes, not symptoms" is Beck/Fowler vintage; what's new is having to *say it explicitly* because the model otherwise patches symptoms.

### E.11 AI-Internal Disagreements

- **Vibe coding vs. spec-first.** Karpathy original celebrates throwaway autonomy; Willison/Anthropic come down spec-first. Karpathy's later writing (autonomy sliders, generation–verification loops) closes much of the gap.
- **Multi-agent vs. single-threaded.** Cognition argues multi-agent is fragile by construction; Anthropic recommends subagents for *isolated read-heavy investigation with summarized return*.
- **Abstractions vs. raw SDKs.** Ronacher anti-framework until things settle; Anthropic itself uses thin scaffolding.
- **Eval-driven vs. capability-driven.** Hamel — evals are rate-limiter; Anthropic — start with *"single LLM calls with retrieval and in-context examples."*
- **Optimism on autonomy.** Hashimoto/Ronacher trust on well-scoped tasks but warn on brownfield; DeVault wholesale rejects; Cherny/Schluntz think agentic coding is *the* future.

### E.12 Stream E Sources

- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)
- [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic — Raising the bar on SWE-bench Verified](https://www.anthropic.com/research/swe-bench-sonnet)
- [Pragmatic Engineer — Building Claude Code with Boris Cherny](https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny)
- [Simon Willison — Here's how I use LLMs to help me write code](https://simonwillison.net/2025/Mar/11/using-llms-for-code/)
- [Simon Willison — Not all AI-assisted programming is vibe coding](https://simonwillison.net/2025/Mar/19/vibe-coding/)
- [Simon Willison — Designing agentic loops](https://simonwillison.net/2025/Sep/30/designing-agentic-loops/)
- [Simon Willison — 2025 year in LLMs](https://simonwillison.net/2025/Dec/31/the-year-in-llms/)
- [Karpathy — original vibe coding tweet](https://x.com/karpathy/status/1886192184808149383)
- [Latent Space — Karpathy "Software 3.0" recap](https://www.latent.space/p/s3)
- [Steve Yegge — Cheating is all you need](https://sourcegraph.com/blog/cheating-is-all-you-need)
- [Geoffrey Litt — Malleable software in the age of LLMs](https://www.geoffreylitt.com/2023/03/25/llm-end-user-programming.html)
- [Hamel Husain — Your AI product needs evals](https://hamel.dev/blog/posts/evals/)
- [Hamel Husain — LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/)
- [Hamel Husain — Field Guide to Rapidly Improving AI Products](https://hamel.dev/blog/posts/field-guide/)
- [Mitchell Hashimoto — My AI adoption journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [Mitchell Hashimoto — Vibing a non-trivial Ghostty feature](https://mitchellh.com/writing/non-trivial-vibing)
- [Armin Ronacher — Agentic Coding Recommendations](https://lucumr.pocoo.org/2025/06/12/agentic-coding/)
- [Armin Ronacher — Things That Didn't Work](https://lucumr.pocoo.org/2025/7/30/things-that-didnt-work/)
- [Armin Ronacher — Agent Design Is Still Hard](https://lucumr.pocoo.org/2025/11/21/agents-are-hard/)
- [Armin Ronacher — A Year of Vibes](https://lucumr.pocoo.org/2025/12/22/a-year-of-vibes/)
- [Drew DeVault — The cults of TDD and GenAI](https://drewdevault.com/blog/Cult-of-TDD-and-LLMs/)
- [SWE-agent paper — arXiv:2405.15793](https://arxiv.org/abs/2405.15793)
- [Cognition — Don't Build Multi-Agents (HN)](https://news.ycombinator.com/item?id=45096962)
- [Aider — Edit formats](https://aider.chat/docs/more/edit-formats.html)
- [SWE-bench Verified leaderboard](https://www.swebench.com/)
- [Slopsquatting / hallucinated package names](https://devops.com/ai-generated-code-packages-can-lead-to-slopsquatting-threat-2/)

---

## VII. Research Methodology Notes

Five parallel subagents conducted independent literature searches (web search + primary-source retrieval) on the streams above. Each agent was instructed to:
- Treat human-author advice as also applicable to AI agents (per project framing).
- Capture direct quotes with full citations.
- Document disagreements within and between authorities, not just consensus.
- Flag claims they could not verify.

Synthesis (Section I) was authored after all five reports were returned, identifying convergences, disagreements, and AI-specific additions across the streams. The synthesis prioritizes claims that survive multiple streams' scrutiny over claims unique to any single school of thought.

Verification gaps acknowledged by the agents:
- Some quote-attributions to Larson's books were verified against Goodreads/secondary review pages rather than print pages.
- Specific timestamps for Carmack/Lex Fridman and Blow/DevGAMM video segments are approximate.
- Specific Wayne and Muratori phrases (e.g., "encapsulation theater") that could not be verified to a primary source were not attributed as direct quotes.
