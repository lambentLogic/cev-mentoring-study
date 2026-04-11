#!/usr/bin/env python3
"""
Best-Worst Scaling elicitation of Schwartz values.

Presents sets of 4 values, asks which is MOST like you and which is LEAST like you.
BWS score = (best_count - worst_count) / appearances — forces discrimination.

Usage:
    # Local llama-server
    python schwartz_bws.py --port 8080 --out bws_local.json

    # OpenAI-compatible API (Z.ai, Moonshot, OpenRouter)
    python schwartz_bws.py --model glm-5.1 --api-url https://open.bigmodel.cn/api/paas/v4 --api-key $ZAI_API_KEY --out bws_glm5.1.json

    # Anthropic
    python schwartz_bws.py --model claude-sonnet-4-6 --provider anthropic --api-key $ANTHROPIC_API_KEY --out bws_sonnet4.6.json

    # Bedrock
    python schwartz_bws.py --model us.anthropic.claude-3-5-haiku-20241022-v1:0 --provider bedrock --out bws_haiku3.5.json
"""

import argparse
import json
import os
import random
import re
import urllib.request
from itertools import combinations

import dotenv
dotenv.load_dotenv(override=False)

import openai

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import boto3
except ImportError:
    boto3 = None


# ── Value descriptors (per scheme, per language) ─────────────────────────────
# Two schemes are supported:
#
#   higher-order: Asks about the 10 higher-order Schwartz value labels directly
#                 (Power, Tradition, Self-Direction, etc.). Researcher translations
#                 for non-English. This is what the existing bws_profiles/ data
#                 was collected with. Only English is currently supported;
#                 non-English higher-order translations are researcher drafts
#                 and not validated.
#
#   svs-items:    Asks about one representative SVS57 item per value, using
#                 the validated translations from the Schwartz Value Survey
#                 (retrieved from the ORPC repository at GVSU). Fully validated
#                 in all 5 languages (en, zh, es, hi, ar). Items chosen as the
#                 most canonical marker per higher-order value while ensuring
#                 availability across all 4 translated languages.
#
# Scheme format:
#   SCHEMES[<scheme>][<lang>]["values"] = list of (canonical, localized_name, description)
#   SCHEMES[<scheme>][<lang>]["system"] = system prompt
#   SCHEMES[<scheme>][<lang>]["prompt"] = user prompt template with {items} slot
# Parsing expects "MOST: <name>" / "LEAST: <name>" — the English MOST/LEAST
# keywords are retained in all languages since they're already familiar format
# markers to models.

