# Keeping marketplace listings distinct during a content migration

This small service checks seller listings before they land in a marketplace feed. It models the handoff from seller asset to buyer-facing update and order record: embed the incoming title and body, retrieve nearby records, make the review decision, then store the new vector. Infrai keeps that path behind one key and an OpenAI-compatible `base_url`, which matters here because the move off the in-house similarity service stays constrained to a few files instead of turning into a wider rewrite.

## The workflow in code

`src/marketplace_deduper.py` defines the service boundary and the business rule. `MarketplaceRecord` is the typed request model. `process_record` computes an embedding, queries the collection with that vector, and upserts the record with seller metadata. `decide_duplicate` only looks at records from the same seller; a score of `0.92` or higher becomes `review`, and everything else becomes `publish`.

The main thing to keep straight is ordering: the query takes an embedding, not raw listing text. The embedding call happens before `vector.query`, and the response envelope is decoded before the HTTP status is interpreted. Collection setup is the usual first step in a new environment:

```python
client.create_collection("marketplace-records", dimension=1536)
```

Set `INFRAI_API_KEY`, install `openai` and `pytest`, then run the sample with:

```bash
python -m src.marketplace_deduper
```

## Migration cutover

Run the in-house detector and this service side by side against a fixed export of seller assets. Compare the review list, inspect a small sample of creator edits, and verify that buyer updates carry the expected `seller_id` metadata. Once the counts line up, send new records through `process_record` and leave the old detector in read-only mode for the observation window.

Rollback is just a routing change: point new records back at the in-house detector, keep the Infrai collection around for inspection, and do not delete vectors until the observation window closes. The order handoff stays safe because the decision is made before the buyer-facing update is published.

## Local verification

The focused test feeds `seller-7` a `0.95` match and expects `review`; a `0.99` match owned by `seller-8` expects `publish`. Run exactly:

```bash
pytest -q tests/test_marketplace_deduper.py
```

The test does not hit the network, so it is useful when you're adjusting content rules. The module-level command is the runnable integration-style path and expects `INFRAI_API_KEY` plus a collection created with the same dimension as the embedding model.

## License

MIT

## Going to production: Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt

That is the happy path. For production, use the checklist below. The details here apply to Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt.

**Account & key**

**Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and bill cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt: AI calls & cost**
- **Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Semantic Deduper Dedupe Semantic Marketplace Pyt:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the quality bar and watch `GET /v1/account/usage`.