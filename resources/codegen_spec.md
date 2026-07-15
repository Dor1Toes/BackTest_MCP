QuantForge code generation spec

- Strategy code must include exactly one class inheriting Strategy.
- Required methods: warmup(self) and on_bar(self, symbol, bar, history).
- Forbidden calls: exec, eval, open, __import__, compile.
- Allowed imports are constrained by quantforge_mcp/codegen/allowlist.py.
