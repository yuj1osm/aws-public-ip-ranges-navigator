---
name: ip-ranges-format
description: The structure of the AWS public IP ranges document (ip-ranges.json) — top-level keys and per-entry fields — used when reading or changing the parser, models, or fetcher.
---

# AWS `ip-ranges.json` format reference

Authoritative source URL:
`https://ip-ranges.amazonaws.com/ip-ranges.json`

The Navigator's core (`src/aws_ip_navigator/parser.py`,
`models.py`, `fetcher.py`) depends on this format. Consult this reference
before changing field names or the parsing structure. When in doubt, verify
against AWS official documentation (the `aws-docs` MCP server, if enabled)
rather than guessing.

## Top-level structure

The document is a single JSON object with these top-level keys:

| Key               | Type    | Meaning                                              |
|-------------------|---------|------------------------------------------------------|
| `syncToken`       | string  | Publish timestamp as a Unix epoch (freshness marker) |
| `createDate`      | string  | Publish time, `YYYY-MM-DD-HH-mm-ss` (UTC)            |
| `prefixes`        | array   | IPv4 entries                                         |
| `ipv6_prefixes`   | array   | IPv6 entries                                         |

The current parser reads only `prefixes` (IPv4). IPv6 support would read
`ipv6_prefixes`, whose entries use `ipv6_prefix` instead of `ip_prefix`.

## Per-entry fields

Each object in `prefixes`:

| Field                  | Example             | Notes                                  |
|------------------------|---------------------|----------------------------------------|
| `ip_prefix`            | `52.94.0.0/22`      | CIDR block (IPv4)                       |
| `region`               | `ap-northeast-1`    | Region code; may be `GLOBAL`           |
| `service`              | `EC2`               | Service; `AMAZON` is the superset      |
| `network_border_group` | `ap-northeast-1`    | Network border group (not yet used)    |

Each object in `ipv6_prefixes` is the same, except the CIDR field is
`ipv6_prefix` (e.g. `2600:1f00::/40`).

## How this maps onto the code

In `parser.py`:

- `_PREFIXES_KEY = "prefixes"` → top-level IPv4 collection.
- `_CIDR_FIELD = "ip_prefix"`, `_REGION_FIELD = "region"`,
  `_SERVICE_FIELD = "service"` → the three fields mapped onto
  `IP_Prefix(cidr, region, service)` in `models.py`.
- Entries with a missing, non-string, or blank `ip_prefix` / `region` /
  `service` are skipped; surviving entries keep input order.

## Rules when editing the core

- Do not rename `_PREFIXES_KEY` or the `_*_FIELD` constants to values that
  diverge from the field names above.
- The `service` value `AMAZON` is the union of all services; treat it as data,
  not as a duplicate to filter out.
- `region` can be `GLOBAL` for global services — do not assume every region is
  a standard `xx-xxxx-N` code.
- If you add IPv6 support, read `ipv6_prefixes` with the `ipv6_prefix` CIDR
  field; the `region`/`service` fields are unchanged.
