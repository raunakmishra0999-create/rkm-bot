# 🏆 Tournament Discord Bot

Gaming tournament server ke liye complete Discord bot.

---

## 📁 Files List
| File | Kaam |
|------|------|
| `bot.py` | Main bot code |
| `requirements.txt` | Python libraries |
| `render.yaml` | Render deployment config |
| `runtime.txt` | Python version |
| `.gitignore` | Git ignore rules |

---

## 🚀 Render Par Deploy Karne Ka Tarika

### Step 1 — GitHub par upload karo
1. GitHub mein new repository banao
2. Yeh saari files upload karo

### Step 2 — Render par deploy karo
1. [render.com](https://render.com) par jao
2. **New → Web Service** click karo
3. Apna GitHub repo connect karo
4. Yeh settings lagao:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

### Step 3 — Token add karo
1. Render dashboard → **Environment** tab
2. Add environment variable:
   - **Key:** `DISCORD_TOKEN`
   - **Value:** Apna bot token (Discord Developer Portal se)

### Step 4 — Deploy!
- **Deploy** button dabao
- Logs mein `✅ Bot Online` dikhega

---

## ⚙️ Bot Configuration (bot.py mein change karo)

```python
TAG_CHECK_CHANNEL    = XXXXXXXXXXXXXXX  # Tag check channel ID
REG_CATEGORY         = XXXXXXXXXXXXXXX  # Registration category ID
MATCH_RESULT_CHANNEL = XXXXXXXXXXXXXXX  # Match result channel ID
LEADERBOARD_CHANNEL  = XXXXXXXXXXXXXXX  # Leaderboard channel ID
T2_CATEGORY          = XXXXXXXXXXXXXXX  # T2 category ID
IDP_SOURCE_CHANNEL   = XXXXXXXXXXXXXXX  # IDP source channel ID
```

Channel ID kaise milega: Channel par right-click → **Copy Channel ID**
(Developer Mode ON hona chahiye: Settings → Advanced → Developer Mode ✅)

---

## 📋 Commands

### 👤 Player Commands
| Command | Kaam |
|---------|------|
| `!ping` | Bot latency check |
| `!stats` | Bot statistics |
| `!helpme` | Commands list |

### 🛡️ Admin Commands
| Command | Kaam |
|---------|------|
| `!sendidp 1 ID:123 Pass:456` | IDP channel mein bhejo |
| `!lockch #channel` | Channel lock karo |
| `!unlockch #channel` | Channel unlock karo |
| `!showregs #channel` | Registrations dekho |
| `!clearregs #channel` | Registrations clear karo |
| `!clearresults` | Match results clear karo |
| `!leaderboard` | Manually leaderboard post karo |
| `!result TeamName: Win` | Match result submit karo |

---

## 📝 Tag Check Format
Players ko **#tag-check** mein aise likhna hoga:
```
Team Name: YourTeamName
Players: @Player1 @Player2
UID: 123456, 789012
```

---

## 🔧 Features
- ✅ Tag verification system
- ✅ Auto registration (25 team limit)
- ✅ Auto IDP channel creation
- ✅ Weekly leaderboard (Sunday 7PM)
- ✅ T2 Qualifier role auto-assign
- ✅ Time-based channel auto-open
- ✅ Admin moderation commands
- ✅ Render health check server
- ✅ SQLite database (persistent)
