from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import httpx

from rss_br.discover import discover_candidates, pick_best_feeds, site_root, validate_feed
from rss_br.http import HttpConfig, make_client
from rss_br.io import write_json, write_scan_csv, write_scan_json
from rss_br.models import ScanMeta, ScanResult, SiteRecord
from rss_br.sources.wikidata import fetch_newspapers
from rss_br.util import make_site_variants, normalize_site_url
from rss_br.report import topic_summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="rss-br", description="Scanner de RSS/Atom/XML para jornais do Brasil.")
    sub = p.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="Busca jornais e descobre RSS/Atom nos sites.")
    scan.add_argument("--source", choices=["wikidata"], default="wikidata", help="Fonte de jornais.")
    scan.add_argument("--max-sites", type=int, default=200, help="Máximo de sites para processar.")
    scan.add_argument("--max-workers", type=int, default=20, help="Concorrência (threads).")
    scan.add_argument("--timeout", type=float, default=15.0, help="Timeout HTTP (segundos).")
    scan.add_argument("--max-candidates", type=int, default=25, help="Máx. candidatos a feed por site.")
    scan.add_argument("--max-feeds", type=int, default=5, help="Máx. feeds válidos salvos por site.")
    scan.add_argument("--out-dir", default="data", help="Diretório de saída (JSON/CSV).")

    rep = sub.add_parser("report", help="Gera relatório por tópico a partir de um scan JSON.")
    rep.add_argument("--input", required=True, help="Arquivo JSON gerado pelo scan.")
    rep.add_argument("--out", default="", help="Arquivo de saída (JSON). Se vazio, imprime.")
    rep.add_argument("--min-count", type=int, default=2, help="Filtra tópicos com menos ocorrências.")

    return p.parse_args(argv)


def _fetch_homepage_html(client: httpx.Client, site_url: str) -> tuple[str | None, int | None, str | None]:
    """
    Busca HTML do site tentando variações http/https.
    """
    variants = make_site_variants(site_url)
    # tenta também a raiz do domínio
    if variants:
        variants = variants + [site_root(variants[0])]

    last_err: str | None = None
    for u in variants:
        try:
            r = client.get(u)
            if r.status_code >= 400:
                last_err = f"http {r.status_code}"
                continue
            ct = (r.headers.get("content-type") or "").lower()
            if "text/html" not in ct and "xml" in ct:
                # o "site_url" pode já apontar para um feed
                return r.text, r.status_code, None
            return r.text, r.status_code, None
        except Exception as e:  # noqa: BLE001 - CLI tool: keep reason
            last_err = f"{type(e).__name__}: {e}"
            continue
    return None, None, last_err


def _scan_one(name: str, site_url: str, source: str, cfg: HttpConfig, max_candidates: int, max_feeds: int) -> SiteRecord:
    site_url = normalize_site_url(site_url)
    rec = SiteRecord(name=name, site_url=site_url, source=source)

    with make_client(cfg) as client:
        html, status, err = _fetch_homepage_html(client, site_url)
        rec.fetched_at = ScanMeta.now_iso()
        rec.status_code = status
        rec.error = err

        cands = discover_candidates(site_root(site_url), html)
        rec.discovered_candidates = cands[:max_candidates]

        feeds = []
        for u in rec.discovered_candidates:
            fr = validate_feed(client, u)
            fr.fetched_at = ScanMeta.now_iso()
            feeds.append(fr)

        rec.feeds = pick_best_feeds(feeds, max_feeds=max_feeds)
        if not rec.feeds and not rec.error:
            rec.error = "no valid feeds found"
        return rec


def _chunked(it: Iterable, n: int) -> list:
    out = []
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = HttpConfig(timeout_s=args.timeout)
    started = ScanMeta.now_iso()

    # fonte (single-thread)
    with make_client(cfg) as client:
        if args.source == "wikidata":
            src_sites = fetch_newspapers(client, max_sites=args.max_sites)
        else:
            raise ValueError(f"unsupported source {args.source}")

    meta = ScanMeta(
        started_at=started,
        source=args.source,
        max_sites=args.max_sites,
        max_workers=args.max_workers,
        timeout_s=args.timeout,
    )

    sites: list[SiteRecord] = []
    out_dir = Path(args.out_dir)
    out_json = out_dir / "feeds.json"
    out_csv = out_dir / "feeds.csv"
    out_topics = out_dir / "topics.json"

    # varredura concorrente por site
    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = [
            ex.submit(_scan_one, s.name, s.site_url, s.source, cfg, args.max_candidates, args.max_feeds)
            for s in src_sites
        ]
        for fut in as_completed(futs):
            sites.append(fut.result())

    meta.finished_at = ScanMeta.now_iso()
    result = ScanResult(meta=meta, sites=sites)

    write_scan_json(out_json, result)
    write_scan_csv(out_csv, result)
    write_json(out_topics, topic_summary(result, min_count=2))

    # saída curta no terminal
    ok_sites = sum(1 for s in sites if s.feeds)
    ok_feeds = sum(len(s.feeds) for s in sites)
    print(f"Sites processados: {len(sites)} | com feed: {ok_sites} | feeds válidos: {ok_feeds}")
    print(f"Arquivos: {out_json} | {out_csv} | {out_topics}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = ScanResult.from_dict(data)
    rep = topic_summary(result, min_count=args.min_count)

    if args.out:
        write_json(Path(args.out), rep)
        print(f"Relatório salvo em: {args.out}")
    else:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "report":
        return cmd_report(args)
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())

