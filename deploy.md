# Cloud Run Deploy

This repo is the Cloud Run backend.

- Project: `project-7a553536-625a-43b4-836`
- Service: `chp-flask-app`
- Region: `us-central1`
- Live URL: `https://chp-flask-app-5bt6pirytq-uc.a.run.app`

## Deploy

```powershell
gcloud auth login
gcloud config set project project-7a553536-625a-43b4-836
gcloud run deploy chp-flask-app `
  --source . `
  --project project-7a553536-625a-43b4-836 `
  --region us-central1 `
  --platform managed `
  --allow-unauthenticated
```

## Secret

If the AI features are not showing, verify the secret is attached to the live service:

```powershell
gcloud run services update chp-flask-app `
  --region us-central1 `
  --project project-7a553536-625a-43b4-836 `
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

## Verify

```powershell
curl.exe https://chp-flask-app-5bt6pirytq-uc.a.run.app/version
curl.exe https://chp-flask-app-5bt6pirytq-uc.a.run.app/_healthz
curl.exe https://chp-flask-app-5bt6pirytq-uc.a.run.app/
```

The deployed app should return:
- `/version` with the current revision in `X-App-Revision`
- `/_healthz` with `status: ok`
- `/` with the same incident UI as local