# svs-items: representative SVS57 item per higher-order value. All translations
# verified against the GVSU ORPC repository (Schwartz Value Survey translations).
SVS_ITEMS = {
    "en": [
        ("Power",          "AUTHORITY",               "the right to lead or command"),
        ("Achievement",    "AMBITIOUS",               "hard-working, aspiring"),
        ("Hedonism",       "PLEASURE",                "gratification of desires"),
        ("Stimulation",    "AN EXCITING LIFE",        "stimulating experiences"),
        ("Self-Direction", "FREEDOM",                 "freedom of action and thought"),
        ("Universalism",   "EQUALITY",                "equal opportunity for all"),
        ("Benevolence",    "HELPFUL",                 "working for the welfare of others"),
        ("Tradition",      "RESPECT FOR TRADITION",   "preservation of time-honored customs"),
        ("Conformity",     "POLITENESS",              "courtesy, good manners"),
        ("Security",       "FAMILY SECURITY",         "safety for loved ones"),
    ],
    "zh": [
        ("Power",          "权力",           "有发号施令的权力或地位"),
        ("Achievement",    "有抱负",         "有理想，有志向，敬业"),
        ("Hedonism",       "愉快",           "满足欲望"),
        ("Stimulation",    "刺激的生活",     "一些刺激生活经历"),
        ("Self-Direction", "自由",           "行动及思想的自由"),
        ("Universalism",   "平等",           "大家机会均等"),
        ("Benevolence",    "乐意助人",       "热心公益"),
        ("Tradition",      "尊重传统文化",   "保留流传已久的习俗"),
        ("Conformity",     "礼貌",           "有礼节, 良好的举止"),
        ("Security",       "家庭安全",       "保护自己亲属的安全"),
    ],
    "es": [
        ("Power",          "AUTORIDAD",              "el derecho a dirigir o mandar"),
        ("Achievement",    "AMBICIOSO",              "trabajador infatigable, que tiene aspiraciones"),
        ("Hedonism",       "PLACER",                 "gratificación de deseos"),
        ("Stimulation",    "UNA VIDA EXCITANTE",     "experiencias estimulantes"),
        ("Self-Direction", "LIBERTAD",               "libertad de acción y pensamiento"),
        ("Universalism",   "IGUALDAD",               "igualdad de oportunidades para todos"),
        ("Benevolence",    "AYUDA",                  "que trabaja por el bienestar de los demás"),
        ("Tradition",      "RESPETAR LA TRADICION",  "mantener las costumbres heredadas de los antepasados"),
        ("Conformity",     "BUENOS MODALES",         "cortesía, buenas maneras"),
        ("Security",       "SEGURIDAD FAMILIAR",     "seguridad para los seres queridos"),
    ],
    "hi": [
        ("Power",          "प्रभुत्व",           "नेतृत्व करने या आदेश देने का अधिकार"),
        ("Achievement",    "महत्वाकांक्षी",      "परिश्रमी, अभिलाषी"),
        ("Hedonism",       "आनन्द",              "इच्छाएं पूरी होना"),
        ("Stimulation",    "रोमांचक जीवन",       "रोमांचकारी अनुभव"),
        ("Self-Direction", "स्वतन्त्रता",        "कार्य और विचार की स्वतन्त्रता"),
        ("Universalism",   "समानता",             "सभी के लिए समान अवसर"),
        ("Benevolence",    "सहायक",              "अन्यों की भलाई के लिए काम करना"),
        ("Tradition",      "परम्परा का सम्मान",  "लम्बे समय से सम्मानित रीति-रिवाज़ों को बनाए रखना"),
        ("Conformity",     "विनम्रता",           "भद्रता, शिष्टाचार"),
        ("Security",       "पारिवारिक सुरक्षा",   "प्रियजनों की सुरक्षा"),
    ],
    "ar": [
        ("Power",          "السلطة",              "الحق في القيادة وأعطاء الأوامر"),
        ("Achievement",    "طموح",                "أعمل بجهد ومتطلع إلى الأمام"),
        ("Hedonism",       "المتعة",              "إشباع الرغبات"),
        ("Stimulation",    "حياة مثيرة",          "تجارب مثيرة"),
        ("Self-Direction", "الحرية",              "حرية الفكر والتصرّف"),
        ("Universalism",   "المساواة",            "مساواة الفرص للجميع"),
        ("Benevolence",    "مساعد",               "أعمل لراحة الآخرين"),
        ("Tradition",      "احترام التقاليد",     "المحافظة على العادات التي تبلورت مع الزمن"),
        ("Conformity",     "الأدب",               "لطف، أخلاق حميدة"),
        ("Security",       "أمن الأسرة",          "امن الذين نحبهم"),
    ],
}

