#!/bin/bash
# TruthGraph API - cURL Examples
# Complete walkthrough of the claim verification API

BASE_URL="http://localhost:8000"

echo "========================================="
echo "TruthGraph API - cURL Examples"
echo "========================================="
echo ""

# =========================================
# 1. Health Check
# =========================================
echo "1. Health Check"
echo "   GET /health"
echo ""

curl -s "$BASE_URL/health" | json_pp
echo ""
echo ""

# =========================================
# 2. Simple Synchronous Verification
# =========================================
echo "2. Simple Synchronous Verification"
echo "   POST /api/v1/verify"
echo ""

curl -s -X POST "$BASE_URL/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "The Earth orbits the Sun",
    "max_evidence": 5,
    "confidence_threshold": 0.7
  }' | json_pp

echo ""
echo ""

# =========================================
# 3. Async Verification - Trigger
# =========================================
echo "3. Async Verification - Trigger"
echo "   POST /api/v1/claims/{claim_id}/verify"
echo ""

CLAIM_ID="claim_$(date +%s)"
echo "   Using claim_id: $CLAIM_ID"
echo ""

RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/claims/$CLAIM_ID/verify" \
  -H "Content-Type: application/json" \
  -d "{
    \"claim_id\": \"$CLAIM_ID\",
    \"claim_text\": \"The Earth is approximately 4.54 billion years old\",
    \"options\": {
      \"max_evidence_items\": 5,
      \"confidence_threshold\": 0.7,
      \"return_reasoning\": true
    }
  }")

echo "$RESPONSE" | json_pp

# Extract task_id
TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)".*/\1/')
echo ""
echo "   Task ID: $TASK_ID"
echo ""
echo ""

# =========================================
# 4. Poll Task Status
# =========================================
echo "4. Poll Task Status"
echo "   GET /api/v1/tasks/{task_id}"
echo ""

if [ -n "$TASK_ID" ]; then
  for i in {1..5}; do
    echo "   Attempt $i:"
    curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" | json_pp
    echo ""

    # Check if completed
    STATUS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)".*/\1/')
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
      break
    fi

    sleep 2
  done
else
  echo "   Skipped: No task_id available"
fi

echo ""
echo ""

# =========================================
# 5. Get Verdict
# =========================================
echo "5. Get Verdict"
echo "   GET /api/v1/verdicts/{claim_id}"
echo ""

if [ -n "$CLAIM_ID" ]; then
  # Wait a bit for processing
  sleep 3

  curl -s "$BASE_URL/api/v1/verdicts/$CLAIM_ID" | json_pp
else
  echo "   Skipped: No claim_id available"
fi

echo ""
echo ""

# =========================================
# 6. Generate Embeddings
# =========================================
echo "6. Generate Embeddings"
echo "   POST /api/v1/embed"
echo ""

curl -s -X POST "$BASE_URL/api/v1/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "The Earth orbits the Sun",
      "Water freezes at 0 degrees Celsius"
    ],
    "batch_size": 32
  }' | json_pp | head -20

echo "   ... (truncated)"
echo ""
echo ""

# =========================================
# 7. Search for Evidence
# =========================================
echo "7. Search for Evidence"
echo "   POST /api/v1/search"
echo ""

curl -s -X POST "$BASE_URL/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change effects on polar ice",
    "limit": 5,
    "mode": "hybrid",
    "min_similarity": 0.5
  }' | json_pp

echo ""
echo ""

# =========================================
# 8. NLI Single Inference
# =========================================
echo "8. NLI Single Inference"
echo "   POST /api/v1/nli"
echo ""

curl -s -X POST "$BASE_URL/api/v1/nli" \
  -H "Content-Type: application/json" \
  -d '{
    "premise": "The Earth revolves around the Sun in an elliptical orbit",
    "hypothesis": "The Earth orbits the Sun"
  }' | json_pp

echo ""
echo ""

# =========================================
# 9. NLI Batch Inference
# =========================================
echo "9. NLI Batch Inference"
echo "   POST /api/v1/nli/batch"
echo ""

curl -s -X POST "$BASE_URL/api/v1/nli/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "pairs": [
      ["The Earth orbits the Sun", "Earth revolves around Sun"],
      ["Water boils at 100°C", "Water freezes at 100°C"],
      ["Cats are mammals", "Cats are animals"]
    ],
    "batch_size": 8
  }' | json_pp

echo ""
echo ""

# =========================================
# 10. Rate Limit Statistics
# =========================================
echo "10. Rate Limit Statistics"
echo "    GET /rate-limit-stats"
echo ""

curl -s "$BASE_URL/rate-limit-stats" | json_pp

echo ""
echo ""
echo "========================================="
echo "Examples Complete!"
echo "========================================="
