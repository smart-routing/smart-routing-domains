# smart-routing-domains

Service domain lists for smart routing, generated from [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community).

[`services.json`](services.json) is the generated application data. Edit [`services.config.json`](services.config.json) to maintain service metadata and source mappings.

## Generate or update

Requires Python 3.12+ and Git on PATH. No Python packages are needed.

```sh
python scripts/update_services.py
```

The script fetches upstream `master` into a temporary checkout, resolves its commit, and generates all services before replacing the output. Failed downloads or parsing leave the existing output intact. Domains are sorted and deduplicated. Identical inputs produce no file change.

Reproduce a particular upstream revision:

```sh
python scripts/update_services.py --revision 88305e9df237d81de4d879db17ba535a54be5e14
```

Use a clean local upstream checkout for an offline run (its HEAD is used; `--revision` does not apply):

```sh
python scripts/update_services.py --checkout /path/to/domain-list-community
python -m unittest discover -s tests
```

Optional `--config PATH` and `--output PATH` select different files.

## Automatic updates

The [GitHub Actions workflow](.github/workflows/update.yml) runs daily at 03:23 UTC (06:23 Moscow time), on relevant configuration/code pushes, and manually through **Actions → Update service domains → Run workflow**. It tests, regenerates, and commits changes on the default branch as `github-actions[bot]`.

Push these files to GitHub and enable Actions. The workflow requests `contents: write`; branch and repository policies must allow the bot to push. Scheduled runs use the default branch and can be delayed. See [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Configuration and parsing

Each configuration entry needs a unique `id`, a `sourceList` matching an upstream filename, and your service metadata. Names, categories, icons, platforms, exclusions, and `verifiedAt` are copied unchanged. Add an entry and regenerate to add a service.

| Source rule | Output |
| --- | --- |
| Bare domain or `domain:` | `domains`, matching the domain and its subdomains |
| `full:` | `exactDomains`, matching only that hostname |
| `include:` | Recursively resolve lists with positive and negative attribute filters |
| `@attribute` | Used internally for include filtering |
| `&list` | Adds the rule to the affiliated list, including lists without a file |
| `keyword:` / `regexp:` | Omitted; distinct type/value pairs counted in `omittedRules` |
| Comments and blank lines | Ignored |

Missing includes, cycles, unknown rules, duplicate IDs, and empty supported domain lists fail generation. Exclusions are application metadata, preserved rather than subtracted from the arrays. Unsupported rules mean the generated lists may have less coverage than upstream.

The top-level `revision` records the upstream commit, and each service's `source` links to its file at that commit. `updatedAt` records output changes. `verifiedAt` remains manual and does not imply automated connectivity testing.

## Sources

- [Upstream repository](https://github.com/v2fly/domain-list-community)
- [Domain source files](https://github.com/v2fly/domain-list-community/tree/master/data)
- [Rule syntax](https://github.com/v2fly/domain-list-community#structure-of-data)
- [OpenAI list](https://github.com/v2fly/domain-list-community/blob/master/data/openai)
- [Gemini list](https://github.com/v2fly/domain-list-community/blob/master/data/google-gemini)
- [Anthropic list](https://github.com/v2fly/domain-list-community/blob/master/data/anthropic)
- [Upstream MIT license](https://github.com/v2fly/domain-list-community/blob/master/LICENSE)

Membership in an upstream list does not establish whether a domain should be proxied or blocked.
