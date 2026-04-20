# Avatar Web UI Kaise Chalayein? (How to Run)

Yeh naya 3D system FastAPI frontend aur browser ke microphone ka upyog karta hai. Ise chalana bahut aasaan hai.

### Steps:

1. **Terminal/Command Prompt kholiye** aur apne is project ke folder (`/Volumes/Download/chatbot 2`) mein jayein.
2. Niche diya gaya command type karke enter dabayein:
   ```bash
   python ui.py
   ```
   (Aap is command ko directly terminal me run karenge to backend server start ho jayega. Terminal background me 'Uvicorn running on...' dikhayega).

3. Aapka jab server chalu ho jaye, toh apna **Google Chrome** browser kholiye. 
> *Note: Hamesha Chrome browser use karein kyunki usme voice aur speech-to-text sabse achha aur seamlessly chalta hai.*

4. URL search bar me **exact yeh link** type karein aur zaroor yahi link type karein:
   👉 `http://localhost:8000`

   ❌ **DHYAN RAHE:** `http://0.0.0.0:8000` ya file path na kholein, warna Chrome microphone chalne ki permission **block** kar dega. Hamesha `localhost` likhein.

5. Page open hote hi browser aapse Microphone use karne ki permission mangega. Usme **"Allow"** ka button dabayein. 
*(Agar permission ka popup na aaye toh URL bar ke right side mein camera/mic icon par click karein aur permission dein).*

6. Uske baad screen par "Start" button click karein aur aapki Avatar se baatcheet shuru ho jayegi!
