# v2.1 Vertex AI Gemini Migration Spike

## Purpose

The current Gemini Developer API / AI Studio API-key path is blocked before item-context verification can run:

- current model id: `gemini-2.5-flash`
- current endpoint family: Gemini Developer API / AI Studio API key
- current endpoint host: `generativelanguage.googleapis.com`
- smoke prompt: `Reply exactly: OK`
- smoke result: HTTP 429 `RESOURCE_EXHAUSTED`
- safe summary: prepayment credits depleted / AI Studio project billing guidance
- item context payload: not used

This means the current blocker is API availability, billing, credits, or quota. It is not reproduced by item context payload shape.

This spike designs a possible Google Cloud / Vertex AI Gemini route without replacing or deleting the current Developer API client.

## Current Repo Client

Current path:

| Area | Current behavior |
|---|---|
| Provider | `gemini_developer_api` |
| Implementation | `scripts/spike_advisor.py::call_gemini()` reused by `llm/advisor_client.py` |
| Endpoint host | `generativelanguage.googleapis.com` |
| Endpoint shape | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
| Auth | API key from `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Default model source | `GEMINI_MODEL`, defaulting to `gemini-3-flash` in code |
| Current observed model | `gemini-2.5-flash` |
| Request generation config | no explicit temperature, max output tokens, or thinking config |
| Retry/backoff | not configured |
| Timeout | 60 seconds |
| Current status | `BLOCKED_HTTP_429` due to prepayment credits / AI Studio billing state |

Keep this path intact. It remains the known working integration shape when its account/quota state is healthy.

## Official Documentation Notes

Google Cloud Gemini model APIs are exposed through the Google Cloud AI Platform service:

- Service name: `aiplatform.googleapis.com`
- REST method for Gemini content generation: `projects.locations.endpoints.generateContent`
- Endpoint shape: `https://{service-endpoint}/v1/{model}:generateContent`
- Authentication can use Application Default Credentials (ADC), gcloud CLI credentials for REST, or service account credentials.
- Local development setup can use `gcloud auth application-default login`.
- Gemini/Agent Platform resources require a Google Cloud project, billing, enabled APIs, IAM permissions, and a supported region/location.
- Official rate-limit docs describe quota dimensions such as requests per minute, tokens per minute, and requests per day; Vertex/Google Cloud quota differs from AI Studio API-key credit state.
- Official thinking docs state Gemini models can use dynamic thinking by default. For 2.5-family models, thinking behavior may affect latency and token usage unless explicitly configured.

Primary references:

- Gemini API troubleshooting: https://ai.google.dev/gemini-api/docs/troubleshooting
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini thinking: https://ai.google.dev/gemini-api/docs/thinking
- Google Cloud authentication for Vertex AI / Agent Platform: https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/authentication
- Google Cloud local environment setup: https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/start/cloud-environment
- Google Cloud Gemini generate content REST method: https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.endpoints/generateContent
- Google Cloud deployments and endpoints: https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations
- Google Cloud client libraries / ADC: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/libraries
- Google Cloud Gemini rate / quota options: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/standard-paygo

## Developer API vs Vertex AI Gemini

| Topic | Gemini Developer API / AI Studio | Vertex AI / Google Cloud Gemini candidate |
|---|---|---|
| Provider name | `gemini_developer_api` | `vertex_ai_gemini` |
| Endpoint host | `generativelanguage.googleapis.com` | `aiplatform.googleapis.com` via supported regional/global service endpoints |
| Resource shape | `models/{model}:generateContent` | `projects/{project}/locations/{location}/endpoints/{model}:generateContent`-style model resource |
| Auth | API key | ADC, gcloud credentials, or service account |
| Billing | AI Studio / Developer API credits and limits | Google Cloud billing account and Vertex/Agent Platform quota |
| Quota | Developer API model/tier limits | Google Cloud project/model/region quota and throughput |
| Local setup | `.env` API key | Google Cloud project, location, ADC or service account |
| Current repo support | implemented | not implemented |
| Migration risk | known shape but currently blocked by credits | new provider, auth, endpoint, and error-normalization work |

## Required Vertex AI Preconditions

T1 must prepare these outside the repo:

