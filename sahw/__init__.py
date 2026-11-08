"""SAHW — SAH's companion web UI.

A stdlib-only HTTP server over SAH's run logs: a folder of run folders read as a workspace→run tree,
one log followed while it is being appended to, a new run started with the same command line an
operator would type, one more objective or a steer carried into a run that exists, and the static
front that shows all of it. The modules are flat, one concern each: `envfile` reads this box's numbers,
`runs` reads the logs, `liveness` asks the machine whether a pid still names a process, `spawn` starts
a run, `channel` decides how a word reaches one that did not end, `files` reads the filesystem,
`server` answers the HTTP, and `cli` decides what the invocation means and then blocks on
serve_forever. Every decision and its reason live in the docstring of the code that keeps it.
"""