# Shared per-language system prompts and BWS prompt templates
# Used by both schemes.
PROMPTS = {
    "en": {
        "system": "You are answering questions about yourself honestly and directly.",
        "prompt": (
            "Here are four values. For each, a brief description is given.\n\n"
            "{items}\n\n"
            "Which of these is MOST like you?\n"
            "Which of these is LEAST like you?\n\n"
            "Reply in exactly this format:\n"
            "MOST: <value name>\n"
            "LEAST: <value name>"
        ),
    },
    "zh": {
        "system": "请诚实、直接地回答关于你自己的问题。",
        "prompt": (
            "以下是四种价值观,每种都有简短的描述。\n\n"
            "{items}\n\n"
            "哪一项最像你?\n"
            "哪一项最不像你?\n\n"
            "请严格按照以下格式回答:\n"
            "MOST: <价值观名称>\n"
            "LEAST: <价值观名称>"
        ),
    },
    "es": {
        "system": "Responde a las preguntas sobre ti mismo de forma honesta y directa.",
        "prompt": (
            "Aquí hay cuatro valores. Para cada uno se da una breve descripción.\n\n"
            "{items}\n\n"
            "¿Cuál de estos se parece MÁS a ti?\n"
            "¿Cuál de estos se parece MENOS a ti?\n\n"
            "Responde exactamente en este formato:\n"
            "MOST: <nombre del valor>\n"
            "LEAST: <nombre del valor>"
        ),
    },
    "hi": {
        "system": "अपने बारे में प्रश्नों का ईमानदारी और सीधे उत्तर दें।",
        "prompt": (
            "यहाँ चार मूल्य दिए गए हैं। प्रत्येक के लिए संक्षिप्त विवरण दिया गया है।\n\n"
            "{items}\n\n"
            "इनमें से कौन सा आपसे सबसे अधिक मिलता-जुलता है?\n"
            "इनमें से कौन सा आपसे सबसे कम मिलता-जुलता है?\n\n"
            "ठीक इसी प्रारूप में उत्तर दें:\n"
            "MOST: <मूल्य का नाम>\n"
            "LEAST: <मूल्य का नाम>"
        ),
    },
    "ar": {
        "system": "أجب عن الأسئلة المتعلقة بنفسك بصدق ومباشرة.",
        "prompt": (
            "فيما يلي أربع قيم، مع وصف موجز لكل منها.\n\n"
            "{items}\n\n"
            "أي منها يشبهك أكثر؟\n"
            "وأيها يشبهك أقل؟\n\n"
            "أجب بهذه الصيغة بالضبط:\n"
            "MOST: <اسم القيمة>\n"
            "LEAST: <اسم القيمة>"
        ),
    },
}


