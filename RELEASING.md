# Releasing SafeLang

Releases are built and published by
[`.github/workflows/release.yml`](.github/workflows/release.yml) when a `v*` tag
is pushed. Nothing is uploaded by hand, and no PyPI token is stored in the
repository.

## The distribution name

The bare name `safelang` on PyPI is **already taken** by an unrelated
placeholder package (version 0.0.1, published via `registerit`, pointing at
`safelang.ai`). So this project publishes as:

| | |
| --- | --- |
| Distribution name | `safelang-verifier` |
| Import package | `safelang` |
| Console script | `safelang` |

```bash
pip install safelang-verifier
safelang example.slang
```

If you want the shorter name, PyPI's [PEP 541][pep541] process handles name
claims against abandoned or placeholder packages. That is a request the project
owner has to file; if it is ever granted, changing `name` in `pyproject.toml` is
the only code change needed — the import package and script names already match.

[pep541]: https://peps.python.org/pep-0541/

## One-time setup

Configure PyPI Trusted Publishing so the workflow can upload over OIDC without a
long-lived token:

1. Go to <https://pypi.org/manage/account/publishing/>.
2. Add a pending publisher with:
   * **PyPI project name**: `safelang-verifier`
   * **Owner**: `seanwevans`
   * **Repository name**: `SafeLang`
   * **Workflow name**: `release.yml`
   * **Environment name**: `pypi`
3. In the GitHub repository, create an environment named `pypi`
   (Settings → Environments). Adding required reviewers there gives you a manual
   approval gate before anything is published.

## Cutting a release

1. Bump `__version__` in `safelang/__init__.py`. The packaged version is read
   from that attribute, so it is the single source of truth.
2. Commit the bump and merge it to `main`.
3. Tag and push:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

The workflow refuses to publish if the tag does not match
`safelang.__version__`, so a forgotten bump fails loudly instead of shipping a
mislabelled release.

## Checking a build without publishing

Every pull request runs the `package` job in CI, which builds both
distributions, runs `twine check --strict`, and asserts the wheel still ships
`safelang/runtime.js`. To reproduce locally:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check --strict dist/*
```

`workflow_dispatch` on the release workflow does the same thing without
uploading, which is a useful dry run before tagging.
