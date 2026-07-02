import json
from dataclasses import dataclass

DEV_RATE = 62.5
DESIGNER_RATE = 50.0


@dataclass
class Task:
    name: str
    hours: int
    rate: str  # "dev" | "designer"

    @property
    def cost(self) -> float:
        return round(self.hours * (DESIGNER_RATE if self.rate == "designer" else DEV_RATE), 2)


@dataclass
class CanonicalExample:
    title: str
    client: str
    features: str
    tasks: list[Task]
    duration: str
    team: list[str]

    @property
    def total_hours(self) -> int:
        return sum(t.hours for t in self.tasks)

    @property
    def total_cost(self) -> float:
        return round(sum(t.cost for t in self.tasks), 2)

    @property
    def estimation_markdown(self) -> str:
        return _format_markdown(self)


# ── Canonical examples (single source of truth) ────────────────────────────────
# Invariant enforced by tests: sum(task.hours) == total_hours, sum(task.cost) == total_cost

CANONICAL_EXAMPLES: list[CanonicalExample] = [
    CanonicalExample(
        title="Landing page corporativa",
        client="Consultora B2B de transformación digital",
        features="web de 5 secciones, blog, formulario de contacto, multiidioma ES/EN",
        tasks=[
            Task("Diseño UX/UI + prototipo Figma", 8, "designer"),       # 8 × 50   = 400
            Task("Maquetación HTML/CSS responsive", 12, "dev"),           # 12 × 62.5 = 750
            Task("Desarrollo frontend (Next.js)", 20, "dev"),             # 20 × 62.5 = 1,250
            Task("CMS headless (Contentful)", 10, "dev"),                 # 10 × 62.5 = 625
            Task("Internacionalización i18n", 6, "dev"),                  # 6 × 62.5 = 375
            Task("Formulario de contacto + alertas email", 4, "dev"),     # 4 × 62.5 = 250
            Task("SEO on-page y meta tags", 4, "dev"),                    # 4 × 62.5 = 250
            Task("Testing cross-browser + despliegue", 6, "dev"),         # 6 × 62.5 = 375
        ],                                                                 # total = 70h / 4,275 €
        duration="4 semanas",
        team=["Frontend developer (1)", "Designer (1)"],
    ),
    CanonicalExample(
        title="App móvil e-commerce",
        client="Startup de moda sostenible",
        features="catálogo, carrito, pagos Stripe, perfil de usuario, push notifications, panel de administración web",
        tasks=[
            Task("Discovery y arquitectura técnica", 16, "dev"),              # 16 × 62.5 = 1,000
            Task("Diseño UX (flujos, wireframes)", 20, "designer"),           # 20 × 50   = 1,000
            Task("Diseño UI (sistema de diseño)", 24, "designer"),            # 24 × 50   = 1,200
            Task("Backend API REST (Node.js + PostgreSQL)", 80, "dev"),       # 80 × 62.5 = 5,000
            Task("App móvil React Native (iOS + Android)", 120, "dev"),       # 120 × 62.5= 7,500
            Task("Integración Stripe", 16, "dev"),                            # 16 × 62.5 = 1,000
            Task("Push notifications (Firebase)", 10, "dev"),                 # 10 × 62.5 = 625
            Task("Panel de administración web", 40, "dev"),                   # 40 × 62.5 = 2,500
            Task("QA y testing", 24, "dev"),                                  # 24 × 62.5 = 1,500
            Task("Despliegue + CI/CD", 16, "dev"),                            # 16 × 62.5 = 1,000
        ],                                                                     # total = 366h / 22,325 €
        duration="4–5 meses",
        team=["Backend developer (1)", "Mobile developer (1)", "Designer (1)", "QA engineer (0.5)"],
    ),
    CanonicalExample(
        title="Dashboard analítico interno",
        client="Empresa logística",
        features="KPIs en tiempo real, filtros por fecha/región/transportista, exportación Excel, autenticación con roles",
        tasks=[
            Task("Análisis de requisitos y fuentes de datos", 8, "dev"),   # 8 × 62.5 = 500
            Task("Diseño del modelo de datos", 8, "dev"),                   # 8 × 62.5 = 500
            Task("Backend + ETL (Python/FastAPI)", 32, "dev"),              # 32 × 62.5 = 2,000
            Task("Frontend dashboard (React + Recharts)", 40, "dev"),       # 40 × 62.5 = 2,500
            Task("Autenticación SSO + roles", 12, "dev"),                   # 12 × 62.5 = 750
            Task("Exportación Excel/CSV", 8, "dev"),                        # 8 × 62.5 = 500
            Task("Testing + documentación técnica", 8, "dev"),              # 8 × 62.5 = 500
        ],                                                                   # total = 116h / 7,250 €
        duration="6–8 semanas",
        team=["Full-stack developer (1)", "Data engineer (0.5)"],
    ),
]


# ── Public API ─────────────────────────────────────────────────────────────────

def select_examples(n: int) -> list[CanonicalExample]:
    return CANONICAL_EXAMPLES[:n]


def format_examples_for_prompt(examples: list[CanonicalExample], fmt: str) -> str:
    if not examples:
        return ""
    if fmt == "json":
        bodies = [_format_json(e) for e in examples]
    elif fmt == "narrative":
        bodies = [_format_narrative(e) for e in examples]
    else:
        bodies = [e.estimation_markdown for e in examples]
    return "## Reference Estimations\n\n" + "\n\n---\n\n".join(bodies)


# ── Formatters (private) ───────────────────────────────────────────────────────

def _format_markdown(example: CanonicalExample) -> str:
    rows = "\n".join(
        f"| {t.name} | {t.hours}h | {t.cost:,.2f} € |" for t in example.tasks
    )
    return (
        f"### {example.title}\n"
        f"**Client:** {example.client}  \n"
        f"**Features:** {example.features}\n\n"
        f"| Task | Hours | Cost |\n"
        f"|------|-------|------|\n"
        f"{rows}\n"
        f"| **Total** | **{example.total_hours}h** | **{example.total_cost:,.2f} €** |\n\n"
        f"**Total hours:** {example.total_hours}h  \n"
        f"**Total cost:** {example.total_cost:,.2f} €\n\n"
        f"**Recommended Team:** {', '.join(example.team)}\n\n"
        f"**Duration:** {example.duration}"
    )


def _format_json(example: CanonicalExample) -> str:
    data = {
        "title": example.title,
        "client": example.client,
        "features": example.features,
        "tasks": [
            {"name": t.name, "hours": t.hours, "rate": t.rate, "cost": t.cost}
            for t in example.tasks
        ],
        "total_hours": example.total_hours,
        "total_cost": example.total_cost,
        "team": example.team,
        "duration": example.duration,
    }
    return f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"


def _format_narrative(example: CanonicalExample) -> str:
    task_list = ", ".join(t.name for t in example.tasks[:-1])
    last_task = example.tasks[-1].name
    return (
        f"**{example.title}** ({example.client}).\n"
        f"Scope: {example.features}.\n"
        f"The project required {example.total_hours}h of work "
        f"({example.total_cost:,.2f} €), covering {task_list} and {last_task}. "
        f"Timeline: {example.duration}. "
        f"Team: {', '.join(example.team)}."
    )
