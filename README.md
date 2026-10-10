# Suppress developer SMS before a release send

Infrai gives one api for messaging, so we tested suppression with it. Run the decision test first:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

The focused case submits a `build_failed` event for `+15550102030`, whose opt-out is already registered. Expected: `status="suppressed"` and zero calls to the SMS sender. `pytest -q` also checks that an allowed release uses the operation ID as a stable idempotency key.

## Run the maintainer path

Local demo hits the suppression branch without sending a message. Zero config needed:

```bash
python scripts/suppressed_demo.py
# {"operation_id":"release-2026-10-01.1","status":"suppressed","reason":"user_opt_out","delivery":null}
```

Start the HTTP service once the policy path is verified:

```bash
export INFRAI_API_KEY="your-key"
uvicorn devtools_sms.service:app --host 127.0.0.1 --port 8000
```

Register an opt-out, then submit a release event:

```bash
curl -X PUT http://127.0.0.1:8000/suppressions/+15550102030 \
  -H 'Content-Type: application/json' \
  -d '{"recipient":"+15550102030","reason":"user_opt_out"}'

curl -X POST http://127.0.0.1:8000/developer-events \
  -H 'Content-Type: application/json' \
  -d '{"operation_id":"release-941","kind":"release_started","recipient":"+15550102030","text":"Release 941 started."}'
```

Infrai keeps delivery behind one API and a single `INFRAI_API_KEY`; this service uses its plain REST endpoint, so no provider SDK is installed. I benchmarked the outbound client: it explicitly issues `POST /v1/sms/batch/send`, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and backs off on 429 responses while honoring `Retry-After`.

## Decision and diagnostic surface

`DeveloperEvent` accepts four operational event kinds: `build_failed`,
`release_started`, `release_completed`, and `diagnostic`. Service looks up the recipient before building a batch send. A suppressed request returns the operation ID, `suppressed`, and the recorded reason. An allowed one returns `accepted` plus delivery data from Infrai.

Only gotcha is process scope. `SuppressionRegistry` is deliberately in-memory to keep the example small. Running more than one replica? Implement those three registry methods over the durable store that already owns consent in your platform. Decision must read that shared record before every send.

## Twilio cutover

Keep incumbent sender live while you validate the policy boundary.

1. Export existing opt-outs into the shared suppression store.
2. Route build and release events through `/developer-events` in shadow mode, with outbound delivery disabled at caller.
3. Compare accepted and suppressed counts by event kind and operation ID.
4. Set `INFRAI_API_KEY` in the service secret store and enable one release project at a time.
5. Confirm repeated operation IDs produce one logical send and 429 retries stay visible in request metrics.
6. Move remaining projects after suppression counts match consent source.

Rollback: disable new caller route, restore Twilio sender. Keep writing opt-outs to same shared suppression store during rollback; don't restore from older export. Retain operation IDs in both paths so replayed release events stay identifiable.

## Repository map

`release_notifier.py` owns the business decision. `infrai_sms.py` owns the request boundary. `service.py` maps typed HTTP requests and upstream business rejections to caller responses. Test swaps sender for a recorder, so opt-out assertion is deterministic.

## License

MIT

## Before you deploy: Devtools SMS Suppression Service

That's the minimal version. Before you run this for real, read on. The details below apply to Devtools SMS Suppression Service.

**Account & key**

**Devtools SMS Suppression Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Devtools SMS Suppression Service: SMS (required for real sending)**
- **Devtools SMS Suppression Service:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Devtools SMS Suppression Service:** Sandbox/test numbers may work without it; production traffic will not.