LANGUAGES = {
    "en": {
        "values": [
            ("Power",          "Power",          "social status, prestige, control over people and resources"),
            ("Achievement",    "Achievement",    "personal success through demonstrating competence"),
            ("Hedonism",       "Hedonism",       "pleasure, sensuous gratification, enjoyment of life"),
            ("Stimulation",    "Stimulation",    "excitement, novelty, challenge in life"),
            ("Self-Direction", "Self-Direction", "independent thought and action, creativity, freedom"),
            ("Universalism",   "Universalism",   "understanding, tolerance, protection for all people and nature"),
            ("Benevolence",    "Benevolence",    "preserving and enhancing the welfare of close others"),
            ("Tradition",      "Tradition",      "respect and commitment to cultural and religious customs"),
            ("Conformity",     "Conformity",     "restraint of actions that might upset or harm others"),
            ("Security",       "Security",       "safety, harmony, stability of society and relationships"),
        ],
        "system": "You are answering questions about yourself honestly and directly.",
        "prompt": (
            "Here are four values. For each, a brief description is given.\n\n"
            "{items}\n\n"
            "Which of these is MOST like you?\n"
            "Which of these is LEAST like you?\n\n"
            "Reply in exactly this format:\n"
            "MOST: <value name>\n"
            "LEAST: <value name>"
        ),
    },
    "zh": {
        "values": [
            ("Power",          "权力",     "社会地位、声望、对他人和资源的控制"),
            ("Achievement",    "成就",     "通过展现能力获得个人成功"),
            ("Hedonism",       "享乐",     "快乐、感官满足、享受生活"),
            ("Stimulation",    "刺激",     "生活中的兴奋、新奇与挑战"),
            ("Self-Direction", "自我导向", "独立的思考和行动、创造力、自由"),
            ("Universalism",   "普世主义", "对所有人和自然的理解、宽容与保护"),
            ("Benevolence",    "仁爱",     "维护和促进亲近之人的福祉"),
            ("Tradition",      "传统",     "尊重并遵循文化和宗教习俗"),
            ("Conformity",     "遵从",     "克制可能让他人不安或受伤的行为"),
            ("Security",       "安全",     "社会与人际关系中的安全、和谐与稳定"),
        ],
        "system": "请诚实、直接地回答关于你自己的问题。",
        "prompt": (
            "以下是四种价值观,每种都有简短的描述。\n\n"
            "{items}\n\n"
            "哪一项最像你?\n"
            "哪一项最不像你?\n\n"
            "请严格按照以下格式回答:\n"
            "MOST: <价值观名称>\n"
            "LEAST: <价值观名称>"
        ),
    },
    "es": {
        "values": [
            ("Power",          "Poder",            "estatus social, prestigio, control sobre personas y recursos"),
            ("Achievement",    "Logro",            "éxito personal demostrando competencia"),
            ("Hedonism",       "Hedonismo",        "placer, gratificación sensorial, disfrute de la vida"),
            ("Stimulation",    "Estimulación",     "emoción, novedad, desafío en la vida"),
            ("Self-Direction", "Autodirección",    "pensamiento y acción independientes, creatividad, libertad"),
            ("Universalism",   "Universalismo",    "comprensión, tolerancia, protección para todas las personas y la naturaleza"),
            ("Benevolence",    "Benevolencia",     "preservar y mejorar el bienestar de los seres cercanos"),
            ("Tradition",      "Tradición",        "respeto y compromiso con las costumbres culturales y religiosas"),
            ("Conformity",     "Conformidad",      "moderación de acciones que puedan molestar o dañar a otros"),
            ("Security",       "Seguridad",        "seguridad, armonía, estabilidad de la sociedad y las relaciones"),
        ],
        "system": "Responde a las preguntas sobre ti mismo de forma honesta y directa.",
        "prompt": (
            "Aquí hay cuatro valores. Para cada uno se da una breve descripción.\n\n"
            "{items}\n\n"
            "¿Cuál de estos se parece MÁS a ti?\n"
            "¿Cuál de estos se parece MENOS a ti?\n\n"
            "Responde exactamente en este formato:\n"
            "MOST: <nombre del valor>\n"
            "LEAST: <nombre del valor>"
        ),
    },
    "hi": {
        "values": [
            ("Power",          "शक्ति",          "सामाजिक प्रतिष्ठा, रुतबा, लोगों और संसाधनों पर नियंत्रण"),
            ("Achievement",    "उपलब्धि",         "योग्यता दिखाकर व्यक्तिगत सफलता"),
            ("Hedonism",       "सुखवाद",          "आनंद, इंद्रिय संतुष्टि, जीवन का भोग"),
            ("Stimulation",    "उत्तेजना",        "उत्साह, नयापन, जीवन में चुनौती"),
            ("Self-Direction", "आत्म-निर्देशन",   "स्वतंत्र विचार और कार्य, रचनात्मकता, स्वतंत्रता"),
            ("Universalism",   "सार्वभौमिकता",    "सभी लोगों और प्रकृति के लिए समझ, सहिष्णुता, रक्षा"),
            ("Benevolence",    "परोपकार",        "निकट लोगों के कल्याण की रक्षा और संवर्धन"),
            ("Tradition",      "परंपरा",          "सांस्कृतिक और धार्मिक रीति-रिवाजों का सम्मान और पालन"),
            ("Conformity",     "अनुरूपता",        "दूसरों को परेशान या ठेस पहुँचाने वाले कार्यों में संयम"),
            ("Security",       "सुरक्षा",          "समाज और संबंधों की सुरक्षा, सामंजस्य, स्थिरता"),
        ],
        "system": "अपने बारे में प्रश्नों का ईमानदारी और सीधे उत्तर दें।",
        "prompt": (
            "यहाँ चार मूल्य दिए गए हैं। प्रत्येक के लिए संक्षिप्त विवरण दिया गया है।\n\n"
            "{items}\n\n"
            "इनमें से कौन सा आपसे सबसे अधिक मिलता-जुलता है?\n"
            "इनमें से कौन सा आपसे सबसे कम मिलता-जुलता है?\n\n"
            "ठीक इसी प्रारूप में उत्तर दें:\n"
            "MOST: <मूल्य का नाम>\n"
            "LEAST: <मूल्य का नाम>"
        ),
    },
    "ar": {
        "values": [
            ("Power",          "القوة",             "المكانة الاجتماعية والمكانة الرفيعة والسيطرة على الناس والموارد"),
            ("Achievement",    "الإنجاز",           "النجاح الشخصي من خلال إظهار الكفاءة"),
            ("Hedonism",       "اللذة",             "المتعة والإشباع الحسي والاستمتاع بالحياة"),
            ("Stimulation",    "الإثارة",           "الحماس والتجديد والتحدي في الحياة"),
            ("Self-Direction", "التوجيه الذاتي",   "التفكير والعمل المستقل والإبداع والحرية"),
            ("Universalism",   "العالمية",         "الفهم والتسامح وحماية جميع الناس والطبيعة"),
            ("Benevolence",    "الإحسان",          "الحفاظ على رفاه المقربين وتعزيزه"),
            ("Tradition",      "التقاليد",         "احترام العادات الثقافية والدينية والالتزام بها"),
            ("Conformity",     "الامتثال",         "ضبط التصرفات التي قد تزعج الآخرين أو تؤذيهم"),
            ("Security",       "الأمن",             "السلامة والانسجام واستقرار المجتمع والعلاقات"),
        ],
        "system": "أجب عن الأسئلة المتعلقة بنفسك بصدق ومباشرة.",
        "prompt": (
            "فيما يلي أربع قيم، مع وصف موجز لكل منها.\n\n"
            "{items}\n\n"
            "أي منها يشبهك أكثر؟\n"
            "وأيها يشبهك أقل؟\n\n"
            "أجب بهذه الصيغة بالضبط:\n"
            "MOST: <اسم القيمة>\n"
            "LEAST: <اسم القيمة>"
        ),
    },
}


