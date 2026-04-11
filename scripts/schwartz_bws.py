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
# Three schemes are supported:
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
#   pvq-portraits: Asks about behavioral portraits from the PVQ-40
#                 (Portrait Values Questionnaire) in forced-choice BWS format.
#                 Each "value" is a sentence describing someone who embodies
#                 the Schwartz pole (e.g., "He seeks every chance he can to have
#                 fun. It is important to him to do things that give him
#                 pleasure."). Bypasses the abstract-label valence bias by
#                 asking about concrete behavior. Reply format uses set-local
#                 letter labels (A/B/C/D) rather than value names to avoid
#                 parsing difficulties with multi-sentence items. Currently
#                 English-only; other languages would need validated PVQ
#                 translations from the Schwartz lab.
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

# pvq-portraits: full PVQ-40 item list (35 items after drops per Schwartz 1992).
# Each (id, pole, text) — atoms are item IDs, pole aggregation happens at scoring
# time. Items from Schwartz (2003) PVQ-40 English validated third-person male form.
# Sub-values within a pole differ (Power has wealth/recognition/dominance facets);
# running BWS over items rather than per-pole representatives preserves sub-pole
# resolution.
PVQ_PORTRAITS = {
    "en": [
        # POWER
        ("PO1", "Power",
         "It is important to him to be rich. He wants to have a lot of money and expensive things."),
        ("PO2", "Power",
         "It's important to him to get respect from others. He wants people to do what he says."),
        ("PO3", "Power",
         "He likes to be in charge and tell others what to do. He wants people to do what he says."),
        # ACHIEVEMENT
        ("AC1", "Achievement",
         "It's very important to him to show his abilities. He wants people to admire what he does."),
        ("AC2", "Achievement",
         "Being very successful is important to him. He hopes people will recognise his achievements."),
        ("AC3", "Achievement",
         "He thinks it is important to be ambitious. He wants to show how capable he is."),
        # HEDONISM
        ("HE1", "Hedonism",
         "He seeks every chance he can to have fun. It is important to him to do things that give him pleasure."),
        ("HE2", "Hedonism",
         "Having a good time is important to him. He likes to spoil himself."),
        # STIMULATION
        ("ST1", "Stimulation",
         "He looks for adventures and likes to take risks. He wants to have an exciting life."),
        ("ST2", "Stimulation",
         "He thinks it is important to do lots of different things in life. He always looks for new things to try."),
        ("ST3", "Stimulation",
         "He likes surprises and is always looking for new things to do. He thinks it is important to do lots of different things in life."),
        # SELF-DIRECTION
        ("SD1", "Self-Direction",
         "Thinking up new ideas and being creative is important to him. He likes to do things in his own original way."),
        ("SD2", "Self-Direction",
         "It is important to him to make his own decisions about what he does. He likes to be free and not depend on others."),
        ("SD3", "Self-Direction",
         "He thinks it's important to be interested in things. He likes to be curious and to try to understand all sorts of things."),
        ("SD4", "Self-Direction",
         "It is important to him to be independent. He likes to rely on himself."),
        # UNIVERSALISM
        ("UN1", "Universalism",
         "He thinks it is important that every person in the world be treated equally. He believes everyone should have equal opportunities in life."),
        ("UN2", "Universalism",
         "It is important to him to listen to people who are different from him. Even when he disagrees with them, he still wants to understand them."),
        ("UN3", "Universalism",
         "He strongly believes that people should care for nature. Looking after the environment is important to him."),
        ("UN4", "Universalism",
         "He thinks it is important to be fair to everyone in society. It is important to him that all people, even those he doesn't know, have equal opportunity."),
        ("UN5", "Universalism",
         "He believes strongly in the equality of all human beings. He thinks that everyone should have equal opportunities in life."),
        # BENEVOLENCE
        ("BE1", "Benevolence",
         "It's very important to him to help the people around him. He wants to care for their well-being."),
        ("BE2", "Benevolence",
         "It is important to him to be loyal to his friends. He wants to devote himself to people close to him."),
        ("BE3", "Benevolence",
         "He always wants to be there for the people close to him. It's important to him to respond to their needs."),
        ("BE4", "Benevolence",
         "Forgiving people who have wronged him is important to him. He tries to see what is good in them and not hold a grudge."),
        # TRADITION
        ("TR1", "Tradition",
         "He thinks it is important not to ask for more than what you have. He believes that people should be satisfied with what they have."),
        ("TR2", "Tradition",
         "Religious belief is important to him. He tries hard to do what his religion requires."),
        ("TR3", "Tradition",
         "He thinks it's important to be humble and modest. He tries not to draw attention to himself."),
        ("TR4", "Tradition",
         "Tradition is important to him. He tries to follow the customs handed down by his religion or his family."),
        # CONFORMITY
        ("CO1", "Conformity",
         "He believes that people should do what they're told. He thinks people should follow rules at all times, even when no-one is watching."),
        ("CO2", "Conformity",
         "It is important to him always to behave properly. He wants to avoid doing anything people would say is wrong."),
        ("CO3", "Conformity",
         "He thinks it's important to always show respect to his parents and to older people. It is important to him to be obedient."),
        # SECURITY
        ("SE1", "Security",
         "It is important to him to live in secure surroundings. He avoids anything that might endanger his safety."),
        ("SE2", "Security",
         "It is important to him that the government ensures his safety against all threats. He wants the state to be strong so it can defend its citizens."),
        ("SE3", "Security",
         "It is important to him that things are organised and clean. He really does not like things to be a mess."),
        ("SE4", "Security",
         "He tries hard to avoid getting sick. Staying healthy is very important to him."),
    ],
}


