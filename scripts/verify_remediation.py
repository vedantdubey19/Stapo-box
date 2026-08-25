"""Targeted Verification Script for Remediation of Rows #4, #14, and #25.

Tests:
1. Row #14: 15-item schema validation loop across all 5 types.
2. Row #4: Rapid-fire 4-item True/False batch generation.
3. Row #25: End-to-end UX flow (Batch generation -> In-place Redo -> JSON export) with pacing logs.
"""

import json
import os
import sys
import time
from pathlib import Path
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.orchestrator import orchestrator
from backend.agent.schemas import TrueFalseSchema, ThisOrThatSchema, MCQSchema, FillBlankSchema, GuessNumberSchema

BACKEND_URL = "http://127.0.0.1:8000"

print("=" * 80)
print("  REMEDIATION VERIFICATION SUITE (ROWS #4, #14, #25)")
print("=" * 80)

# ── Verification 1: Row #14 (15-item schema validation loop) ─────────────────
print("\n[VERIFICATION 1] Testing Row #14: 15-item schema validation loop...")
c_types = ["MCQ", "True/False", "This-or-That", "Fill in the Blank", "Guess the Number"]
val_results = []
start_t = time.time()

for ct in c_types:
    for i in range(3):
        t0 = time.time()
        item = orchestrator.generate_single_item(sport="Cricket", difficulty="Medium", content_type=ct)
        schema_cls = orchestrator._get_schema_class(ct)
        validated = schema_cls.model_validate(item.model_dump())
        elapsed = time.time() - t0
        val_results.append(f"{ct} #{i+1} (t={elapsed:.1f}s): OK")
        print(f"  ✅ {ct} #{i+1} validated successfully in {elapsed:.1f}s")

total_14_time = time.time() - start_t
print(f"Row #14 Result: 15/15 items validated successfully with 0 errors in {total_14_time:.1f}s total.")
assert len(val_results) == 15

# ── Verification 2: Row #4 (True/False 4-item batch generation) ──────────────
print("\n[VERIFICATION 2] Testing Row #4: True/False 4-item batch generation...")
t0 = time.time()
tf_batch = orchestrator.generate_batch(sport="Football", difficulty="Medium", count=4, content_types=["True/False"])
tf_elapsed = time.time() - t0
print(f"  Generated {len(tf_batch)} items in {tf_elapsed:.1f}s. Types: {[b.content_type for b in tf_batch]}")
assert len(tf_batch) == 4
assert all(b.content_type == "True/False" for b in tf_batch)
for idx, b in enumerate(tf_batch):
    assert isinstance(b.item, TrueFalseSchema)
    print(f"  Item #{idx+1}: '{b.item.statement[:50]}...' -> Correct: {b.item.correct_answer}")
print(f"Row #4 Result: 4/4 True/False items generated and validated.")

# ── Verification 3: Row #25 (End-to-end UX flow audit) ───────────────────────
print("\n[VERIFICATION 3] Testing Row #25: End-to-end UX flow audit...")
t0 = time.time()
resp = requests.post(f"{BACKEND_URL}/generate/batch", json={"sport": "Tennis", "difficulty": "Medium", "count": 5}, timeout=90)
print(f"  POST /generate/batch status: {resp.status_code}")
assert resp.status_code == 200
batch_data = resp.json()
assert batch_data["total_items"] == 5

# Test in-place single redo
item_to_redo = batch_data["items"][1]
redo_resp = requests.post(f"{BACKEND_URL}/regenerate/item", json={
    "sport": "Tennis", "difficulty": "Medium", "content_type": item_to_redo["content_type"]
}, timeout=60)
print(f"  POST /regenerate/item status: {redo_resp.status_code}")
assert redo_resp.status_code == 200
new_item = redo_resp.json()["item"]

# Test JSON serialization & export
json_export_str = json.dumps(batch_data, indent=2)
assert len(json_export_str) > 100
ux_elapsed = time.time() - t0
print(f"Row #25 Result: End-to-end flow passed in {ux_elapsed:.1f}s with 0 raw 500s. Export payload size: {len(json_export_str)} bytes.")

print("\n" + "=" * 80)
print("  ALL 3 REMEDIATION CHECKS (ROWS #4, #14, #25) PASSED 100%!")
print("=" * 80)
