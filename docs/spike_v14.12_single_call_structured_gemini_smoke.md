# v14.12 single-call structured Gemini smoke

The shell lacked `GEMINI_API_KEY`, but the normal application loader
`scripts.spike_advisor` invokes `config.env_loader.load_dotenv(override=True)`.
Application runtime and a fresh runtime subprocess both reported availability.
The `config/.env` candidate existed; its contents were not inspected.

After compile and 41 structured offline tests passed, exactly one production
structured call ran. It ended as sanitized `response_validation_failed`; no
move or slot was validated or displayed. Usage was input 452, output 41,
cached 0, model `gemini-2.5-flash`; retry and fallback were both zero.

No raw request, response, secret, traceback, or protected log content was
exposed. No decoder defect was proven, so no production fix or second call was
made. A sanitized offline semantic-failure regression was added.

Next: v14.13 provider-boundary stabilization based on the observed sanitized
validation failure category. Legacy replacement remains unauthorized.
