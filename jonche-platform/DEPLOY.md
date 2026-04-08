# Deploying to PythonAnywhere

## One-time setup

### 1. Upload the repo

```bash
# On your local machine:
git init
git add .
git commit -m "Initial Jonche Platform"
git remote add origin https://github.com/yourusername/jonche-platform.git
git push -u origin main
```

### 2. Clone on PythonAnywhere

Open a PythonAnywhere **Bash console** and run:

```bash
git clone https://github.com/yourusername/jonche-platform.git
cd jonche-platform
cp .env.example .env
# Edit .env with your values:
nano .env
```

### 3. Install dependencies

```bash
cd ~/jonche-platform/apps/web && pip install -r requirements.txt --user
cd ~/jonche-platform/apps/api && pip install -r requirements.txt --user
```

### 4. Configure Web Apps

Go to **Web** tab → **Add a new web app** → **Manual configuration** → **Python 3.10**

#### Web App (Dashboard)
- **Source code:** `/home/yourusername/jonche-platform/apps/web`
- **WSGI file:** Edit to contain:

```python
import sys, os
sys.path.insert(0, '/home/yourusername/jonche-platform/apps/web')
from dotenv import load_dotenv
load_dotenv('/home/yourusername/jonche-platform/.env')
from app import app as application
```

- **Static files:**
  - URL: `/static/`
  - Directory: `/home/yourusername/jonche-platform/apps/web/static`

#### API App (Free tier: use same web app with /api prefix)

On the **free tier**, mount the API under the same web app by updating the WSGI:

```python
import sys, os
sys.path.insert(0, '/home/yourusername/jonche-platform/apps/web')
sys.path.insert(0, '/home/yourusername/jonche-platform/apps/api')
from dotenv import load_dotenv
load_dotenv('/home/yourusername/jonche-platform/.env')

from apps.web.app import app as web_app
from apps.api.app import app as api_app

# Mount API under /api
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

application = DispatcherMiddleware(web_app, {'/api': api_app})
```

### 5. Reload & Go Live

Click **Reload** on the Web tab.

Your platform is live at: `https://yourusername.pythonanywhere.com`

---

## Updating

```bash
# SSH into PythonAnywhere console:
cd ~/jonche-platform
git pull origin main
# Then click Reload in the Web tab
```

## Custom Domain (Hacker plan, $5/month)

1. Upgrade to Hacker plan
2. In Web tab → Add custom domain: `platform.jonche.com`
3. Add CNAME record in your DNS: `platform.jonche.com → yourusername.pythonanywhere.com`
