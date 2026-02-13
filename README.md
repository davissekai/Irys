# Irys Project
(Will be updated soon)
Digitization app for paper registers.

## Production Architecture

- Frontend: Vercel (`irys-web`)
- Backend API: Render (`api.py`)
- Database: Supabase PostgreSQL

This is the recommended split for phone usage. The app remains available even when your PC is off.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Copy `.env.example` to `.env` and set:
   ```bash
   GLM_OCR_API_KEY=your_key_here
   ```

## Usage

### Extract Table from Image
To extract structured data from a register image:

```bash
python extract_glm.py path/to/image.jpg
```

This will output a JSON file named `image_output.json` in the same directory.

## Deploy (Vercel + Render)

1. Backend on Render:
   - Deploy this repo as a Python web service.
   - Start command: `python api.py`
   - Add backend env vars from `.env.example`.
   - Configure `GLM_OCR_API_KEY` (GLM-only OCR pipeline).
   - Set `FRONTEND_ORIGINS` to your Vercel production URL.
   - Keep `FRONTEND_ORIGIN_REGEX=https://.*\.vercel\.app` to allow Vercel preview deployments.

2. Frontend on Vercel:
   - Root directory: `irys-web`
   - Add frontend env vars from `irys-web/.env.example`.
   - Set `VITE_API_BASE_URL` to your Render backend URL (for example `https://irys-api.onrender.com`).

3. Latency guidance:
   - Put Render + Supabase in the same region.
   - Choose the closest region to your users for Vercel and Render.
   - OCR time usually dominates network latency; cross-platform overhead is typically much smaller than OCR compute time.

## Project Structure
- `extract_glm.py`: Main OCR extraction logic (GLM-only).
- `Project_Irys_Spec.md`: Project specification and design document.
