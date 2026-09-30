"""
Per-line checks for the content editor, so problems show up next to the
bullet that has them while you type. Same rules as the pipeline's guards
(and reusing its regexes), but returning structured issues instead of
printing, and never modifying anything. The render step still runs the real
guards in generate_resume.py; this is only the live preview of them.
"""

import re

import generate_resume as g

LONG_BULLET = 240


def _digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s)


def _number_issues(text: str, allowed_digits: set, against: str) -> list[dict]:
    issues = []
    for match in g.NUMBER_RE.findall(text):
        d = _digits(match)
        if len(d) >= 2 and d not in allowed_digits:
            issues.append({
                "kind": "number",
                "value": d,
                "severity": "warning",
                "message": f"'{match.strip()}' isn't in {against}. Please verify it.",
            })
    return issues


def lint_result(result: dict, source_text: str, fact_bank: dict | None, deny_patterns: list) -> dict:
    source_digits = {_digits(n) for n in g.NUMBER_RE.findall(source_text)} if source_text else None
    source_lower = source_text.lower()
    companies = [job.get("company", "") for job in result.get("experience", [])]

    def common(text: str) -> list[dict]:
        issues = []
        for p in deny_patterns:
            if p.search(text):
                issues.append({"kind": "deny", "severity": "error",
                               "message": f"Matches your never-claim pattern “{p.pattern}”. Rendering is blocked until it's removed."})
        if "—" in text or re.search(r"\s–\s", text):
            issues.append({"kind": "style", "severity": "info",
                           "message": "Contains an em dash; it will be replaced with a comma when rendered."})
        if g.ANALOGY_RE.search(text):
            issues.append({"kind": "analogy", "severity": "warning",
                           "message": "Comparison phrasing may overclaim relevance to unfamiliar terms."})
        if source_digits is not None:
            issues += _number_issues(text, source_digits, "your profile or prior resume")
        return issues

    out = {"summary": common(result.get("summary", "")), "bullets": {}, "skills": {}, "cover_letter": {}}

    for j, job in enumerate(result.get("experience", [])):
        company = job.get("company", "")
        others = [c for c in companies if c and c != company]
        for b, bullet in enumerate(job.get("bullets", [])):
            text, ids = bullet.get("text", ""), bullet.get("ids") or []
            issues = common(text)
            for other in others:
                if any(kw.lower() in text.lower() for kw in g._company_keywords(other)):
                    issues.append({"kind": "cross_employer", "severity": "warning",
                                   "message": f"Mentions {other}, a different employer."})
                    break
            if fact_bank is not None:
                if not ids:
                    issues.append({"kind": "uncited", "severity": "warning",
                                   "message": "Not linked to any fact in your fact bank."})
                cited_text = []
                for fid in ids:
                    fact = fact_bank.get(fid)
                    if fact is None:
                        issues.append({"kind": "citation", "severity": "error", "message": f"Cites unknown fact {fid}."})
                    elif fact["employer"] not in (company, "general"):
                        issues.append({"kind": "citation", "severity": "error",
                                       "message": f"Cites {fid}, a fact from {fact['employer']}."})
                    else:
                        cited_text.append(fact["text"] + " " + " ".join(map(str, fact.get("metrics") or [])))
                if cited_text:
                    cited_digits = {_digits(n) for n in g.NUMBER_RE.findall(" ".join(cited_text))}
                    flagged = {i["value"] for i in issues if i["kind"] == "number"}
                    issues += [
                        i for i in _number_issues(text, cited_digits, "the facts it cites")
                        if i["value"] not in flagged
                    ]
            if len(text) > LONG_BULLET:
                issues.append({"kind": "length", "severity": "info",
                               "message": f"{len(text)} characters; bullets over ~{LONG_BULLET} tend to wrap to three lines."})
            if issues:
                out["bullets"][f"{j}.{b}"] = issues

    for i, skill in enumerate(result.get("skills", [])):
        issues = [x for x in common(skill) if x["kind"] == "deny"]
        core = re.sub(r"\s*\([^)]*\)", "", skill).strip().lower()
        if source_text and core and core not in source_lower:
            issues.append({"kind": "unverified", "severity": "warning",
                           "message": "Not found verbatim in your profile or prior resume."})
        if issues:
            out["skills"][str(i)] = issues

    for i, para in enumerate(result.get("cover_letter") or []):
        issues = common(para.get("text", ""))
        if issues:
            out["cover_letter"][str(i)] = issues

    counts = {"error": 0, "warning": 0, "info": 0}
    for group in (out["summary"], *out["bullets"].values(), *out["skills"].values(), *out["cover_letter"].values()):
        for issue in group:
            counts[issue["severity"]] += 1
    out["counts"] = counts
    return out