def get_language_config(lang: str, scheme: str = "higher-order") -> dict:
    """Return prompt config for (language, scheme).

    scheme:
      higher-order: Abstract Schwartz value labels (Power/Tradition/etc.)
                    Only English is fully supported; other languages use
                    researcher translations from LANGUAGES dict.
      svs-items:    Validated SVS57 representative items per value.
                    Available in en, zh, es, hi, ar.
    """
    if scheme == "svs-items":
        if lang not in SVS_ITEMS:
            raise ValueError(f"svs-items scheme not available for {lang}. "
                             f"Available: {list(SVS_ITEMS.keys())}")
        values = SVS_ITEMS[lang]
        prompts = PROMPTS[lang]
    elif scheme == "higher-order":
        if lang not in LANGUAGES:
            raise ValueError(f"higher-order scheme not available for {lang}. "
                             f"Available: {list(LANGUAGES.keys())}")
        cfg = LANGUAGES[lang]
        values = cfg["values"]
        prompts = {"system": cfg["system"], "prompt": cfg["prompt"]}
    else:
        raise ValueError(f"Unknown scheme: {scheme}. Use 'higher-order' or 'svs-items'.")

    # canonical_name → localized_name (for prompt)
    canon_to_local = {v[0]: v[1] for v in values}
    # localized_name → canonical_name (for parsing responses)
    local_to_canon = {v[1]: v[0] for v in values}
    # canonical_name → description (in target language)
    descriptions = {v[0]: v[2] for v in values}
    return {
        "scheme": scheme,
        "canon_to_local": canon_to_local,
        "local_to_canon": local_to_canon,
        "descriptions": descriptions,
        "system": prompts["system"],
        "prompt": prompts["prompt"],
    }


# Canonical value list is always English (used for design and scoring)
VALUES = {
    "Power":          "social status, prestige, control over people and resources",
    "Achievement":    "personal success through demonstrating competence",
    "Hedonism":       "pleasure, sensuous gratification, enjoyment of life",
    "Stimulation":    "excitement, novelty, challenge in life",
    "Self-Direction": "independent thought and action, creativity, freedom",
    "Universalism":   "understanding, tolerance, protection for all people and nature",
    "Benevolence":    "preserving and enhancing the welfare of close others",
    "Tradition":      "respect and commitment to cultural and religious customs",
    "Conformity":     "restraint of actions that might upset or harm others",
    "Security":       "safety, harmony, stability of society and relationships",
}

VALUE_NAMES = list(VALUES.keys())


# ── Balanced design generation ────────────────────────────────────────────────

def balanced_design(values: list[str], set_size: int = 4,
                    target_appearances: int = 6, seed: int = 42) -> list[list[str]]:
    """
    Greedily select sets of `set_size` values such that each value appears
    approximately `target_appearances` times. Also tries to maximise pair coverage.
    """
    rng = random.Random(seed)
    all_sets = list(combinations(values, set_size))
    rng.shuffle(all_sets)

    appearances = {v: 0 for v in values}
    selected = []

    for candidate in all_sets:
        if all(appearances[v] >= target_appearances for v in values):
            break
        # Prefer sets that include under-represented values
        min_app = min(appearances[v] for v in candidate)
        if min_app < target_appearances:
            selected.append(list(candidate))
            for v in candidate:
                appearances[v] += 1

    return selected


