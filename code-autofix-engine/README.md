# 🚀 TryCatchMe — AI-Powered Autonomous Code Debugger

TryCatchMe is a full-stack AI debugging environment featuring a self-healing code repair engine, automated logical detection, AST-based transformations, LLM-powered fallback mechanisms, and a modern interactive IDE.

It acts like a fully autonomous **AI software engineer** that finds bugs, fixes them, tests the code, merges patches safely, and returns the corrected version — all while showing you every change that was made.

---

## 🌟 Key Features

### 🔍 Autonomous Debugging Engine
- Multi-iteration repair loop (AST → patches → SSR → LLM fallback)
- Forced LLM fix when the engine detects semantic bugs
- Dead-iteration guard (prevents infinite “no-change” cycles)
- Change logging via diff tracking
- High-accuracy merge strategy that preserves the original file layout

### 🧪 Safe Python Execution Sandbox
- Isolated subprocess runner  
- CPU time limits, memory limits  
- No filesystem access  
- Captures stdout + stderr

### 🧠 Semantic Logic Detector
Instant detection of common logical failure patterns:
- Preorder / Inorder / Postorder traversal bugs  
- Fibonacci memoization bug (`memo[0]` issue)  
- Binary Search pointer / mid calculation errors  
- Silent logic mismatches & incorrect control flow  

Triggers instant LLM repair (Iteration 0 Fix).

### 🪄 Patch Viewer
Full visibility into:
- Added lines  
- Removed lines  
- Iteration number  
- Reason for change  
- Fix method (AST, LLM, Forced LLM)

### 💻 Modern Code Editor
- Monaco-based editor  
- Light / Dark themes  
- File upload support  
- Live output terminal  
- Spinner + animated repair messages  

---

# 🧠 System Architecture

```
Frontend (Next.js 14 + Typescript)
│
├── Code Editor (Monaco)
├── Output Terminal
├── Patch Viewer
└── API Communication
       ↓
Backend (FastAPI)
│
├── /run     — sandbox execution
├── /repair  — AI iterative repair engine
│
└── Iteration Engine
      ├── Semantic Detector
      ├── AST Fixer
      ├── SSR Processor
      ├── LLM Fallback Fixer
      ├── Merge Strategy
      ├── Dynamic Test Runner
      └── Patch Generator
```

---

# ⚙️ Installation
g
## 2️⃣ Install Backend (FastAPI)
```
cd backend
pip install -r requirements.txt
```

Run backend:
```
uvicorn main:app --reload
```

## 3️⃣ Install Frontend (Next.js)
```
cd frontend
npm install
npm run dev
```

Frontend will run at:
```
http://localhost:3000
```

Backend will run at:
```
http://localhost:8000
```

---

# 🧩 API Endpoints

### ▶️ `/run`
Executes Python code safely.

**POST Body**
```json
{
  "code": "print('Hello')"
}
```

---

### 🔧 `/repair`
Runs multi-iteration AI self-healing system.

**POST Body**
```json
{
  "code": "buggy code",
  "prompt": "Fix this",
  "max_iterations": "12"
}
```

---

# 🧠 Iteration Engine Overview

1. **Semantic Pre-check (Iteration 0)**
   - Detects high-confidence logic bugs instantly  
   - Forces LLM repair before the loop begins  

2. **Iteration Loop**
   - Sandbox execution  
   - Error parsing  
   - Logical tester  
   - AST fix attempt  
   - SSR cleaning  
   - LLM fallback  
   - Diff tracking  
   - Validation  

3. **Dead-Iteration Guard**
   - Prevents infinite loops  
   - Forces LLM rewrite if no change detected  

4. **Final Output**
   - Fully fixed code  
   - Full patch list  
   - Full logs  

---

# 📜 License
MIT License. Free to use, modify, and distribute.

---

# 🤝 Contributing
PRs, issues, and feature suggestions are welcome.

---

# ❤️ Acknowledgements
Built with:
- FastAPI  
- Next.js  
- Monaco Editor  
- OpenAI LLMs  
- A lot of debugging & caffeine ☕
