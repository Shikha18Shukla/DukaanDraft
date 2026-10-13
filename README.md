# DukaanDraft ✨
### Turn product details into content that sells.

**An AI-powered product content studio for small businesses, powered by open-weight AI running locally on your machine.**

<img width="1341" height="640" alt="Screenshot 2026-10-13 214605" src="https://github.com/user-attachments/assets/9ada9cc8-dbdb-478f-abd1-0f11bfa50c27" />



<p align="center">
  <b>Local-first AI · No paid LLM APIs · Built for small sellers</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-Backend-black?logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Ollama-Local%20AI-white?logo=ollama" alt="Ollama">
  <img src="https://img.shields.io/badge/Model-Gemma%203%204B-8A2BE2" alt="Gemma 3 4B">
  <img src="https://img.shields.io/badge/Frontend-Vanilla%20JS-yellow?logo=javascript" alt="JavaScript">
  <img src="https://img.shields.io/badge/License-Check%20Repository-lightgrey" alt="License">
</p>

---

## 💡 What is DukaanDraft?

Small businesses selling through Instagram, WhatsApp, and online marketplaces often spend valuable time writing product descriptions, social media captions, sales messages, and hashtags.

**DukaanDraft turns product information into a complete set of marketing content with one generation request.**

Enter your product details, select your preferred language, and let a locally running AI model create content you can review, copy, and adapt for your business.

Built for independent sellers, clothing resellers, small shops, and entrepreneurs who want a simpler content-creation workflow.

## ✨ Features

- **📸 Three Instagram caption options** — product-led, lifestyle-oriented, and short-and-punchy approaches.
- **🛍️ Product titles** — descriptive titles for identifying and presenting products.
- **💬 WhatsApp sales messages** — ready-to-edit messages for customer outreach.
- **📝 Product descriptions** — structured descriptions based on seller-provided information.
- **🎯 Selling points** — product features expressed clearly for potential customers.
- **#️⃣ Relevant hashtags** — generated and normalized for convenient copying.
- **📦 Marketplace titles** — concise titles for product listings.
- **🌐 Multilingual content** — English, Hindi, and Hinglish.
- **📋 One-click copying** — copy individual sections or the complete content package.
- **🎨 Editorial-inspired UI** — warm ivory backgrounds, burgundy accents, and a responsive product-content workspace.
- **🔒 Local-first inference** — generate content using a local Ollama runtime without a paid LLM API.

## 🧠 Powered by open-weight AI

DukaanDraft uses **Gemma 3 4B through Ollama** for local text generation.

The model is responsible for generating the content, while the application validates requests, builds category-aware prompts, checks structured output, normalizes hashtags, and handles inference errors.

Why use this approach?

- **Control:** Run the model on your own machine.
- **Privacy:** Product details are sent to your configured local Ollama endpoint rather than a hosted LLM API.
- **Cost control:** No per-request charge from a third-party inference API.
- **Flexibility:** Prompts and model configuration can be adapted as the project evolves.
- **Transparency:** You can inspect the application code and understand how content is generated.

Local inference has trade-offs. Performance depends on your hardware, and model-generated content still needs review before publication.

## ⚙️ Tech stack

| Component | Technology |
|---|---|
| Backend | Python + Flask |
| AI runtime | Ollama |
| Model | Gemma 3 4B |
| Frontend | HTML, CSS, JavaScript |
| HTTP client | Python standard library |
| Testing | Python `unittest` |

## 🚀 Getting started

### Prerequisites

Install the following:

- Python 3
- [Ollama](https://ollama.com/)
- Git (optional, for cloning the repository)

You also need sufficient system memory to run Gemma 3 4B locally.

### 1. Clone the repository

```bash
git clone https://github.com/Shikha18Shukla/DukaanDraft.git
cd DukaanDraft
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks virtual-environment activation, consult the Python documentation or use the appropriate activation method for your environment.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Install the model

Make sure Ollama is installed and running. Then execute:

```powershell
ollama pull gemma3:4b
```

If the model is already installed, you can skip downloading it again.

Verify the installation:

```powershell
ollama list
```

### 5. Configure the application

Review `.env.example` and configure the environment variables supported by your version of DukaanDraft.

Typical settings include:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:4b
```

Use the actual variable names documented in `config.py` and `README.md` if they differ. Never commit a private `.env` file.

### 6. Run the application

```powershell
python app.py
```


## 🧪 Running the tests

Run the automated test suite:

```powershell
python -m unittest discover -s tests -v
```

The current development test report recorded **73 passing tests**. Test results may change as the project evolves; run the tests against your current checkout to verify its status.

The automated suite uses mocked Ollama requests where appropriate, so it does not need to run a full model generation for every test.

## 🔄 How it works

1. **Enter product details** — name, category, price, features, audience, and language.
2. **Validate the input** — Flask checks required fields and input limits.
3. **Build the prompt** — the application prepares instructions based on the product category and language.
4. **Generate locally** — Ollama sends the prompt to Gemma 3 4B.
5. **Validate the response** — the application checks the structured output and handles invalid model responses.
6. **Review and copy** — the frontend displays the generated content in separate cards.

## 🔐 Privacy and limitations

DukaanDraft is designed for local-first use.

- Inference requests go to the configured Ollama endpoint.
- The application does not require a paid LLM API.
- The current version does not use a database to persist product information.
- Avoid entering sensitive customer information.
- If you configure a non-local Ollama endpoint, the privacy properties depend on that endpoint.
- Local generation can be slow, particularly on CPU-only systems.
- AI output may occasionally be inaccurate or awkward; review content before using it commercially.

**Local AI does not automatically guarantee perfect privacy, accuracy, or speed.** Those depend on configuration, model behavior, hardware, and how the application is used.

## 🗺️ Roadmap

Potential future improvements:

- [ ] Customer reply drafting using verified product information.
- [ ] Better evaluation of caption quality across product categories.
- [ ] Configurable brand voice and writing style.
- [ ] Additional product-specific prompt templates.
- [ ] Performance improvements for local inference.
- [ ] Feedback from real small-business sellers.

These are planned improvements, not features currently claimed as implemented.

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change.
4. Run the automated tests.
5. Open a pull request with a clear explanation of the change.

For larger features, please open an issue first to discuss the proposed implementation.

## 👩‍💻 Built by

**Shikha Shukla**

DukaanDraft was built as an exploration of practical open-weight AI for small businesses, combining local inference, prompt engineering, structured output validation, and frontend design.

## 🌱 Hacktoberfest Open-Source AI Challenge

This project was developed for the **Hacktoberfest Open-Source AI Challenge — Week 2: Side Hustle**.

The goal is to explore how locally running open-weight AI can support a real small-business workflow without relying on paid LLM inference APIs.

## 📄 License

A license has not been specified here. Check the repository's license file and the relevant dependency and model terms before redistributing or modifying the project under a particular license.

---

<p align="center">
  <b>Built with curiosity, open-weight AI, and a focus on practical tools for small businesses.</b>
</p>
