# Teen Job Compass

A local prototype that turns your **AI Job Search Super Prompt** into an AI-assisted job finder for teens ages **14–18** in the **United States**. The form starts with South Bend, Indiana, and lets you choose another city/state or ZIP code.

The complete source code is included. There are no third-party Python packages to install. This is a development prototype for your project, with a reusable AI engine and a small browser interface.

## Start here

1. Install Python 3.10 or newer if needed: <https://www.python.org/downloads/>.
2. Extract the entire ZIP file. Keep the folders together.
3. Open a terminal inside the `teen-job-compass` folder.
4. Run:

   ```sh
   python app.py
   ```

   On Windows, `py app.py` also works if the Python launcher is installed. On macOS/Linux you may need `python3 app.py`.

5. Open <http://127.0.0.1:8000> in your browser.

Without an API key, **Build my search plan** produces tailored search phrases and next steps using ordinary code. **Try example results** shows clearly labeled fictional cards. Neither mode calls an AI service or verifies current vacancies.

Stop the app with Ctrl+C. If port 8000 is busy, run `python app.py --port 8001` and open <http://127.0.0.1:8001>.

## Turn on live AI search

Live search needs an OpenAI API project, an API key with access to the configured model, internet access, and available API billing or credits. API model use and web search can incur usage charges. Check your project's usage controls and current pricing before testing: <https://developers.openai.com/api/docs/pricing>.

1. Copy `.env.example` to `.env` in the project folder. In Windows PowerShell:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   On macOS/Linux:

   ```sh
   cp .env.example .env
   ```

2. Put your key after `OPENAI_API_KEY=` in `.env`. Keep the other settings unless you have a reason to change them:

   ```dotenv
   OPENAI_API_KEY=your_key_goes_here
   OPENAI_MODEL=gpt-5.6-terra
   PORT=8000
   API_TIMEOUT_SECONDS=180
   ```

3. Save the file and restart `python app.py`.
4. The form changes to **Find jobs that fit me**. Enter your age, interests, and general location, then add any optional requirements and start a search.

Keep your real key in `.env` on the server. Do not paste it into chat, put it in the browser code, or include `.env` when you share the project. The app never sends the key to the browser. The key is used only to authorize requests to OpenAI's API.

The configured default is GPT-5.6 Terra, whose current model documentation lists Responses API web search and structured output support. You may choose another available model with both features by changing `OPENAI_MODEL`. Model access and behavior still need to be tested with your own API project.

## What happens during a search

The app validates the three required inputs together: age, interests, and location. Transportation, skills, availability, pay, and travel limits remain unspecified unless you enter them. The first version deliberately supports a narrower audience than the original general-purpose prompt: U.S. teens ages 14–18, looking for paid work.

The AI engine then makes two requests:

1. **Research.** The model receives your original prompt, the app's extra instructions, the current date, and the form data. It uses the web-search tool to look for actual postings, open pages, and inspect official work-rule sources. The code records the search tool's source URLs and explicit page-opening actions.
2. **Organize.** A second model request converts that research into a fixed JSON structure. It has no additional tools. The engine then applies its own checks before returning any cards to the browser.

The original prompt is preserved in `prompts/original_super_prompt.txt`. The adaptation instructions are in `prompts/app_instructions.txt`. The response format is in `schemas/results.json`.

### What the code checks

- Only a specific listing that the AI describes as open and whose exact URL appears in a completed page-opening action can enter the openings sections. A search snippet or general careers page is a lead only.
- Known age, hours, pay, work-arrangement, and travel conflicts are excluded where supported structured values are available. Unknown essential requirements go in **Needs confirmation**.
- Employer age requirements are distinct from general government work rules. Neither one substitutes for the other.
- For a minor to appear in the best-match section, the research must include distinct opened federal and applicable-state government sources. A single federal rule page is not enough. The AI still identifies the applicable state and interprets the rules; this is not an independent legal determination.
- URLs are checked against the search record. Unsupported or unsafe links are removed. Duplicate listings are removed while preserving job identifiers in URLs.
- The combined opening lists contain at most 10 jobs. Leads and immediate next steps are capped at three each, and five reusable search phrases are supplied.
- The app never submits an application, creates an employer account, emails anyone, uploads a resume, or monitors jobs in the background.

**These checks reduce unsupported results; they do not prove that an AI interpreted a page correctly.** Opening a URL is evidence that the search tool attempted to inspect it. It is not independent confirmation of a vacancy, the employer's age policy, or legal eligibility. Review the original employer page and any official work rules before acting.

### Travel limits and sparse results

A city or ZIP code is a general search area. The app does not ask for a home address, collect GPS location, or include a routing service. It cannot reliably calculate a journey from your home. If it cannot establish a strict travel limit from sourced route information, the result needs confirmation. It may return no well-supported matches; the prompt explicitly prohibits padding the list or silently relaxing your requirements.

