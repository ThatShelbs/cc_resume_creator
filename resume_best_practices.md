# Resume best practices (evidence-based)

Researched once and cached here so `generate_resume.py` doesn't have to re-research
best practices (or spend tokens/time on it) on every run. Only claims traceable to a
named study, a described methodology, or a company's own reported platform data are
included. A first pass of web search turned up dozens of "resumes with quantified
achievements get 3.2x more callbacks (Harvard Business Review)"-style statistics that
are repeated verbatim across SEO content-mill sites with no link to an actual HBR
study — those are excluded. If a number below can't be traced to a source, it isn't
here.

## Sources

- **TheLadders Eye-Tracking Study** (2012, updated 2018) — eye-tracking of 30
  professional recruiters over a 10-week period reviewing resumes.
  [recruiter.com summary](https://www.recruiter.com/recruiting/theladders-reveals-research-reporting-that-resumes-spend-six-seconds-with-a-recruiter/),
  [2018 update via PRNewswire](https://www.prnewswire.com/news-releases/ladders-updates-popular-recruiter-eye-tracking-study-with-new-key-insights-on-how-job-seekers-can-improve-their-resumes-300744217.html)
- **ResumeGo field experiments** — real fictitious resumes submitted to real job
  postings on Indeed/ZipRecruiter/Glassdoor, with actual callback rates measured.
  [One vs. two-page resume study, n=7,712](https://www.resumego.net/research/one-or-two-page-resumes/),
  [Cover letter study, n=7,287, Jul 2019–Jan 2020](https://www.resumego.net/research/cover-letters/),
  [Employment gaps study](https://www.resumego.net/research/resume-employment-gaps/)
- **Jobscan** — ATS optimization platform; claims below are their reported product/usage
  data, not independent academic research, and are treated accordingly.
  [State of the Job Search report / ATS resume guide](https://www.jobscan.co/blog/ats-resume/),
  [ATS formatting mistakes](https://www.jobscan.co/blog/ats-formatting-mistakes/),
  [Resume tables/columns and ATS parsing](https://www.jobscan.co/blog/resume-tables-columns-ats/)
- **Ge, Knox, et al., "Algorithmic Writing Assistance on Jobseekers' Resumes Increases
  Hires"** — field experiment (RCT) in an online labor market, ~half a million
  jobseekers, randomized to receive AI writing assistance or not; outcome was actual
  hire probability. [arXiv:2301.08083](https://arxiv.org/abs/2301.08083)
- **CareerBuilder recruiter surveys** — large annual surveys of hiring
  managers/recruiters on resume preferences (opinion/preference data, not outcome data).

## What the evidence supports

### Content and substance
- Quantify accomplishments (dollars, percentages, counts, time saved) wherever the
  underlying fact supports it — the RCT on AI writing assistance found that clearer,
  better-written resumes causally increased hire probability by ~8%, with no drop in
  employer satisfaction, i.e. clarity and impact-legibility help employers assess real
  ability rather than just signaling. (Ge et al., arXiv:2301.08083)
- Explaining an employment gap performs better than leaving it unaddressed.
  (ResumeGo employment gaps study)
- Don't pad with unquantified duty-lists — the eye-tracking research found recruiters
  spend the majority of their initial scan on name, titles, dates, and education, then
  scan for keywords; they are not reading dense paragraphs closely on a first pass.
  (TheLadders eye-tracking study)

### Language and phrasing
- Lead bullets with strong, specific action verbs ("led," "built," "reduced") rather
  than passive/duty phrasing ("was responsible for"). Recruiter surveys consistently
  report a preference for direct, active language over passive descriptions.
  (CareerBuilder recruiter surveys)

### Tailoring to the specific posting
- Include the exact job title language from the posting where it's an honest match —
  ATS keyword filters are used near-universally, and job-title/keyword alignment is
  the single factor ATS platforms report most strongly correlating with getting
  surfaced to a recruiter. (Jobscan)
- Tailoring the application to the specific role (not just the resume, but supporting
  materials like a cover letter) measurably raises callback rates in real submitted-
  application experiments. (ResumeGo cover letter study)
- Mirror the posting's own terminology for skills/tools the candidate genuinely has,
  since ATS and recruiter keyword scans match on exact phrasing, not synonyms.

### Structure and length
- One page is the safer default for less than ~10 years of experience; two pages is
  standard and performs at least as well for candidates with 10+ years of experience —
  do not artificially compress a long career into one page at the cost of cutting
  strong, relevant material. (ResumeGo one-vs-two-page study, n=7,712)
- Put the highest-value information first: name, current title, most recent
  employer/title/dates, and education are what get the most attention in the initial
  scan — don't bury the strongest, most relevant qualification below weaker material.
  (TheLadders eye-tracking study)
- Skills section length: no traceable study was found pinning an exact "optimal"
  count. Search results here were dominated by the same unsourced content-mill
  statistics called out above (e.g. a specific "10-15 skills" or "60% hard / 40% soft"
  split attributed to no actual study). The generator targets ~20 skills, drawn from a
  mix of tools, soft/leadership skills, methodologies, and discipline subfields,
  selected for relevance to the specific posting — a reasonable default in the absence
  of real evidence for a different number, not a research-backed figure.

### ATS-safe formatting (technical parsing mechanics, not a "study" per se — this is
how ATS text-extraction actually works)
- Single-column, left-to-right reading order. Tables and multi-column layouts cause
  ATS parsers to scramble text order because they read linearly.
- No headers/footers for content that must be parsed (contact info, section content) —
  most ATS systems skip the header/footer layer entirely.
- No text boxes, icons, or graphics for content — these live outside the normal text
  flow and are often invisible to parsers.
- Standard section headings ("Experience," "Education," "Skills") rather than creative
  labels — ATS and recruiters both pattern-match on conventional headings.
- Standard fonts (e.g., Calibri, Arial, Times New Roman), simple bullet characters, and
  a .docx or text-extractable PDF rather than a flattened image/design-tool export.

## Condensed rules for prompt injection

The generator embeds this shorter list directly in its tailoring prompt (see
`BEST_PRACTICES` in `generate_resume.py`) to keep the per-run prompt compact:

1. Quantify impact wherever the source material has a real number — dollars, %, counts, time.
2. Start bullets with strong active verbs; never passive "was responsible for" phrasing.
3. Mirror the job posting's exact terminology for skills/title language the candidate honestly has.
4. Lead with the single most relevant, highest-impact bullet per role — recruiters scan, they don't read linearly at first.
5. Don't compress a 10+ year career to fit one page at the cost of cutting strong material; don't pad a short career to fill two.
6. Cut unquantified, generic duty-description bullets in favor of fewer, sharper, evidence-backed ones.