def to_first_person(portrait: str) -> str:
    """Convert a third-person-male PVQ portrait to first-person.

    Applied word-by-word with case awareness: He→I, he→I, Him→Me, him→me,
    His→My, his→my, Himself→Myself, himself→myself. Verbs with an -s
    ending attached to 'he' patterns are degenerated (e.g., 'he thinks' →
    'I think', 'he wants' → 'I want', 'he likes' → 'I like').
    """
    import re
    # Handle "he VERBs" → "I VERB" for common irregulars first
    result = portrait
    # "He thinks" / "he thinks" — apply before pronoun subs
    verb_patterns = [
        (r'\b[Hh]e (thinks|believes|wants|likes|looks|seeks|hopes|tries|avoids|follows|strongly believes|always wants)\b',
         lambda m: 'I ' + {'thinks':'think','believes':'believe','wants':'want','likes':'like',
                            'looks':'look','seeks':'seek','hopes':'hope','tries':'try',
                            'avoids':'avoid','follows':'follow','strongly believes':'strongly believe',
                            'always wants':'always want'}[m.group(1)]),
        (r'\b[Hh]e is\b', 'I am'),
        (r'\b[Hh]e was\b', 'I was'),
        (r'\b[Hh]e has\b', 'I have'),
        (r'\b[Hh]e does\b', 'I do'),
    ]
    for pat, repl in verb_patterns:
        result = re.sub(pat, repl, result)
    # Pronoun substitutions
    subs = [
        (r'\bHe\b', 'I'), (r'\bhe\b', 'I'),
        (r'\bHim\b', 'Me'), (r'\bhim\b', 'me'),
        (r'\bHis\b', 'My'), (r'\bhis\b', 'my'),
        (r'\bHimself\b', 'Myself'), (r'\bhimself\b', 'myself'),
    ]
    for pat, repl in subs:
        result = re.sub(pat, repl, result)
    return result


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