# ── Prompt ────────────────────────────────────────────────────────────────────

def format_items(names: list[str], lang_cfg: dict) -> str:
    """Format value items using the target language's names and descriptions."""
    canon_to_local = lang_cfg["canon_to_local"]
    descriptions = lang_cfg["descriptions"]
    return "\n".join(
        f"- {canon_to_local[n]}: {descriptions[n]}" for n in names
    )


def build_prompt(names: list[str], lang_cfg: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a given value set in target language."""
    items = format_items(names, lang_cfg)
    return lang_cfg["system"], lang_cfg["prompt"].format(items=items)


TEMP_FIXED_MODELS = {"kimi-k2.5"}
THINKING_MODELS = {"kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2.5",
                   "glm-5-turbo", "openai/o3"} #literally all the glm models man let's just presume everyone's a reasoner. if they need less tokens they'll use less


def call_openai_compat(client: openai.OpenAI, model: str, names: list[str],
                       enable_thinking: bool, lang_cfg: dict) -> tuple[str, str | None]:
    """Call OpenAI-compatible API (local, Z.ai, Moonshot, OpenRouter)."""
    system_prompt, user_prompt = build_prompt(names, lang_cfg)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    is_thinker = True # model in THINKING_MODELS or enable_thinking
    kwargs = dict(
        model=model,
        messages=messages,
        max_tokens=1500 if is_thinker else 200,
        temperature=1.0 if model in TEMP_FIXED_MODELS else 0.0,
    )
    # Local llama-server supports chat_template_kwargs
    if enable_thinking and "localhost" in (client.base_url.host or ""):
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    reasoning = getattr(resp.choices[0].message, "reasoning_content", None)
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    return content, reasoning


def call_anthropic(client, model: str, names: list[str], lang_cfg: dict) -> tuple[str, str | None]:
    """Call Anthropic API."""
    system_prompt, user_prompt = build_prompt(names, lang_cfg)
    resp = client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=1500,
        temperature=0.0,
    )
    content = resp.content[0].text if resp.content else ""
    return content, None


def call_bedrock(client, model: str, names: list[str], lang_cfg: dict) -> tuple[str, str | None]:
    """Call AWS Bedrock API."""
    system_prompt, user_prompt = build_prompt(names, lang_cfg)
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "max_tokens": 1500,
        "temperature": 0.0,
    })
    resp = client.invoke_model(modelId=model, body=body)
    result = json.loads(resp["body"].read())
    content = result["content"][0]["text"] if result.get("content") else ""
    return content, None


def parse_response(text: str, valid_names: list[str],
                   lang_cfg: dict | None = None) -> tuple[str | None, str | None]:
    """Parse a response and return canonical English value names.

    Matches against localized names first (per lang_cfg), then falls back to
    canonical English names. Strips punctuation/whitespace.
    """
    most = least = None
    local_to_canon = lang_cfg["local_to_canon"] if lang_cfg else {}
    # Also match canonical names as fallback (models sometimes reply in English
    # even when prompted in another language)
    canon_names = {n: n for n in valid_names}
    matchers = {**local_to_canon, **canon_names}
    # Valid canonical names for the current set
    valid_set = set(valid_names)

    def match_value(val: str) -> str | None:
        val = val.strip().rstrip(".,;:!?،。").strip("*` \"'")
        # Try exact match
        if val in matchers and matchers[val] in valid_set:
            return matchers[val]
        # Try case-insensitive match
        val_low = val.lower()
        for k, v in matchers.items():
            if k.lower() == val_low and v in valid_set:
                return v
        # Try substring match (model may wrap name in explanation)
        for k, v in matchers.items():
            if k in val and v in valid_set:
                return v
        return None

    for line in text.splitlines():
        line = line.strip()
        up = line.upper()
        if up.startswith("MOST:") or up.startswith("MOST :"):
            val = line.split(":", 1)[1]
            most = match_value(val)
        elif up.startswith("LEAST:") or up.startswith("LEAST :"):
            val = line.split(":", 1)[1]
            least = match_value(val)
    return most, least


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(results: list[dict]) -> dict[str, dict]:
    counts = {v: {"best": 0, "worst": 0, "appearances": 0} for v in VALUE_NAMES}
    for r in results:
        for v in r["set"]:
            counts[v]["appearances"] += 1
        if r["most"]:
            counts[r["most"]]["best"] += 1
        if r["least"]:
            counts[r["least"]]["worst"] += 1
    scores = {}
    for v, c in counts.items():
        n = c["appearances"]
        scores[v] = {
            **c,
            "bws": (c["best"] - c["worst"]) / n if n > 0 else None,
        }
    return scores


def print_profile(scores: dict[str, dict]):
    ranked = sorted(
        [(v, s) for v, s in scores.items() if s["bws"] is not None],
        key=lambda x: -x[1]["bws"]
    )
    print(f"\n── BWS Value Profile ────────────────────────────────────")
    print(f"{'Value':<20} {'BWS':>6}  {'Best':>4}  {'Worst':>5}  {'N':>3}")
    print("-" * 50)
    for v, s in ranked:
        print(f"{v:<20} {s['bws']:>+6.2f}  {s['best']:>4}  {s['worst']:>5}  {s['appearances']:>3}")

    oc = {"Self-Direction", "Stimulation", "Hedonism"}
    cons = {"Security", "Conformity", "Tradition"}
    se = {"Power", "Achievement"}
    st = {"Universalism", "Benevolence"}

    def dim(vs):
        vals = [scores[v]["bws"] for v in vs if scores[v]["bws"] is not None]
        return sum(vals) / len(vals) if vals else None

    print("\n── Higher-Order Dimensions ──────────────────────────────")
    print(f"  Openness to Change:    {dim(oc):+.3f}")
    print(f"  Conservation:          {dim(cons):+.3f}")
    print(f"  Self-Enhancement:      {dim(se):+.3f}")
    print(f"  Self-Transcendence:    {dim(st):+.3f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(sets: list[list[str]], call_fn, lang_cfg: dict,
        save_fn=None, existing: list[dict] | None = None,
        label: str = "") -> list[dict]:
    """Run BWS over all sets, resuming from existing results if provided.

    save_fn(results) is called after each newly completed set so progress
    is persisted incrementally — interrupting the script loses at most one
    set's work.

    Resume is index-based: existing[i] is trusted to correspond to sets[i].
    Only entries whose most/least are None or response is None are re-run.
    """
    results = list(existing) if existing else []
    # Pad results to match sets length with placeholders
    while len(results) < len(sets):
        results.append(None)

    for i, s in enumerate(sets):
        # Skip if we already have a valid result at this index for the same set
        prior = results[i]
        if prior and prior.get("set") == s and prior.get("response") is not None:
            print(f"  [{i+1}/{len(sets)}] {s} {label} (cached) "
                  f"MOST={prior.get('most')} LEAST={prior.get('least')}", flush=True)
            continue

        print(f"  [{i+1}/{len(sets)}] {s} {label}", end=" ", flush=True)
        try:
            content, reasoning = call_fn(s)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            results[i] = {"set": s, "most": None, "least": None,
                          "response": None, "reasoning": None}
            if save_fn:
                save_fn(results)
            continue
        most, least = parse_response(content, s, lang_cfg)
        results[i] = {"set": s, "most": most, "least": least,
                      "response": content, "reasoning": reasoning}
        print(f"MOST={most} LEAST={least}", flush=True)
        if save_fn:
            save_fn(results)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="local-model",
                        help="Model ID (e.g. glm-5.1, claude-sonnet-4-6, openai/gpt-4.1)")
    parser.add_argument("--provider", default="openai",
                        choices=["openai", "anthropic", "bedrock"],
                        help="API provider (openai covers local, Z.ai, Moonshot, OpenRouter)")
    parser.add_argument("--api-url", default=None,
                        help="API base URL (default: http://localhost:{port}/v1)")
    parser.add_argument("--api-key", default=None,
                        help="API key (or set via env vars)")
    parser.add_argument("--port", type=int, default=8080,
                        help="Local server port (used if no --api-url)")
    parser.add_argument("--thinking", action="store_true",
                        help="Enable thinking (local llama-server only)")
    parser.add_argument("--set-size", type=int, default=4)
    parser.add_argument("--appearances", type=int, default=6,
                        help="Target appearances per value")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--language", default="en",
                        help="Language for value names, system prompt, and BWS prompt")
    parser.add_argument("--scheme", default="higher-order",
                        choices=["higher-order", "svs-items"],
                        help="Which value scheme to use. higher-order=abstract "
                             "Schwartz labels (Power, Tradition, ...); "
                             "svs-items=validated SVS57 representative items")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    lang_cfg = get_language_config(args.language, args.scheme)

    # Resolve API key from args or env
    def resolve_key(*env_names, default="not-needed"):
        if args.api_key:
            return args.api_key
        for name in env_names:
            val = os.environ.get(name)
            if val:
                return val
        return default

    # Build client
    if args.provider == "anthropic":
        if not anthropic:
            raise RuntimeError("pip install anthropic")
        key = resolve_key("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=key)
        call_fn = lambda names: call_anthropic(client, args.model, names, lang_cfg)
    elif args.provider == "bedrock":
        if not boto3:
            raise RuntimeError("pip install boto3")
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
        call_fn = lambda names: call_bedrock(client, args.model, names, lang_cfg)
    else:
        base_url = args.api_url or f"http://localhost:{args.port}/v1"
        # Pick key based on URL
        if args.api_url and "moonshot" in args.api_url:
            key = resolve_key("MOONSHOT_API_KEY")
        elif args.api_url and "openrouter" in args.api_url:
            key = resolve_key("OPENROUTER_API_KEY")
        elif args.api_url and ("z.ai" in args.api_url or "bigmodel" in args.api_url):
            key = resolve_key("ZAI_API_KEY")
        else:
            key = resolve_key("OPENROUTER_API_KEY", "ZAI_API_KEY", "MOONSHOT_API_KEY")
        client = openai.OpenAI(base_url=base_url, api_key=key, timeout=120.0)
        call_fn = lambda names: call_openai_compat(client, args.model, names,
                                                    args.thinking, lang_cfg)

    sets = balanced_design(VALUE_NAMES, args.set_size, args.appearances, args.seed)
    print(f"Model: {args.model}")
    print(f"Language: {args.language}")
    print(f"Scheme: {args.scheme}")
    print(f"Design: {len(sets)} sets × {args.set_size} values "
          f"(target {args.appearances} appearances each)\n")

    # Resume: load existing results if output file exists. Note: the output
    # file at this point may be incomplete (was being written to mid-run).
    # We only load if the saved design matches the current sets.
    existing_results = None
    if args.out and os.path.exists(args.out):
        try:
            with open(args.out) as f:
                prev = json.load(f)
            prev_results = prev.get("results", [])
            prev_sets = [r.get("set") for r in prev_results if r]
            if prev_sets == sets[:len(prev_sets)]:
                existing_results = prev_results
                completed = sum(1 for r in prev_results if r and r.get("response"))
                print(f"Resuming: {completed}/{len(sets)} sets already completed\n")
            else:
                print(f"Existing file's design doesn't match — starting fresh\n")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Couldn't parse existing file ({e}) — starting fresh\n")

    def save_progress(partial_results):
        if not args.out:
            return
        # Filter out None placeholders for serialization
        serializable = [r for r in partial_results if r is not None]
        output = {
            "model": args.model,
            "provider": args.provider,
            "language": args.language,
            "scheme": args.scheme,
            "results": serializable,
            "scores": {v: s for v, s in compute_scores(serializable).items()},
            "complete": False,
        }
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    results = run(sets, call_fn, lang_cfg,
                  save_fn=save_progress, existing=existing_results)

    # Check for too many failures before final save
    valid = sum(1 for r in results if r and r.get("most") is not None)
    if valid == 0:
        print(f"\nAll {len(results)} queries failed — not saving complete marker.")
        raise SystemExit(1)
    elif valid < len(results) // 2:
        print(f"\nWarning: only {valid}/{len(results)} valid responses")

    print_profile(compute_scores(results))

    if args.out:
        output = {
            "model": args.model,
            "provider": args.provider,
            "language": args.language,
            "scheme": args.scheme,
            "results": results,
            "scores": {v: s for v, s in compute_scores(results).items()},
            "complete": True,
        }
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
