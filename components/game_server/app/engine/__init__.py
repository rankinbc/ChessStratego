"""Pure, transport-free rules engine for ChessStratego.

No module in this package may import from FastAPI, Starlette, or anything
websocket-related. Every rule domain lives in its own module so a single
rule can be swapped by editing one small file. See each module's docstring
for the current rule and any documented variants.
"""