1. Confirm a Google Cloud project.
2. Attach or confirm a billing account.
3. Enable the Vertex AI / AI Platform API (`aiplatform.googleapis.com`) if required for the selected route.
4. Decide the region/location.
5. Confirm the target Gemini model is available in that location.
6. Decide authentication:
   - local user ADC with `gcloud auth application-default login`
   - or service account JSON outside the repo
7. Ensure the caller has IAM permissions to call the model endpoint.
8. Check active quotas/rate limits in Google Cloud / AI Studio as appropriate.

Do not put service account JSON, API keys, or billing details in the repo.

## Environment Variables

Use placeholders only:

```text
LLM_PROVIDER=vertex_ai_gemini
GOOGLE_CLOUD_PROJECT=<project-id>
GOOGLE_CLOUD_LOCATION=<region-or-global>
VERTEX_AI_MODEL=<model-id>
GOOGLE_APPLICATION_CREDENTIALS=<optional-local-path-to-service-account-json>
```

Notes:

- `GOOGLE_APPLICATION_CREDENTIALS` is optional if local ADC is already configured.
- The service account JSON path must point outside the repo or to a git-ignored local-only location.
- Do not write actual project IDs, service account paths, keys, or billing details into committed docs.

## Provider Adapter Design

Do not replace `llm/advisor_client.py` directly in v2.1.

Recommended future shape:

```text
llm providers:
- GeminiDeveloperApiProvider
- VertexAiGeminiProvider

common interface:
- generate_advice(prompt, model, timeout, options)
- return text and usage metadata when available
- normalize errors into stable classifications
- never expose secrets
```

Suggested error classifications:

```text
AVAILABLE
BLOCKED_HTTP_429
BLOCKED_QUOTA
AUTH_ERROR
PERMISSION_DENIED
API_KEY_INVALID
MODEL_NOT_FOUND
REGION_NOT_SUPPORTED
OTHER_ERROR
```

This keeps the existing Developer API path stable while allowing Vertex AI as an optional provider once T1 has prepared Google Cloud auth and billing.

## REST vs SDK Options

### Option A - Vertex AI REST Provider

Pros:

- Closer to the current `requests.post` implementation.
- Easier to keep a small provider interface.
- No immediate SDK dependency if auth token acquisition is handled separately.

Cons:

- Must implement ADC token acquisition safely.
- Must construct regional/global endpoint and resource names correctly.
- Must normalize Google Cloud errors manually.

### Option B - Google SDK Provider

Pros:

- Official client libraries support ADC.
- Less custom auth/token handling.
- More future-proof for Google Cloud API changes.

Cons:

- Adds dependency and setup surface.
- Provider implementation differs more from the current REST code.
- Tests may need provider-level fakes/mocks.

Recommendation for v2.2: design the provider abstraction first, then choose REST or SDK based on available repo dependency policy and T1's auth setup. If implementation must stay minimal, REST can mirror the current client, but SDK is safer for ADC handling.

## Safe Vertex AI Smoke Test Design

Do not run this in v2.1. Run only after T1 confirms Google Cloud project, billing, API enablement, region, model, and auth.

Smoke prompt:

```text
Reply exactly: OK
```

Expected success:

```text
OK
```

Classification:

| Classification | Meaning |
|---|---|
| `AVAILABLE` | request succeeded and returned text |
| `BLOCKED_QUOTA` | Google Cloud quota/rate/billing blocked the request |
| `AUTH_ERROR` | ADC/service account credential setup failed |
| `PERMISSION_DENIED` | authenticated but caller lacks IAM permission |
| `MODEL_NOT_FOUND` | model id or resource name is wrong/not available |
| `REGION_NOT_SUPPORTED` | model not available in selected location |
| `OTHER_ERROR` | unclassified error |

Safe command shape for a future local-only script:

```bash
set LLM_PROVIDER=vertex_ai_gemini
set GOOGLE_CLOUD_PROJECT=<project-id>
set GOOGLE_CLOUD_LOCATION=<region-or-global>
set VERTEX_AI_MODEL=<model-id>
uv run python scripts/vertex_ai_gemini_smoke.py --prompt "Reply exactly: OK"
```

If using ADC:

```bash
gcloud auth application-default login
```

If using service account credentials:

```bash
set GOOGLE_APPLICATION_CREDENTIALS=<local-path-outside-repo>
```

