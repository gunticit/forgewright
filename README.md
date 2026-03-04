# Production Grade Plugin for Claude Code

**Fully autonomous production-grade SaaS pipeline.** One install gives you 13 bundled skills covering the entire software lifecycle. You sit in the CEO/CTO seat -- Claude handles everything from requirements to production deployment.

## No Prerequisites

Unlike v1.0, **no separate skill installations are needed**. All 13 skills are bundled. Just install and go.

## Installation

### Via Marketplace
```
/plugin marketplace add nagisanzenin/claude-code-plugins
/plugin install production-grade@nagisanzenin
```

### Load Directly
```
claude --plugin-dir /path/to/production-grade-plugin
```

## The Pipeline

```
DEFINE          BUILD              HARDEN             SHIP            SUSTAIN
  |               |                  |                  |               |
  v               v                  v                  v               v
Product       Software           QA Engineer        DevOps            SRE
Manager       Engineer           Security Eng       (CI/CD,IaC)      (Reliability)
(BRD/PRD)     (Services)         Code Reviewer
              Frontend Eng
Solution      (UI/UX)
Architect     Data Scientist
(Design)      (AI/ML)            Technical Writer
                                 (Docs)
```

**DEFINE** -- Product Manager interviews stakeholders, writes BRD/PRD. Solution Architect designs the system, API contracts, data models, and scaffolds the project.

**BUILD** -- Software Engineer implements backend services with clean architecture. Frontend Engineer builds the UI with design systems and accessibility. Data Scientist handles AI/ML/LLM optimization.

**HARDEN** -- QA Engineer writes comprehensive test suites (unit, integration, e2e, performance). Security Engineer runs STRIDE threat modeling and OWASP audits. Code Reviewer enforces architecture conformance and quality.

**SHIP** -- DevOps builds Terraform IaC, CI/CD pipelines, Docker/Kubernetes configs, monitoring, and security scanning.

**SUSTAIN** -- SRE ensures production readiness with chaos engineering, capacity planning, and incident management. Technical Writer generates API references, dev guides, and operational docs.

## Workspace Structure

All output is organized under a single workspace:

```
Claude-Production-Grade-Suite/
├── 00-business/
│   ├── BRD.md
│   ├── PRD.md
│   └── stakeholder-interviews/
├── 01-architecture/
│   ├── docs/ (ADRs, diagrams, tech stack)
│   ├── api/ (OpenAPI, gRPC, AsyncAPI)
│   ├── schemas/ (ERD, migrations)
│   └── scaffold/ (project structure)
├── 02-implementation/
│   ├── backend/ (services, clean architecture)
│   ├── frontend/ (design system, components, pages)
│   └── ai-ml/ (models, prompts, experiments)
├── 03-quality/
│   ├── tests/ (unit, integration, e2e, perf)
│   ├── security/ (threat model, OWASP, pen test)
│   └── reviews/ (architecture conformance)
├── 04-infrastructure/
│   ├── terraform/
│   ├── ci-cd/
│   ├── containers/
│   ├── monitoring/
│   └── security/
├── 05-operations/
│   ├── sre/ (runbooks, chaos, capacity)
│   └── docs/ (API ref, dev guides, ops docs)
└── ORCHESTRATOR-STATE.md
```

## Bundled Skills (13)

| # | Skill | Phase | Description |
|---|-------|-------|-------------|
| 1 | **production-grade** | Orchestrator | Master pipeline controller -- coordinates all skills end-to-end |
| 2 | **product-manager** | DEFINE | Stakeholder interviews, BRD/PRD, implementation verification |
| 3 | **solution-architect** | DEFINE | System design, tech stack, API contracts, data models, scaffolding |
| 4 | **software-engineer** | BUILD | Service implementation, clean architecture, payment integration, debugging |
| 5 | **frontend-engineer** | BUILD | Design system, components, pages, API clients, accessibility (Next.js/Vue/Svelte) |
| 6 | **data-scientist** | BUILD | AI/ML/LLM optimization, prompt engineering, token optimization, A/B testing |
| 7 | **qa-engineer** | HARDEN | Unit, integration, contract, e2e, performance tests with self-healing protocols |
| 8 | **security-engineer** | HARDEN | STRIDE threat modeling, OWASP audit, pen test planning, compliance |
| 9 | **code-reviewer** | HARDEN | Architecture conformance, code quality, security, performance review, auto-fix |
| 10 | **devops** | SHIP | Terraform IaC, CI/CD, Docker/K8s, monitoring, security scanning |
| 11 | **sre** | SUSTAIN | Production readiness, chaos engineering, capacity planning, incident management |
| 12 | **technical-writer** | SUSTAIN | API reference, dev guides, operational docs, Docusaurus site scaffold |
| 13 | **skill-maker** | Meta | Creates new Claude Code skills and plugins with marketplace publishing |

## Usage

Trigger with phrases like:
- "Build a production-grade SaaS for [idea]"
- "Full production pipeline for this project"
- "Production ready setup"
- "Run the complete pipeline"

The orchestrator will run all phases autonomously, producing a complete production-ready codebase.

## License

MIT
