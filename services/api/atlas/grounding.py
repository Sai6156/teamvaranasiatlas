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


def disclosed_column_totals(answer: str, question: str, sources: list[dict]) -> str:
    """Compute requested category sums only from exact, source-verified rows."""
    if not re.search(r"\b(?:total|totals|overall|combined)\b", question, re.I):
        return answer
    lines = answer.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = [
            re.sub(r"[*`]", "", cell).strip()
            for cell in line.strip().strip("|").split("|")
        ]
        if not headers or headers[0].lower() not in ("location", "region", "geography"):
            continue
        if any(re.search(r"fy|year|rate|percent", header, re.I) for header in headers):
            continue
        rows = []
        for data_line in lines[index + 2 :]:
            if not data_line.strip().startswith("|"):
                break
            cells = [
                re.sub(r"[*`]", "", cell).strip()
                for cell in data_line.strip().strip("|").split("|")
            ]
            if len(cells) != len(headers) or not all(
                re.fullmatch(r"[\d,]+", cell) for cell in cells[1:]
            ):
                break
            rows.append(cells)
        if len(rows) < 2 or {row[0].lower() for row in rows} not in (
            {"national", "international"},
            {"domestic", "international"},
        ):
            continue
        witness = None
        for source in sources:
            plain = re.sub(r"\s+", " ", source["content"]).lower()
            if all(
                re.search(
                    r"\b"
                    + re.escape(row[0].lower())
                    + r"\s+"
                    + r"\s+".join(re.escape(cell) for cell in row[1:])
                    + r"\b",
                    plain,
                )
                for row in rows
            ):
                witness = source
                break
        if witness is None:
            continue
        totals = []
        for column, header in enumerate(headers[1:], 1):
            if header.lower() == "total":
                continue
            values = [int(row[column].replace(",", "")) for row in rows]
            totals.append(
                f"**{header}: {' + '.join(str(value) for value in values)} = {sum(values):,}**"
            )
        if totals:
            return (
                answer
                + "\n\nDerived totals across the disclosed locations: "
                + "; ".join(totals)
                + f" [{witness['number']}]."
            )
    return answer


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
