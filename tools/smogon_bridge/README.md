# Smogon Calc Bridge

CLI adapter for `@smogon/calc`. It reads a `damage_request_v1` JSON payload from stdin and writes a `damage_response_v1` JSON payload to stdout.

Install once:

```powershell
npm install
```

Run the example:

```powershell
npm test
```

The Python test infrastructure calls this script through `advisor.parity.bridge.call_smogon_calc`.
