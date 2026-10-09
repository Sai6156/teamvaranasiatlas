"""Conservative citation checks for obvious heading/body mismatches."""

import re

STOP_WORDS = set(
    "a an the this that these those is are was were be been being to of in on at by for from with and or as it its they their our your we you i do does did can must should will have has had before after within required requirements requirement information document documents says say source sources".split()
)


def words(text: str) -> set[str]:
    return {
        word.rstrip("s")
        for word in re.findall(r"[a-z]{3,}|\d+", text.lower())
        if word not in STOP_WORDS
    }


def citation_support(answer: str, sources: list[dict]) -> tuple[str, bool]:
    """Repair only a clearly unsupported short-heading reference, else reject it.

    This is a consistency guard, not a general factual entailment guarantee.
    The substantive answer must still come from the model's supplied evidence.
    """
    by_number = {source["number"]: source for source in sources}
    valid = True

    def replace(match):
        nonlocal valid
        number = int(match.group(1))
        original = by_number.get(number)
        if original is None:
            valid = False
            return match.group(0)
        start = max(answer.rfind("\n\n", 0, match.start()) + 2, match.start() - 450, 0)
        claim = re.sub(r"\[\d+\]", "", answer[start : match.start()])
        claim_words = words(claim)
        if len(claim_words) < 4 or len(original["content"].strip()) >= 100:
            return match.group(0)
        support = len(claim_words & words(original["content"])) / len(claim_words)
        if support >= 0.2:
            return match.group(0)
        candidates = [
            (len(claim_words & words(source["content"])) / len(claim_words), source)
            for source in sources
            if len(source["content"].strip()) >= 100
        ]
        if candidates:
            score, best = max(candidates, key=lambda entry: entry[0])
            if score >= 0.55:
                return f"[{best['number']}]"
        valid = False
        return match.group(0)

    return re.sub(r"\[(\d+)\]", replace, answer), valid


def abstention(answer: str) -> str | None:
    beginning = answer.strip()
    if re.match(
        r"^I (?:couldn.t|could not|can.t|cannot|don.t|do not) (?:find|have|establish)",
        beginning,
        re.I,
    ):
        first = re.split(r"(?<=[.!?])\s+", beginning, maxsplit=1)[0]
        return re.sub(r"\s*\[\d+\]", "", first)
    return None
