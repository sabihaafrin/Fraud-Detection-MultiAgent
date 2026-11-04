# SentinelAI — Setup Guide

*Agentic AI Bootcamp — DAIM Lab, University of Hull — 4 November 2026*

Get your machine ready **before the buildathon session** so the day is spent building, not installing. Each team member should run through this on their own laptop.

---

## The stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Required by the bootcamp; what LangGraph runs on |
| IDE | VS Code | Free, cross-platform, great Python + Git support |
| Agent framework | LangGraph (+ LangChain) | Graph-based multi-agent flow with a real human-in-the-loop pause |
| LLM | Google Gemini (free tier via Google AI Studio) | Most generous free API tier, no credit card needed |
| Version control | Git + GitHub | Required deliverable — "push your work to GitHub and share" |

If the team prefers OpenAI or Groq instead of Gemini, only the API-key step and one package name change — the rest is identical.

---

## Step 1 — Python 3.11 or newer

Check what you already have:

```bash
python --version      # or: python3 --version
```

If it's below 3.11, or Python isn't installed, get it from [python.org/downloads](https://www.python.org/downloads/).
**Windows users:** tick *"Add Python to PATH"* in the installer — this avoids the most common beginner headache.

---

## Step 2 — VS Code + extensions

1. Install VS Code: [code.visualstudio.com](https://code.visualstudio.com/)
2. Open VS Code → Extensions panel (the square icon in the sidebar) → install:
   - **Python** (Microsoft) — the main one
   - **Pylance** — autocomplete and type hints
   - **Jupyter** — optional, handy for quick experiments

---

## Step 3 — Project folder + virtual environment

A virtual environment keeps this project's packages isolated so they don't clash with anything else on your machine.

```bash
mkdir sentinelai && cd sentinelai

# create the environment
python -m venv .venv

# activate it
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (PowerShell)
```

When active, your terminal prompt shows `(.venv)`. Activate it every time you open a new terminal for this project.

---

## Step 4 — Install the packages

With the virtual environment active:

```bash
pip install langgraph langchain langchain-google-genai python-dotenv pandas
```

What each is for:
- **langgraph** — the agent graph (nodes, edges, state, the HITL interrupt)
- **langchain** — core building blocks LangGraph sits on
- **langchain-google-genai** — connects LangChain to Gemini *(swap for `langchain-openai` or `langchain-groq` if you change LLM)*
- **python-dotenv** — loads your API key from a file instead of hard-coding it
- **pandas** — for the sample transaction data and behavioural history lookup

Save the list so teammates get the exact same setup:

```bash
pip freeze > requirements.txt
```

Anyone cloning the repo can then run `pip install -r requirements.txt`.

---

## Step 5 — Get an LLM API key (Gemini)

1. Go to [aistudio.google.com](https://aistudio.google.com/) and sign in with a Google account.
2. Click **Get API key** → create one. No credit card required.
3. In your project folder, create a file named `.env`:

   ```
   GOOGLE_API_KEY=your-api-key-here
   ```

4. **Never commit this file.** Create a `.gitignore` in the project folder containing:

   ```
   .venv/
   .env
   __pycache__/
   ```

---

## Step 6 — Git + GitHub

Pushing to GitHub is a required deliverable, so set this up early.

1. Check Git is installed: `git --version`. If not, get it from [git-scm.com](https://git-scm.com/).
2. Create a free account at [github.com](https://github.com/) if you don't have one.
3. **One person** creates a repo (e.g. `sentinelai`) and adds the others as collaborators (repo → Settings → Collaborators).
4. Initialise and push:

   ```bash
   git init
   git add .
   git commit -m "Initial setup"
   git branch -M main
   git remote add origin https://github.com/<user>/sentinelai.git
   git push -u origin main
   ```

Double-check `.env` is **not** in the pushed files before you share the repo.

---

## Step 7 — Verify it all works

The single most useful check: confirm your API key actually talks to the LLM. Create `test.py`:

```python
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
response = llm.invoke("Reply with exactly: setup works")
print(response.content)
```

Run it:

```bash
python test.py
```

If you see **setup works**, your whole chain is ready: Python → virtual environment → packages → API key → LLM. If it errors, the message almost always points at the key (Step 5) or the package install (Step 4).

*(If a model name is rejected, Google AI Studio's "Get API key" page lists the current model names — model labels change occasionally.)*

---

## Agree these as a team before 9am

- **One LLM provider** for everyone (don't mix Gemini and OpenAI across agents for the MVP).
- **Who owns which agent** — Orchestrator, Rules, Behavioural, Adjudicator, HITL. Natural split for a team of up to four.
- **One person owns the GitHub repo** and adds the rest as collaborators.
- **Sample data** — settle on one transaction dataset (a synthetic set like PaySim, or the classic credit-card fraud CSV) so everyone builds against the same thing.

---

## Quick command reference

```bash
# activate environment (do this each session)
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# install from the shared list
pip install -r requirements.txt

# save new packages after installing them
pip freeze > requirements.txt

# push work
git add . && git commit -m "message" && git push
```