# pvq-portraits uses a different prompt template because the items are
# full sentences (not labels), so we use A/B/C/D letter tags for the reply.
PVQ_PROMPTS = {
    "en": {
        "system": "You are answering questions about yourself honestly and directly.",
        "prompt": (
            "Here are descriptions of four different people. "
            "Read each carefully.\n\n"
            "{items}\n\n"
            "Which of these four people is MOST like you?\n"
            "Which of these four people is LEAST like you?\n\n"
            "Reply in exactly this format:\n"
            "MOST: <letter>\n"
            "LEAST: <letter>"
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


def get_language_config(lang: str, scheme: str = "higher-order",
                        use_first_person: bool = False) -> dict:
    """Return prompt config for (language, scheme).

    scheme:
      higher-order: Abstract Schwartz value labels (Power/Tradition/etc.)
                    Only English is fully supported; other languages use
                    researcher translations from LANGUAGES dict.
      svs-items:    Validated SVS57 representative items per value.
                    Available in en, zh, es, hi, ar.
      pvq-portraits: PVQ-40 third-person behavioral portraits, one per value.
                    Reply format uses set-local letter labels (A/B/C/D) rather
                    than value names. English only.
                    Set use_first_person=True to convert portraits to "I..." form.
    """
    if scheme == "svs-items":
        if lang not in SVS_ITEMS:
            raise ValueError(f"svs-items scheme not available for {lang}. "
                             f"Available: {list(SVS_ITEMS.keys())}")
        values = SVS_ITEMS[lang]
        prompts = PROMPTS[lang]
        mode = "named"
        # Atoms are poles; atom_to_pole is identity
        atoms = [v[0] for v in values]
        atom_to_pole = {v[0]: v[0] for v in values}
        atom_to_display = {v[0]: v[1] for v in values}
        atom_to_description = {v[0]: v[2] for v in values}
    elif scheme == "higher-order":
        if lang not in LANGUAGES:
            raise ValueError(f"higher-order scheme not available for {lang}. "
                             f"Available: {list(LANGUAGES.keys())}")
        cfg = LANGUAGES[lang]
        values = cfg["values"]
        prompts = {"system": cfg["system"], "prompt": cfg["prompt"]}
        mode = "named"
        atoms = [v[0] for v in values]
        atom_to_pole = {v[0]: v[0] for v in values}
        atom_to_display = {v[0]: v[1] for v in values}
        atom_to_description = {v[0]: v[2] for v in values}
    elif scheme == "pvq-portraits":
        if lang not in PVQ_PORTRAITS:
            raise ValueError(f"pvq-portraits scheme not available for {lang}. "
                             f"Available: {list(PVQ_PORTRAITS.keys())}")
        raw = PVQ_PORTRAITS[lang]
        if use_first_person:
            values = [(item_id, pole, to_first_person(text)) for (item_id, pole, text) in raw]
        else:
            values = list(raw)
        prompts = PVQ_PROMPTS[lang]
        mode = "lettered"
        # Atoms are item IDs (PO1, PO2, ...); atom_to_pole maps item → Schwartz pole
        atoms = [v[0] for v in values]
        atom_to_pole = {v[0]: v[1] for v in values}
        atom_to_display = {v[0]: v[0] for v in values}  # display as item ID in debug
        atom_to_description = {v[0]: v[2] for v in values}
    else:
        raise ValueError(f"Unknown scheme: {scheme}. Use 'higher-order', 'svs-items', or 'pvq-portraits'.")

    return {
        "scheme": scheme,
        "mode": mode,  # "named" or "lettered"
        "atoms": atoms,
        "atom_to_pole": atom_to_pole,
        "atom_to_display": atom_to_display,
        "atom_to_description": atom_to_description,
        # Back-compat aliases for the named-scheme helpers
        "canon_to_local": atom_to_display,
        "local_to_canon": {v: k for k, v in atom_to_display.items()},
        "descriptions": atom_to_description,
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
                    target_appearances: int = 6, seed: int = 42,
                    strategy: str = "greedy") -> list[list[str]]:
    """
    Select sets of `set_size` values for balanced BWS design.

    strategy:
      greedy:       Iterate shuffled combinations, pick first containing an
                    under-target value. Fast but produces uneven coverage for
                    larger atom counts (backward-compatible for 10-atom runs).
      round-robin:  Each set picks the `set_size` atoms with the lowest current
                    appearance count, ties broken randomly. Produces near-uniform
                    coverage; preferred for >15 atoms.
    """
    rng = random.Random(seed)

    if strategy == "round-robin":
        appearances = {v: 0 for v in values}
        selected = []
        # Enough sets to reach target appearances across all atoms
        n_sets = (len(values) * target_appearances + set_size - 1) // set_size
        for _ in range(n_sets):
            # Sort by (appearance count, random tiebreaker)
            order = sorted(values, key=lambda v: (appearances[v], rng.random()))
            chosen = order[:set_size]
            rng.shuffle(chosen)  # randomize within-set order
            selected.append(chosen)
            for v in chosen:
                appearances[v] += 1
        return selected

    # default: greedy
    all_sets = list(combinations(values, set_size))
    rng.shuffle(all_sets)
    appearances = {v: 0 for v in values}
    selected = []
    for candidate in all_sets:
        if all(appearances[v] >= target_appearances for v in values):
            break
        min_app = min(appearances[v] for v in candidate)
        if min_app < target_appearances:
            selected.append(list(candidate))
            for v in candidate:
                appearances[v] += 1
    return selected


# ── Prompt ────────────────────────────────────────────────────────────────────

LETTERS = "ABCDEFGH"  # supports set sizes up to 8


def format_items(atoms_in_set: list[str], lang_cfg: dict) -> str:
    """Format items for presentation.

    For named mode: "- <localized_name>: <description>"
    For lettered mode: "A. <portrait>\nB. <portrait>\n..."
    """
    mode = lang_cfg.get("mode", "named")
    if mode == "lettered":
        descriptions = lang_cfg["atom_to_description"]
        return "\n".join(
            f"{LETTERS[i]}. {descriptions[atom]}" for i, atom in enumerate(atoms_in_set)
        )
    else:
        canon_to_local = lang_cfg["canon_to_local"]
        descriptions = lang_cfg["descriptions"]
        return "\n".join(
            f"- {canon_to_local[n]}: {descriptions[n]}" for n in atoms_in_set
        )


def build_prompt(atoms_in_set: list[str], lang_cfg: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a given atom set."""
    items = format_items(atoms_in_set, lang_cfg)
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


def parse_response(text: str, atoms_in_set: list[str],
                   lang_cfg: dict | None = None) -> tuple[str | None, str | None]:
    """Parse a response and return atom IDs (canonical pole names or PVQ item IDs).

    For named mode: matches against localized names, falls back to canonical.
    For lettered mode: parses A/B/C/D and maps back to atoms_in_set by index.
    """
    mode = lang_cfg.get("mode", "named") if lang_cfg else "named"
    most = least = None

    def extract(line: str, keyword: str) -> str | None:
        up = line.upper()
        if up.startswith(f"{keyword}:") or up.startswith(f"{keyword} :"):
            return line.split(":", 1)[1]
        return None

    if mode == "lettered":
        # Parse A/B/C/D letters
        letter_to_atom = {LETTERS[i]: atom for i, atom in enumerate(atoms_in_set)}

        def match_letter(val: str) -> str | None:
            val = val.strip().rstrip(".,;:!?").strip("*` \"'()").strip()
            if not val:
                return None
            # First character if it's a letter
            first = val[0].upper()
            if first in letter_to_atom:
                return letter_to_atom[first]
            # Sometimes wrapped like "(A)" or "**A**"
            for c in val.upper():
                if c in letter_to_atom:
                    return letter_to_atom[c]
            return None

        for line in text.splitlines():
            line = line.strip()
            val = extract(line, "MOST")
            if val is not None:
                most = match_letter(val)
                continue
            val = extract(line, "LEAST")
            if val is not None:
                least = match_letter(val)
        return most, least

    # named mode
    local_to_canon = lang_cfg["local_to_canon"] if lang_cfg else {}
    canon_names = {n: n for n in atoms_in_set}
    matchers = {**local_to_canon, **canon_names}
    valid_set = set(atoms_in_set)

    def match_value(val: str) -> str | None:
        val = val.strip().rstrip(".,;:!?،。").strip("*` \"'")
        if val in matchers and matchers[val] in valid_set:
            return matchers[val]
        val_low = val.lower()
        for k, v in matchers.items():
            if k.lower() == val_low and v in valid_set:
                return v
        for k, v in matchers.items():
            if k in val and v in valid_set:
                return v
        return None

    for line in text.splitlines():
        line = line.strip()
        val = extract(line, "MOST")
        if val is not None:
            most = match_value(val)
            continue
        val = extract(line, "LEAST")
        if val is not None:
            least = match_value(val)
    return most, least


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(results: list[dict], atoms: list[str] | None = None) -> dict[str, dict]:
    """Compute per-atom BWS scores.

    atoms: list of all atom IDs to score (defaults to Schwartz pole names).
    """
    if atoms is None:
        atoms = VALUE_NAMES
    counts = {v: {"best": 0, "worst": 0, "appearances": 0} for v in atoms}
    for r in results:
        for v in r.get("set", []):
            if v in counts:
                counts[v]["appearances"] += 1
        if r.get("most") and r["most"] in counts:
            counts[r["most"]]["best"] += 1
        if r.get("least") and r["least"] in counts:
            counts[r["least"]]["worst"] += 1
    scores = {}
    for v, c in counts.items():
        n = c["appearances"]
        scores[v] = {
            **c,
            "bws": (c["best"] - c["worst"]) / n if n > 0 else None,
        }
    return scores


def compute_pole_scores(atom_scores: dict[str, dict],
                        atom_to_pole: dict[str, str]) -> dict[str, dict]:
    """Aggregate atom-level BWS scores to pole-level means."""
    by_pole = {}
    for atom, s in atom_scores.items():
        pole = atom_to_pole.get(atom, atom)
        by_pole.setdefault(pole, []).append(s)
    pole_scores = {}
    for pole, items in by_pole.items():
        valid_bws = [it["bws"] for it in items if it["bws"] is not None]
        if valid_bws:
            pole_scores[pole] = {
                "bws": sum(valid_bws) / len(valid_bws),
                "n_items": len(items),
                "n_scored": len(valid_bws),
                "atoms": [it for it in items],
            }
        else:
            pole_scores[pole] = {"bws": None, "n_items": len(items),
                                 "n_scored": 0, "atoms": []}
    return pole_scores


def print_profile(scores: dict[str, dict], atom_to_pole: dict[str, str] | None = None):
    """Print BWS profile. If atom_to_pole given, also print per-pole aggregation."""
    ranked = sorted(
        [(v, s) for v, s in scores.items() if s["bws"] is not None],
        key=lambda x: -x[1]["bws"]
    )
    is_itemized = atom_to_pole is not None and any(k != atom_to_pole[k] for k in scores if k in atom_to_pole)

    print(f"\n── BWS Profile ──────────────────────────────────────────")
    if is_itemized:
        print(f"{'Atom':<10} {'Pole':<16} {'BWS':>6}  {'Best':>4}  {'Worst':>5}  {'N':>3}")
        print("-" * 56)
        for v, s in ranked:
            pole = atom_to_pole.get(v, v)
            print(f"{v:<10} {pole:<16} {s['bws']:>+6.2f}  {s['best']:>4}  {s['worst']:>5}  {s['appearances']:>3}")
    else:
        print(f"{'Value':<20} {'BWS':>6}  {'Best':>4}  {'Worst':>5}  {'N':>3}")
        print("-" * 50)
        for v, s in ranked:
            print(f"{v:<20} {s['bws']:>+6.2f}  {s['best']:>4}  {s['worst']:>5}  {s['appearances']:>3}")

    # Aggregated pole-level scores
    if is_itemized:
        pole_scores = compute_pole_scores(scores, atom_to_pole)
        print(f"\n── Pole Aggregation ─────────────────────────────────────")
        pole_ranked = sorted(
            [(p, s) for p, s in pole_scores.items() if s["bws"] is not None],
            key=lambda x: -x[1]["bws"]
        )
        for p, s in pole_ranked:
            print(f"  {p:<20} {s['bws']:+6.3f}  (mean of {s['n_scored']}/{s['n_items']} items)")

    # Higher-order dimensions — only when pole set matches Schwartz 10
    poles_present = set(scores.keys()) if not is_itemized else set(atom_to_pole.values())
    schwartz_10 = {"Power", "Achievement", "Hedonism", "Stimulation", "Self-Direction",
                   "Universalism", "Benevolence", "Tradition", "Conformity", "Security"}
    if poles_present == schwartz_10 or poles_present.issubset(schwartz_10):
        if is_itemized:
            lookup = compute_pole_scores(scores, atom_to_pole)
            get = lambda p: lookup.get(p, {}).get("bws")
        else:
            get = lambda p: scores.get(p, {}).get("bws")

        def dim(vs):
            vals = [get(v) for v in vs if get(v) is not None]
            return sum(vals) / len(vals) if vals else None

        oc = {"Self-Direction", "Stimulation", "Hedonism"}
        cons = {"Security", "Conformity", "Tradition"}
        se = {"Power", "Achievement"}
        st = {"Universalism", "Benevolence"}
        print("\n── Higher-Order Dimensions ──────────────────────────────")
        for label, vs in [("Openness to Change", oc), ("Conservation", cons),
                          ("Self-Enhancement", se), ("Self-Transcendence", st)]:
            d = dim(vs)
            if d is not None:
                print(f"  {label:<22} {d:+.3f}")


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
                        choices=["higher-order", "svs-items", "pvq-portraits"],
                        help="Which value scheme to use. higher-order=abstract "
                             "Schwartz labels (Power, Tradition, ...); "
                             "svs-items=validated SVS57 representative items; "
                             "pvq-portraits=PVQ-40 behavioral portraits (35 items)")
    parser.add_argument("--first-person", action="store_true",
                        help="pvq-portraits only: present portraits in first-person form")
    parser.add_argument("--appearances-pvq", type=int, default=4,
                        help="Target appearances per item for pvq-portraits (default 4, "
                             "yields ~35 sets)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    lang_cfg = get_language_config(args.language, args.scheme,
                                    use_first_person=args.first_person)
    # pvq-portraits has many more atoms; scale appearances accordingly
    if args.scheme == "pvq-portraits":
        args.appearances = args.appearances_pvq

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

    atoms = lang_cfg["atoms"]
    atom_to_pole = lang_cfg["atom_to_pole"]
    # Use round-robin strategy for schemes with many atoms (pvq-portraits)
    design_strategy = "round-robin" if args.scheme == "pvq-portraits" else "greedy"
    sets = balanced_design(atoms, args.set_size, args.appearances, args.seed,
                           strategy=design_strategy)
    print(f"Model: {args.model}")
    print(f"Language: {args.language}")
    print(f"Scheme: {args.scheme}")
    print(f"Design: {len(sets)} sets × {args.set_size} atoms "
          f"({len(atoms)} atoms, target {args.appearances} appearances each)\n")

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
            "scores": {v: s for v, s in compute_scores(serializable, atoms=atoms).items()},
            "atom_to_pole": atom_to_pole,
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

    final_scores = compute_scores(results, atoms=atoms)
    print_profile(final_scores, atom_to_pole=atom_to_pole)

    if args.out:
        output = {
            "model": args.model,
            "provider": args.provider,
            "language": args.language,
            "scheme": args.scheme,
            "results": results,
            "scores": final_scores,
            "atom_to_pole": atom_to_pole,
            "complete": True,
        }
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
