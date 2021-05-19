Run
=====================================

1. Install
```console
python -m pip install poetry
poetry install
```

2. Running GUI crawler
```
poetry run HEADLESS=0 EMAIL=[linkedin-email-account] PASSWORD=[linkedin-password] python crawler/crawler.py --profile=[linkedin-profile-slug]
```

3. Running headless crawler
```
poetry run HEADLESS=1 EMAIL=[linkedin-email-account] PASSWORD=[linkedin-password] python crawler/crawler.py --profile=[linkedin-profile-slug]
```
