# Cloud Run backend deployment

## 1. One-time setup

```powershell
npm install -g firebase-tools
firebase login
gcloud auth login
gcloud config set project project-7a553536-625a-43b4-836
```

## 2. Deploy the backend to Cloud Run

This repo is the Cloud Run backend. The live service is:

`chp-flask-app` in `project-7a553536-625a-43b4-836`

## 3. Set OpenAI secret (required for AI)

```powershell
gcloud run services update chp-flask-app `
  --region us-central1 `
  --project project-7a553536-625a-43b4-836 `
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

## 4. Deploy

```powershell
gcloud run deploy chp-flask-app `
  --source . `
  --project project-7a553536-625a-43b4-836 `
  --region us-central1 `
  --platform managed `
  --allow-unauthenticated
```

## 5. Current live URL

The service currently serves at:

`https://chp-flask-app-5bt6pirytq-uc.a.run.app`

## 6. Local run (optional)

```powershell
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_key_here"
python app.py
```
