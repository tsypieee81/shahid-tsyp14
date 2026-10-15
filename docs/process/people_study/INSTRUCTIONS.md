# SHAHID explanation study — instructions for the team (protocol 07b)

## Before you start
- At least 8 people **outside the team** who have never seen SHAHID's code, documents or demo.
- Give participants codes P01, P02, … in order. Odd codes get `booklet_1.md`, even codes
  `booklet_2.md`. Print the booklet; never show `results/p7/people_key.json`.
- Record nothing that identifies a person: no names, e-mail addresses, student numbers or photos.
  Background is one of: `electrical_engineering`, `other_engineering`, `other`.
- Copy `answer_sheet_template.csv` to `answers/P01.csv` (etc.), set `participant`, `booklet` and
  `background`, and type the answers exactly as offered (`outage`, `communication`, `cannot_tell`;
  `crew`, `data_link`, `supervisor_or_wait`; numbers 1–5). Leave empty what was not answered.
- In the sheet, set `form` per item as printed in that participant's booklet (booklet 2 has form A for
  items 1–6 and form B for items 7–12).

## Text to read to each participant (English)
> This is a short study about a research prototype that uses **simulated** electricity data. It is not
> a real system and you are not being tested. You will read 12 short texts. Each describes a group of
> electricity meters that stopped sending data. For some texts you are asked what you think happened
> (power cut, communication problem, or cannot tell) and how sure you are. For the others you are asked
> what an operator should do and how clear the text was. Please answer from the text alone; there is
> no time limit, and you may stop at any time. We record only your answers and a broad background
> category, never your name. Do you agree to take part?

## Texte à lire à chaque participant (français)
> Cette courte étude porte sur un prototype de recherche qui utilise des données électriques
> **simulées**. Ce n'est pas un système réel et vous n'êtes pas évalué·e. Vous allez lire 12 textes
> courts. Chacun décrit un groupe de compteurs électriques qui ont cessé d'envoyer des données. Pour
> certains textes, on vous demande ce qui s'est passé selon vous (coupure de courant, problème de
> communication, ou impossible à dire) et votre degré de certitude. Pour les autres, on vous demande ce
> que l'opérateur devrait faire et si le texte était clair. Répondez à partir du texte seul ; il n'y a
> pas de limite de temps et vous pouvez arrêter à tout moment. Nous n'enregistrons que vos réponses et
> une grande catégorie de formation, jamais votre nom. Acceptez-vous de participer ?

Only continue after a clear yes. Do not explain the method, the numbers or the answers before the
participant has finished.

## After the sessions
```bash
python -m shahid.p7_people analyse
```
writes `results/p7/people_study.json`. With fewer than 8 participants every hypothesis is reported as
underpowered. The confident-wrong item is an over-trust indicator, not a success measure.
