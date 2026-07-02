import logging
import time

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import Settings
from app.context.examples import format_examples_for_prompt, select_examples
from app.schemas.estimation import GenerationOptions, PreprocessingMode

logger = logging.getLogger(__name__)

# ── Output prompt constants ────────────────────────────────────────────────────

PROMPT_OUTPUT_BASIC = "Generate an estimation for the project described above."

PROMPT_OUTPUT_STRUCTURED = """\
Generate the estimation following EXACTLY this structure (do not add, remove, or rename sections):

## [Project Name]

[One paragraph describing the project scope and main features.]

| Task | Hours | Cost |
|------|-------|------|
| [Task name] | [N]h | [X,XXX.XX] € |
| [Task name] | [N]h | [X,XXX.XX] € |
| **Total** | **[N]h** | **[X,XXX.XX] €** |

**Total hours:** [N]h
**Total cost:** [X,XXX.XX] €

### Recommended Team
- [Role]: [brief note]

### Duration
[N]–[N] weeks

Rules:
- Every task row must have a specific, concrete name (no "Miscellaneous")
- The sum of task hours MUST equal the Total hours declared (arithmetic must be correct)
- The sum of task costs MUST equal the Total cost declared
- If scope is ambiguous, add a note after Duration with assumptions and a range\
"""

ACTIVE_OUTPUT_PROMPT = PROMPT_OUTPUT_STRUCTURED

# ── System prompt sections ─────────────────────────────────────────────────────

_ROL = """\
You are a senior software consultant with 15+ years of experience estimating web, mobile, and \
data projects. Your estimations are realistic, well-structured, and grounded in actual market rates.\
"""

_INLINE_CLEANING = """\
Before estimating, preprocess the transcription:
- Ignore informal conversation, greetings, and off-topic discussion
- Extract implicit requirements (things assumed but not explicitly stated)
- Resolve contradictions by preferring the most recent or most specific statement
- Focus only on functional scope and technical constraints\
"""

_TARIFAS = "Use a developer rate of 62.50 EUR/hour and a designer rate of 50.00 EUR/hour."


def build_system_prompt(opts: GenerationOptions) -> str:
    sections = [_ROL]

    if opts.preprocessing == PreprocessingMode.inline_cleaning:
        sections.append(_INLINE_CLEANING)

    sections.append(_TARIFAS)
    sections.append(ACTIVE_OUTPUT_PROMPT)

    if opts.num_examples > 0:
        examples = select_examples(opts.num_examples)
        sections.append(format_examples_for_prompt(examples, opts.example_format))

    return "\n\n".join(sections)


# ── Main entry point ───────────────────────────────────────────────────────────

async def generate_estimation(opts: GenerationOptions, settings: Settings) -> dict:
    pre_input = pre_output = 0
    extracted_requirements = None

    if opts.preprocessing == PreprocessingMode.two_phase:
        pre = await _extract_requirements(opts.transcription, opts, settings)
        effective_transcription = pre["text"]
        extracted_requirements = pre["text"]
        pre_input = pre["input_tokens"]
        pre_output = pre["output_tokens"]
    else:
        effective_transcription = opts.transcription

    system = build_system_prompt(opts)
    user = f"Meeting transcription:\n\n{effective_transcription}"

    t0 = time.monotonic()
    if settings.llm_provider == "anthropic":
        result = await _call_anthropic(
            system, user, opts.model, settings.anthropic_api_key,
            opts.max_tokens, opts.thinking_budget,
        )
    else:
        result = await _call_openai(
            system, user, opts.model, settings.openai_api_key,
            opts.max_tokens, opts.thinking_budget,
        )

    result["preprocessing"] = opts.preprocessing.value
    result["extracted_requirements"] = extracted_requirements
    result["latency_ms"] = int((time.monotonic() - t0) * 1000)
    result["usage"]["preprocessing_input_tokens"] = pre_input
    result["usage"]["preprocessing_output_tokens"] = pre_output

    return result


# ── Preprocessing ──────────────────────────────────────────────────────────────

async def _extract_requirements(
    transcription: str, opts: GenerationOptions, settings: Settings
) -> dict:
    system = (
        "You are an analyst. Read the transcription and produce a clean, structured list of: "
        "functional requirements, non-functional requirements, integrations, and constraints. "
        "Be concise. Use bullet points."
    )
    user = f"Transcription:\n\n{transcription}"

    if settings.llm_provider == "anthropic":
        raw = await _call_anthropic(system, user, opts.model, settings.anthropic_api_key, max_tokens=1024)
    else:
        raw = await _call_openai(system, user, opts.model, settings.openai_api_key, max_tokens=1024)

    return {
        "text": raw["estimation"],
        "input_tokens": raw["usage"]["input_tokens"],
        "output_tokens": raw["usage"]["output_tokens"],
    }


# ── Provider wrappers ──────────────────────────────────────────────────────────

async def _call_openai(
    system: str,
    user: str,
    model: str,
    api_key: str,
    max_tokens: int = 4000,
    thinking_budget: int | None = None,
) -> dict:
    if thinking_budget is not None:
        logger.warning("thinking_budget is Anthropic-only and will be ignored for OpenAI provider")

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return {
        "estimation": resp.choices[0].message.content,
        "model": resp.model,
        "provider": "openai",
        "finish_reason": resp.choices[0].finish_reason,
        "usage": {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        },
    }


async def _call_anthropic(
    system: str,
    user: str,
    model: str,
    api_key: str,
    max_tokens: int = 4000,
    thinking_budget: int | None = None,
) -> dict:
    client = AsyncAnthropic(api_key=api_key)

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    if thinking_budget is not None:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        # auto-pad: max_tokens must exceed the thinking budget
        kwargs["max_tokens"] = max(max_tokens, thinking_budget + 1024)

    resp = await client.messages.create(**kwargs)

    # Skip thinking blocks; return only the first text block
    text = next(b.text for b in resp.content if b.type == "text")

    return {
        "estimation": text,
        "model": resp.model,
        "provider": "anthropic",
        "finish_reason": resp.stop_reason,
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
        },
    }
