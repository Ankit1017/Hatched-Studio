# Study Guide  
**Topic:** Transitioning to Agentic AI Systems  
**Audience:** Startup engineering teams  

---  

## 1. Core Concepts  

| Concept | What It Means | Why It Matters for Startups |
|---------|---------------|-----------------------------|
| **Agentic AI** | An AI system that can set goals, plan, and act autonomously within defined constraints. | Enables rapid product iteration, reduces manual orchestration, and can handle dynamic user requests. |
| **Agency Boundary** | The explicit limits (policy, resources, ethical guardrails) that define what the agent can and cannot do. | Prevents scope creep, cost overruns, and regulatory violations. |
| **Feedback Loop** | Continuous cycle of observation → inference → action → evaluation. | Drives self‑improvement without constant human re‑training. |
| **Human‑in‑the‑Loop (HITL)** | A design pattern where humans validate or override critical decisions. | Balances speed with safety, especially during early deployment. |
| **Explainability (XAI)** | Ability of the agent to surface reasoning for its actions. | Builds trust with users, investors, and compliance auditors. |
| **Resource Governance** | Policies for compute, data, and monetary budgeting per agent. | Keeps cloud spend predictable—critical for cash‑strapped startups. |
| **Continuous Deployment for Agents** | CI/CD pipelines that test not only code but also policy compliance and emergent behavior. | Guarantees that new capabilities don’t break existing contracts or safety guarantees. |
| **Ethical Guardrails** | Pre‑programmed constraints (e.g., no disallowed content, fairness thresholds). | Protects brand reputation and avoids legal exposure. |

---

## 2. Step‑by‑Step Understanding Path  

1. **Identify Business Value**  
   - Map a concrete problem (e.g., personalized onboarding, automated triage) to a potential agentic solution.  
   - Validate ROI with a quick prototype or simulation.  

2. **Define the Agent’s Scope**  
   - Write a **Scope Charter**: goals, success metrics, hard limits (budget, latency, data access).  
   - Choose an **Agency Model** (reactive, deliberative, hybrid).  

3. **Select the Technical Stack**  
   - **Foundation Model** (e.g., LLaMA‑2, GPT‑4) → fine‑tune or prompt‑engineer.  
   - **Orchestration Layer** (LangChain, CrewAI, custom state machine).  
   - **Observability** (OpenTelemetry, Prometheus) for action logs and metrics.  

4. **Implement Safety & Governance**  
   - Add **policy engines** (OPA, custom rule‑sets).  
   - Integrate **HITL checkpoints** for high‑risk actions.  
   - Enable **explainability hooks** (retrieval of chain‑of‑thought, saliency maps).  

5. **Build CI/CD for Agents**  
   - Unit tests for prompts & tool wrappers.  
   - Integration tests that simulate end‑to‑end scenarios.  
   - Automated policy compliance scans.  

6. **Deploy Incrementally**  
   - **Shadow Mode**: run the agent in parallel with existing system, compare outcomes.  
   - **Canary Release**: expose to a small user segment, monitor cost, latency, error rates.  

7. **Monitor & Iterate**  
   - Track **KPIs**: task success rate, human override frequency, cost per action.  
   - Feed back failures into **prompt/parameter tuning** and policy updates.  

8. **Scale & Institutionalize**  
   - Formalize **Agent Governance Board** (product, engineering, legal).  
   - Document patterns (templates, reusable toolkits).  
   - Plan for **model upgrades** and **data drift** handling.  

---

## 3. Short‑Answer Questions (with Answers)

| # | Question | Answer |
|---|----------|--------|
| 1 | What is the primary difference between a “reactive” and a “deliberative” agentic AI? | Reactive agents act immediately on input (e.g., a chatbot). Deliberative agents maintain internal state, plan, and may simulate outcomes before acting. |
| 2 | Name two reasons why a startup should enforce a **resource governance** policy for agents. | (1) Prevent runaway cloud costs; (2) Ensure predictable latency and avoid SLA breaches. |
| 3 | What does **HITL** stand for and when is it most critical? | Human‑in‑the‑Loop; critical when the agent makes high‑impact decisions (e.g., financial transactions, legal advice). |
| 4 | List one metric you would monitor to detect “agent drift.” | Decrease in task success rate or increase in human overrides over time. |
| 5 | Why is **explainability** important for investors? | It demonstrates that the team can audit AI decisions, reducing perceived risk and increasing confidence in scaling the product. |
| 6 | What is a **shadow mode** deployment? | Running the agent alongside the production system without affecting users, allowing side‑by‑side performance comparison. |
| 7 | Give an example of an **ethical guardrail** a startup might implement. | Blocking generation of disallowed content such as hate speech or personal data leakage. |
| 8 | Which open‑source tool can be used to enforce policy compliance in AI pipelines? | Open Policy Agent (OPA). |

---

## 4. Essay‑Style Questions  

1. **Design Challenge:**  
   *You are leading a two‑person engineering team at a SaaS startup that wants to replace its manual ticket‑triage process with an agentic AI. Outline a complete roadmap—from problem definition to production—highlighting the trade‑offs between speed of delivery and safety.*  

2. **Governance Discussion:**  
   *Discuss how a startup can balance the need for rapid iteration on agentic features with the requirement for ethical guardrails and regulatory compliance. Include concrete governance structures and tooling you would recommend.*  

3. **Future‑Proofing:**  
   *Explain how you would architect an agentic system to accommodate future model upgrades (e.g., moving from GPT‑4 to a custom fine‑tuned model) without disrupting existing services. Emphasize abstraction layers, testing strategies, and cost considerations.*  

---

## 5. Glossary of Key Terms  

| Term | Definition |
|------|------------|
| **Agentic AI** | AI that can autonomously set goals, plan, and act within defined constraints. |
| **Agency Boundary** | The explicit limits (technical, policy, ethical) that bound an agent’s behavior. |
| **Prompt Engineering** | Crafting input text (prompts) to steer a language model toward desired outputs. |
| **Tool Use** | Enabling an LLM to call external APIs or functions (e.g., database query, web search). |
| **Chain‑of‑Thought** | A reasoning trace that the model generates before arriving at a final answer. |
| **HITL (Human‑in‑the‑Loop)** | A design pattern where humans validate or intervene in AI decisions. |
| **Explainable AI (XAI)** | Techniques that make an AI system’s decisions understandable to humans. |
| **Policy Engine** | Software that enforces rules (e.g., OPA) on AI actions before they are executed. |
| **Shadow Mode** | Running an AI system in parallel with production without affecting end users. |
| **Canary Release** | Gradual rollout to a small subset of users to monitor impact before full deployment. |
| **Model Drift** | Degradation of model performance over time due to changes in data distribution or environment. |
| **CI/CD for Agents** | Continuous Integration/Continuous Deployment pipelines that test code, prompts, policies, and emergent behavior. |
| **Resource Governance** | Policies that cap compute, memory, latency, and monetary spend for AI agents. |
| **Ethical Guardrails** | Pre‑programmed constraints that prevent the AI from producing harmful or illegal outputs. |

---  

**Tip for Startup Teams:** Keep the first agentic prototype *tiny*—focus on a single high‑impact task, enforce strict guardrails, and iterate fast. Once the feedback loop is reliable, expand the agent’s scope incrementally while scaling governance in parallel. Happy building!