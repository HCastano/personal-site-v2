# personal-site

Copy lives in `content.md` and the shell (head, CSS) in `template.html`; `render.py`
combines them into `index.html`, which is generated and committed — never edit it by hand.

```sh
python3 render.py   # after editing content.md, then commit both files
```

See the docstring at the top of `render.py` for the markdown conventions.
