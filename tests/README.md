# Tests

Plain scripts, no framework. Each connects to the local `boardgames` database,
exercises the app through its own test client, and prints `N passed, M failed`.

    ./venv/bin/python tests/run_all.py          # everything
    ./venv/bin/python tests/photos_test.py      # just one

They need a local Postgres with the same schema as production and the
superuser password in `.env` — they set up and tear down their own fixtures,
all prefixed `ZZ`, so they can be run repeatedly.

These used to live in a scratch directory outside the repo, which is why there
is only one of them: `/tmp` was cleared between sessions and about six hundred
checks went with it. They live here now.
