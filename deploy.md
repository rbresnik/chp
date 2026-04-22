# Firebase App Hosting deployment

## 1. One-time setup

```powershell
npm install -g firebase-tools
firebase login
firebase use chpf-2026-rbres
```

## 2. Create the backend in Firebase App Hosting

From the Firebase console:
1. Go to **App Hosting**.
2. Create a backend connected to this source directory/repo.
3. Region: `us-central1`.

App Hosting will use `apphosting.yaml` in this folder.

App Hosting builds the app with Cloud Build and serves it on Cloud Run.

## 3. Set OpenAI secret (required for AI)

```powershell
firebase apphosting:secrets:set OPENAI_API_KEY
```

## 4. Deploy

Push your code changes. App Hosting deploys from your connected source branch.

If you configured manual deploy in the console, trigger a deploy there after pushing.

## 5. Local run (optional)

```powershell
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_key_here"
python app.py
```
