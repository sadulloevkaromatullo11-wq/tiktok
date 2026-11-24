# Telegram Mini TikTok

Веб-барномаи сабук дар дохили Telegram барои тамошо, шарҳ, лайк ва боркунии видеоҳои кӯтоҳи амудӣ.

## Оғози зуд

Ду терминал:

```powershell
py -3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Сипас дар браузер кушоед: http://127.0.0.1:5173

Бе `BOT_TOKEN` барнома дар реҷаи намоишӣ боз мешавад. Дар профил метавонед байни **Меҳмон** ва **Самандар** гузаред. Лентаи аввал видеоҳои намунавиро нишон медиҳад.

Ё аз решаи лоиҳа: `.\dev.ps1`

## Бот ва Mini App

1. Дар [@BotFather](https://t.me/BotFather) бот созед ва `/newapp` кунед.
2. Файли `.env`-ро аз `.env.example` нусха гиред.
3. `BOT_TOKEN`, `BOT_USERNAME` ва `WEBAPP_URL`-ро пур кунед. `WEBAPP_URL` бояд HTTPS бошад (масалан туннели Cloudflare ё ngrok ба порти `5173`).
4. Серверро аз нав оғоз кунед. Бот тугмаи **Open App**-ро дар меню мегузорад ва ҳангоми лайк ё шарҳ ба соҳиби видео огоҳинома мефиристад.

`initData` дар бекенд бо HMAC-SHA256 («WebAppData») санҷида мешавад ва набояд аз 24 соат кӯҳна бошад.

## Стеки техникӣ

| Қисм | Технология |
| --- | --- |
| Интерфейс | React, Vite, Tailwind CSS, `@twa-dev/sdk` |
| Плеер | HTML5, HLS тавассути `hls.js` |
| API | Python, FastAPI |
| Пойгоҳ | SQLite ба таври пешфарз, PostgreSQL агар `DATABASE_URL` бошад |
| Кэш ва маҳдудияти суръат | Redis агар `REDIS_URL` бошад, вагарна хотира |
| Файлҳо | Диски маҳаллӣ ё S3/R2 (`STORAGE=s3`) |
| Коркард | FFmpeg: 720p/1080p, thumbnail, HLS. Бе FFmpeg файли аслӣ нигоҳ дошта мешавад |

PostgreSQL ва Redis:

```powershell
docker compose up -d
```

```env
DATABASE_URL=postgresql://tiktok:tiktok@localhost:5432/tiktok
REDIS_URL=redis://localhost:6379/0
```

## Гузоштан: Vercel + Railway + Neon

Се хидмат аз як репозиторий. Фронтенд ва бекенд ҷудо мемонанд. Видеоҳои намунавӣ аз интернет меоянд, бинобар ин лента бе диски доимӣ ҳам кушода мешавад. Файли боршудаи корбар дар диски Railway пас аз deploy-и нав мемонад, то он даме ки хидмат аз нав сохта нашавад. Барои нигоҳдории доимӣ баъдтар `STORAGE=s3` лозим аст.

### 1. Neon — пойгоҳ

1. Дар [neon.tech](https://neon.tech) лоиҳа созед.
2. Connection string-и **direct**-ро нусха гиред (суроғаи мизбон бе калимаи `-pooler`).
3. Он бояд бо `postgresql://` сар шавад ва `sslmode=require` дошта бошад.

### 2. Railway — бекенд

1. Репозиторийро ба Railway пайваст кунед. **Root Directory**-ро холӣ монед, то `Dockerfile` аз реша истифода шавад.
2. Домени оммавӣ созед (Settings → Networking → Generate Domain).
3. Тағйирёбандаҳо:

| Ном | Қимат |
| --- | --- |
| `DATABASE_URL` | сатри Neon |
| `BOT_TOKEN` | токени BotFather |
| `BOT_USERNAME` | номи бот бе `@` |
| `BOT_POLLING` | `1` |
| `WEBAPP_URL` | суроғаи Vercel, масалан `https://your-app.vercel.app` |
| `DEV_ALLOW_DEMO` | `0` |

`PUBLIC_URL`-ро холӣ гузоред: Railway худ `RAILWAY_PUBLIC_DOMAIN` медиҳад ва суроғаи `/media` барои фронтенд пурра мешавад. Санҷиш: `https://your-api.up.railway.app/api/health` бояд `"database": "postgres"` гардонад.

### 3. Vercel — фронтенд

1. Ҳамон репозиторийро ба Vercel ворид кунед. Агар Root Directory-ро нагузоред, `vercel.json` аз реша `frontend`-ро месозад. Агар Root Directory = `frontend` бошад, `frontend/vercel.json` кор мекунад.
2. Тағйирёбандаҳои сохтан (Production ва Preview):

| Ном | Қимат |
| --- | --- |
| `VITE_API_URL` | суроғаи Railway, бе `/` дар охир ва бе `/api` |
| `VITE_BOT_USERNAME` | номи бот бе `@` |

3. Пас аз deploy, `WEBAPP_URL`-ро дар Railway ба суроғаи Vercel гузоред ва хидматро як бор аз нав оғоз кунед, то тугмаи **Open App** нав шавад.
4. Дар BotFather ҳамин суроғаи Vercel-ро ба Mini App диҳед.

`BOT_TOKEN` ва `DATABASE_URL` танҳо дар Railway мемонанд. Онҳоро ба Vercel нагузоред.

## Санҷиш

```powershell
cd backend
py -3 -m pytest
```

## Имкониятҳо

- Лентаи амудӣ бо автоплей, пешборкунии 1–2 видео, лайк бо ду пахш, шарҳ, мубодила ба Telegram ва хомӯш кардани овоз
- Боркунӣ то 50 МБ, 5–60 сония, MP4/MOV/WEBM, нишондиҳандаи пешрафт
- Профил: био, истинод, видеоҳо, лайкҳо, обуначиён
- Шарҳ то 300 аломат ва лайк ба шарҳ
- Маҳдудияти суръат барои лайк, шарҳ ва боркунӣ
