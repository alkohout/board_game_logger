# Running Database Query on your own machine

Built and tested, switched **off**. Nothing changes until the environment
variables below are set on the server.

Only Database Query can be routed locally. The Rules Assistant sends ~65,000
tokens of rulebook per question, which needs far more GPU than the SQL step —
leave it on Claude.

## What to expect

Measured on 13 Aug 2026, Claude answers a Database Query in **~15 seconds**
(Opus writes the SQL at low effort, Haiku writes the prose, plus the query).

Estimates for a Ryzen 9 9950X:

| Model | CPU only | With a 24GB GPU |
|---|---|---|
| 8B Q4 | ~20s | 2–3s |
| 14B Q4 | ~35s | 3–5s |
| 32B Q4 | 60–90s | 5–8s |

So on CPU it is slower than Claude; the GPU is what makes it faster. Add
5–30s on the first question after idle while the model loads from disk.

Quality: a 14B model handles straightforward questions and is shakier on the
awkward parts of this data — the free-text `result` column, the 2023 backfill.
Check the "Show SQL" panel when an answer looks surprising.

## Setting it up

On the machine with the GPU:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:14b        # good at SQL for its size
ollama serve                          # listens on 11434
```

Ollama binds to localhost by default. To let the server reach it, prefer a
private network over opening a port — an exposed Ollama has no authentication
and anyone who finds it can use your hardware:

```bash
# Tailscale: both machines join one private network, nothing exposed publicly
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then on the Oracle server, in `.env`:

```
LOCAL_LLM_URL=http://<tailscale-ip>:11434/v1
LOCAL_LLM_MODEL=qwen2.5-coder:14b
LOCAL_LLM_FOR=db_query
# LOCAL_LLM_FALLBACK=false      # optional: fail instead of falling back
# LOCAL_LLM_TIMEOUT=300         # seconds; raise for a slow model on CPU
```

and restart. Unset `LOCAL_LLM_FOR` to go back to Claude.

## How it behaves

- **Falls back to Claude** when the machine is asleep, mid-reboot, still
  loading a model, or returns nothing. A question then costs the usual couple
  of cents instead of failing. Set `LOCAL_LLM_FALLBACK=false` to fail loudly.
- **Costs nothing** when answered locally: billed at zero, and the credit
  guard is skipped, since there is nothing to charge for.
- **The page says which model answered**, so an A/B is visible rather than
  guessed at.
- **Safety is unchanged.** SQL from a local model goes through the same
  validator, the same read-only transaction, the same `bgl_ai` role and the
  same row-level security. A local model returning `DROP TABLE` is refused
  exactly as Claude's would be — there is a test for it.

## Trying it without touching the server

Point a local copy of the app at your local Postgres and at Ollama, and ask
the same questions both ways. No tunnel, nothing exposed, nothing deployed:

```bash
LOCAL_LLM_URL=http://localhost:11434/v1 LOCAL_LLM_FOR=db_query \
  ./.venv/bin/python flask_web_interface.py
```
