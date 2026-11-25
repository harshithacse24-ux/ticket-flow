
"""Optional OpenAI-compatible Generative AI API, with local KB fallback."""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()


def ai_is_configured():
    return bool(os.getenv("OPENAI_API_KEY"))


def fallback(user_text, articles):
    if articles:
        return (
            "I don't have a live Generative AI connection configured. "
            "Here are relevant local knowledge-base steps:\n\n"
            + "\n\n".join(
                f"**{a['source_title']}**\n{a['solution']}"
                for a in articles[:2]
            )
            + "\n\nIf these do not help, submit or update a ticket "
            "with the exact error and device/location."
        )

    return (
        "I couldn't find a matching article locally. Please tell me "
        "the device/service, what you expected, what happened, "
        "and any error text. If several users are affected, "
        "file a ticket for IT."
    )


def generate_ai_response(user_text, articles, history=None, task='chat'):

    history = history or []

    context = "\n\n".join(
        f"[{a['source_title']} — {a['category']}]\n{a['solution']}"
        for a in articles
    ) or "No relevant local articles."

    if not ai_is_configured():
        return fallback(user_text, articles), 'knowledge-base-fallback'

    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    url = (
        os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        .rstrip('/') + '/chat/completions'
    )

    sysmsg = (
        "You are TicketFlow, an IT helpdesk assistant. "
        "Give clear, beginner-friendly, numbered steps. "
        "Ground answers in supplied KB context, name sources when useful, "
        "and admit when context is insufficient. "
        "Never ask for passwords/OTP, claim to have changed a device, "
        "or provide risky repair steps. "
        "Advise IT escalation for urgent, widespread, security-sensitive, "
        "or unresolved issues."
    )

    if task == 'ticket_solution':
        sysmsg += " Write a concise troubleshooting solution for the submitted ticket."

    msgs = [
        {'role': 'system', 'content': sysmsg},
        {
            'role': 'system',
            'content': 'Knowledge base context:\n' + context
        }
    ]

    if task == 'chat':
        msgs.extend(
            {'role': r, 'content': m}
            for r, m in history
            if r in ('user', 'assistant')
        )

    msgs.append({'role': 'user', 'content': user_text})

    try:
        r = requests.post(
            url,
            headers={
                'Authorization': 'Bearer ' + os.getenv('OPENAI_API_KEY'),
                'Content-Type': 'application/json'
            },
            json={
                'model': model,
                'messages': msgs
            },
            timeout=40
        )

        r.raise_for_status()

        return (
            r.json()['choices'][0]['message']['content'].strip(),
            'generative-ai'
        )

    except Exception:
        return (
            "The AI service is unavailable at the moment. "
            "Local KB guidance:\n\n" + fallback(user_text, articles),
            'fallback'
        )
