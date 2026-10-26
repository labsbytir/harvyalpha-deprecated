import re

EMAIL_REGEX = re.compile(r'(?<![A-Za-z0-9._%*+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
MASKED_EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]*\*\*\*[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')


def mask_email(email: str) -> str:
    """Mask email to pattern: j***n@acme.com."""
    if not isinstance(email, str) or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if "***" in local:
        return email
    if len(local) <= 1:
        masked_local = local + "***"
    elif len(local) == 2:
        masked_local = local[0] + "***" + local[1]
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def mask_emails_in_text(text: str) -> str:
    """Replace all plaintext email addresses in text with masked versions."""
    if not isinstance(text, str) or not text:
        return text
    return EMAIL_REGEX.sub(lambda m: mask_email(m.group(0)), text)


def extract_emails(text: str) -> list[str]:
    """Extract real plaintext emails from text (ignoring already masked ones)."""
    if not isinstance(text, str) or not text:
        return []
    matches = EMAIL_REGEX.findall(text)
    return list(dict.fromkeys(matches))