## Files you can change

| File | Purpose |
| --- | --- |
| `app.py` | Local HTTP server, form validation, key configuration, and non-AI fallback |
| `engine.py` | AI research, structured extraction, source checks, and result filtering |
| `prompts/original_super_prompt.txt` | Your supplied prompt, extracted as text |
| `prompts/app_instructions.txt` | Instructions adapting the prompt to this app |
| `schemas/results.json` | Required structure for the AI's extracted results |
| `static/index.html` | The form and page layout |
| `static/styles.css` | Colors, spacing, and responsive layout |
| `static/app.js` | Form submission and safe result rendering |
| `demo.py` | Fictional examples for demonstrating the interface |
| `tests/` | Offline regression tests; these never call a paid API |

## Reuse the AI engine in another app

The browser interface is optional. A Python backend can call the engine directly:

```python
import os
from app import validate_profile
from engine import JobSearchEngine

profile = validate_profile({
    "age": 15,
    "location": "South Bend, Indiana",
    "interests": "coding, engineering, cooking",
    "max_commute_minutes": 10,
    "transportation": "Ride from family",
    "max_hours_per_week": 10,
    "employment_type": "seasonal",
    "skills": "Junior mentor at a coding school",
})

engine = JobSearchEngine(
    api_key=os.environ["OPENAI_API_KEY"],
    model=os.environ.get("OPENAI_MODEL", "gpt-5.6-terra"),
)
results = engine.search(profile)
print(results["best_matches"])
print(results["needs_confirmation"])
```

The example shows the shape of an input; it does not establish that matching jobs exist. The direct-call example reads its key from the environment. The browser app also supports the local `.env` file.

The local HTTP interface offers `GET /api/config`, `GET /api/demo`, and `POST /api/search`. For a POST, get the CSRF token from `/api/config` and include it as `X-CSRF-Token` with `Content-Type: application/json`. The request body is the profile object. Live results use `mode: "live"`; non-AI plans use `mode: "offline"`; fictional examples use `mode: "demo"`.

## Testing

From the project folder:

```sh
python -m unittest discover -s tests -v
```

The tests cover malformed inputs, explicit constraint conflicts, source provenance, uncertain matches, safe links, output limits, and local HTTP boundaries using fixtures and mocked AI responses. A mock proves the application logic for that scenario; it does not prove live model accuracy or access.

No API key was available in the development environment. The live integration was implemented against the official documentation and tested with mock responses, but a paid end-to-end search has not been run. Start with one small live search and check each result against the original sources.

## Data and prototype boundaries

The local server binds to `127.0.0.1` only. It stores no profiles or search history in a database or browser storage. Results stay in the current page unless you choose to download them. When live search is enabled, form details are sent to OpenAI, and search terms may include relevant preferences. Avoid entering names, full addresses, birth dates, financial details, or other information the search does not need.

The API requests use `store: false`; that setting does not by itself mean zero provider retention. Provider data handling is described at <https://developers.openai.com/api/docs/guides/your-data>.

The local app allows one running live search at a time and up to three starts per minute. Those are basic development controls, not account-wide billing limits. Requests are not automatically retried. This is not a production hosting server: before public deployment, add proper hosting, authentication or abuse protection, application-level usage budgets, observability that avoids personal data, and a reviewed process for handling users under 18.

Each live search is limited to 12 web-tool calls, with output-token limits of 12,000 for research and 10,000 for extraction. These are technical bounds, not a guaranteed dollar cost or a promise that every possible source will be checked. Each of the two requests has its own timeout.

### Checks completed for this version

All 45 automated offline tests passed. Browser checks passed for desktop and mobile layouts, the non-AI search plan, fictional examples, disabled demo application links, and JSON downloads. No JavaScript runtime errors or horizontal overflow were observed in those checks. The live AI path was tested with mocked API responses, not a paid live call.

## An experiment for your AI Innovation Challenge

Use a small, checked set of real postings to compare a basic list with the AI's match explanations. Ask a few teens to try both, varying which version they see first. Record time to find a plausible match, whether requirements actually fit, helpfulness of the explanations, and every unsupported claim. Treat this as an exploratory test, and document improvements without inventing success results.

## Official implementation references

- Web search, page actions, and citations: <https://developers.openai.com/api/docs/guides/tools-web-search>
- Structured outputs: <https://developers.openai.com/api/docs/guides/structured-outputs>
- Configured model: <https://developers.openai.com/api/docs/models/gpt-5.6-terra>
- API pricing: <https://developers.openai.com/api/docs/pricing>
- API data controls: <https://developers.openai.com/api/docs/guides/your-data>

The user-provided source is **Job Searching Super Prompt.docx**. The original document was read, not modified.
