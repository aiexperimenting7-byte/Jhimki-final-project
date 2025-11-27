# Jhimki Working

A chat application built with Python backend (FastAPI) and React frontend, deployed on Vercel.

## Prerequisites

- **Python 3.8+**: Download from [python.org](https://www.python.org/downloads/)
- **pip**: Python package installer (included with Python)
- **Node.js & npm**: Download from [nodejs.org](https://nodejs.org/)
- **Vercel CLI** (optional): For deployment

## Setup Instructions

### 1. Python Virtual Environment

Create a virtual environment to isolate project dependencies:

```powershell
# Create virtual environment
python -m venv venv
```

### 2. Activate Virtual Environment

Activate the virtual environment before installing dependencies:

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Python Dependencies

With the virtual environment activated, install the required Python packages:

```powershell
pip install -r requirements.txt
```

### 4. Install Node Dependencies

Install the frontend dependencies:

```powershell
npm install
```

## Running the Application

### Backend (Python API)

```powershell
# Make sure virtual environment is activated
python api/index.py
```

### Frontend (React)

```powershell
npm run dev
```

## Deployment

This project is configured for deployment on Vercel:

1. Install Vercel CLI:
   ```powershell
   npm install -g vercel
   ```

2. Deploy:
   ```powershell
   vercel
   ```

The `vercel.json` configuration file handles both the Python API and React frontend deployment.

## Project Structure

```
├── api/                    # Python backend
│   ├── index.py           # Main API entry point
│   ├── bot_service.py     # Bot service logic
│   └── ...
├── chat-app/              # React frontend source
│   └── src/
├── requirements.txt       # Python dependencies
├── package.json          # Node dependencies
└── vercel.json           # Vercel deployment config
```

## Troubleshooting

- **Virtual environment activation issues**: If you get a script execution error on Windows, run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- **Missing dependencies**: Ensure both `pip install -r requirements.txt` and `npm install` complete successfully

## Environment Variables

Check `ENV_SETUP.md` for environment variable configuration details.