The future smoke command must:

- print model id, provider, and classification
- never print API keys, access tokens, service account JSON, billing details, or token log contents
- not use item context payload
- not mark pending item-context verification as PASS

## Pending Item Verification Relationship

A Vertex AI smoke test `AVAILABLE` result is not item-context verification PASS.

If Vertex smoke is available, the next separate step should retry:

1. Focus Band within `survival_context`
2. Quick Claw `speed_order_context`
3. Light Ball `species_stat_item_context`
4. Chilan Berry `chilan_berry_context`

Use the same PASS / PARTIAL / FAIL / BLOCKED criteria already documented in the v1.8/v1.9 handoff docs.

## v2.2 Local Readiness Check Result

Local setup was checked after this spike:

- `gcloud`: `GCLOUD_NOT_INSTALLED`
- project config: not checked because `gcloud` is not installed
- Application Default Credentials: not checked because `gcloud` is not installed
- `aiplatform.googleapis.com`: not checked because `gcloud` is not installed
- local environment variables:
  - `GOOGLE_CLOUD_PROJECT`: unset
  - `GOOGLE_CLOUD_LOCATION`: unset
  - `VERTEX_AI_MODEL`: unset
  - `GOOGLE_GENAI_USE_ENTERPRISE`: unset
  - `GOOGLE_APPLICATION_CREDENTIALS`: unset
- Vertex AI smoke test: `NOT_RUN_SETUP_INCOMPLETE`
- actual Vertex AI response generated: no
- pending item-context verification: not run

Before any Vertex AI smoke call, T1 needs to install Google Cloud CLI, configure the intended project, set up ADC or an external service account credential, enable `aiplatform.googleapis.com`, and provide project/location/model settings through local environment variables or command arguments.

## v2.3 Local Setup Attempt Result

Local setup was attempted after the readiness check:

- Google Cloud CLI install: completed with `Google.CloudSDK` version `572.0.0`
- current shell PATH: not refreshed; open a new PowerShell or use the installed `gcloud.cmd` path directly
- `gcloud init`: needs T1 browser login/account/project selection
- configured project: `gen-lang-client-0167075914`
- ADC: not configured; T1 needs to run `gcloud auth application-default login`
- `aiplatform.googleapis.com` check: blocked until an active gcloud account is selected
- Vertex AI smoke test: `NOT_RUN_SETUP_INCOMPLETE`
- pending item-context verification: not run

Next local setup step: T1 should complete `gcloud init`, complete ADC login, confirm API enablement, and set temporary Vertex AI environment variables before any smoke call.

## v2.4 Vertex AI Smoke Result

After T1 completed local auth/API preparation, one Vertex AI smoke call was attempted with:

- endpoint family: Vertex AI / `aiplatform.googleapis.com`
- project: `gen-lang-client-0167075914`
- location: `global`
- model: `gemini-2.5-flash`
- prompt: `Reply exactly: OK`

Result:

- classification: `OTHER_ERROR`
- response summary: HTTP 417 `Expectation Failed`
- actual response generated: no
- additional Vertex AI calls: no
- Developer API key path / `generativelanguage.googleapis.com`: not used
- pending item-context verification: not run and not PASS

The Vertex AI path reached the API call stage, but it is not yet `AVAILABLE`.

## Proposed Post-Readiness Path

Recommended next implementation candidate:

```text
v2.3 Optional LLM Provider Adapter Design/Implementation
```

Scope:

- introduce a provider interface without changing payload content
- keep current `GeminiDeveloperApiProvider`
- add a disabled-by-default `VertexAiGeminiProvider`
- add safe smoke-test command behind explicit provider env
- add tests with mocked providers and no network calls

Out of scope for that follow-up unless separately approved:

- pending item-context actual Gemini PASS
- automatic provider fallback
- storing credentials
- changing default provider
- changing prompt or payload filtering

## Out of Scope for v2.1

- actual Vertex AI call
- pending item-context verification retry
- new item implementation
- provider code implementation
- existing Developer API client deletion
- API key path removal
- payload filtering changes
- prompt hardening
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` changes
- legal fixture changes
- fixture changes
- UI or sample additions
- threshold, skip, or xfail changes
- logs, `.env`, secrets, API keys, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits
