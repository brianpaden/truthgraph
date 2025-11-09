/**
 * TruthGraph API - JavaScript Examples (Fetch API)
 *
 * This module demonstrates how to use the TruthGraph verification API
 * with native fetch API for async HTTP requests.
 *
 * Usage:
 *   node verify_claim.js
 *
 * Or in browser:
 *   <script type="module" src="verify_claim.js"></script>
 */

const BASE_URL = 'http://localhost:8000';

/**
 * Check API health status
 */
async function healthCheck() {
  console.log('='.repeat(60));
  console.log('1. Health Check');
  console.log('='.repeat(60));

  const response = await fetch(`${BASE_URL}/health`);
  const health = await response.json();

  console.log(`Status: ${health.status}`);
  console.log(`Version: ${health.version}`);
  console.log('\nServices:');
  for (const [service, status] of Object.entries(health.services)) {
    console.log(`  - ${service}: ${status.status}`);
  }
  console.log();
}

/**
 * Simple synchronous verification
 */
async function simpleVerify() {
  console.log('='.repeat(60));
  console.log('2. Simple Synchronous Verification');
  console.log('='.repeat(60));

  const response = await fetch(`${BASE_URL}/api/v1/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      claim: 'The Earth orbits the Sun',
      max_evidence: 5,
      confidence_threshold: 0.7
    })
  });

  if (response.ok) {
    const result = await response.json();
    console.log(`Verdict: ${result.verdict}`);
    console.log(`Confidence: ${(result.confidence * 100).toFixed(1)}%`);
    console.log(`Evidence count: ${result.evidence.length}`);
    console.log(`Explanation: ${result.explanation}`);
    console.log(`Processing time: ${result.processing_time_ms.toFixed(2)}ms`);
  } else {
    console.log(`Error: ${response.status}`);
    console.log(await response.json());
  }
  console.log();
}

/**
 * Async verification with polling
 */
async function asyncVerifyWithPolling(claimId, claimText) {
  console.log('='.repeat(60));
  console.log('3. Async Verification with Polling');
  console.log('='.repeat(60));

  // Trigger verification
  console.log(`Triggering verification for: ${claimId}`);
  const response = await fetch(`${BASE_URL}/api/v1/claims/${claimId}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      claim_id: claimId,
      claim_text: claimText,
      options: {
        max_evidence_items: 5,
        confidence_threshold: 0.7,
        return_reasoning: true
      }
    })
  });

  const taskData = await response.json();
  const taskId = taskData.task_id;
  console.log(`Task created: ${taskId}`);
  console.log(`Status: ${taskData.status}`);
  console.log();

  // Poll for result with exponential backoff
  console.log('Polling for result...');
  let delay = 1000; // Start with 1 second
  const maxAttempts = 30;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    // Check verdict endpoint
    const verdictResponse = await fetch(`${BASE_URL}/api/v1/verdicts/${claimId}`);

    if (verdictResponse.status === 200) {
      // Verification complete
      const result = await verdictResponse.json();
      console.log(`\n✓ Verification complete (attempt ${attempt})`);
      console.log(`  Claim: ${result.claim_text}`);
      console.log(`  Verdict: ${result.verdict}`);
      console.log(`  Confidence: ${(result.confidence * 100).toFixed(1)}%`);
      console.log(`  Evidence count: ${result.evidence.length}`);
      console.log(`  Processing time: ${result.processing_time_ms}ms`);

      if (result.reasoning) {
        console.log(`  Reasoning: ${result.reasoning}`);
      }

      return result;

    } else if (verdictResponse.status === 202) {
      // Still processing
      console.log(`  Attempt ${attempt}: Still processing... (waiting ${delay/1000}s)`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay = Math.min(delay * 1.5, 10000); // Exponential backoff, cap at 10s

    } else {
      // Error
      console.log(`  Error: ${verdictResponse.status}`);
      console.log(await verdictResponse.json());
      return null;
    }
  }

  console.log(`\n✗ Timeout after ${maxAttempts} attempts`);
  return null;
}

/**
 * Poll task status endpoint
 */
async function taskStatusPolling(taskId) {
  console.log('='.repeat(60));
  console.log('4. Task Status Polling');
  console.log('='.repeat(60));

  const maxAttempts = 10;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const response = await fetch(`${BASE_URL}/api/v1/tasks/${taskId}`);

    if (response.ok) {
      const task = await response.json();
      console.log(`Attempt ${attempt}:`);
      console.log(`  Status: ${task.status}`);
      console.log(`  Progress: ${task.progress_percentage || 0}%`);

      if (task.status === 'completed') {
        console.log(`  ✓ Task completed!`);
        console.log(`  Verdict: ${task.result.verdict}`);
        break;
      } else if (task.status === 'failed') {
        console.log(`  ✗ Task failed: ${task.error}`);
        break;
      }

      await new Promise(resolve => setTimeout(resolve, 2000));
    } else {
      console.log(`Error: ${response.status}`);
      break;
    }
  }
  console.log();
}

/**
 * Generate text embeddings
 */
async function generateEmbeddings() {
  console.log('='.repeat(60));
  console.log('5. Generate Embeddings');
  console.log('='.repeat(60));

  const texts = [
    'The Earth orbits the Sun',
    'Water freezes at 0 degrees Celsius',
    'Python is a programming language'
  ];

  const response = await fetch(`${BASE_URL}/api/v1/embed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texts, batch_size: 32 })
  });

  const data = await response.json();
  console.log(`Generated ${data.count} embeddings`);
  console.log(`Dimension: ${data.dimension}`);
  console.log(`Processing time: ${data.processing_time_ms.toFixed(2)}ms`);

  // Compute cosine similarity between first two
  const [emb1, emb2] = data.embeddings;
  const dotProduct = emb1.reduce((sum, val, i) => sum + val * emb2[i], 0);
  const norm1 = Math.sqrt(emb1.reduce((sum, val) => sum + val * val, 0));
  const norm2 = Math.sqrt(emb2.reduce((sum, val) => sum + val * val, 0));
  const cosSim = dotProduct / (norm1 * norm2);

  console.log(`\nSimilarity between texts 1 and 2: ${cosSim.toFixed(3)}`);
  console.log();
}

/**
 * Search for evidence
 */
async function searchEvidence() {
  console.log('='.repeat(60));
  console.log('6. Search for Evidence');
  console.log('='.repeat(60));

  const response = await fetch(`${BASE_URL}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: 'climate change effects on polar ice caps',
      limit: 5,
      mode: 'hybrid',
      min_similarity: 0.5
    })
  });

  const data = await response.json();
  console.log(`Found ${data.count} results in ${data.query_time_ms.toFixed(2)}ms`);
  console.log(`Mode: ${data.mode}\n`);

  data.results.forEach(result => {
    console.log(`Rank ${result.rank}: Similarity ${result.similarity.toFixed(2)}`);
    console.log(`  Source: ${result.source_url || 'N/A'}`);
    console.log(`  Content: ${result.content.substring(0, 100)}...`);
    console.log();
  });
}

/**
 * Run NLI inference
 */
async function nliInference() {
  console.log('='.repeat(60));
  console.log('7. NLI Inference (Single)');
  console.log('='.repeat(60));

  const response = await fetch(`${BASE_URL}/api/v1/nli`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      premise: 'The Earth revolves around the Sun in an elliptical orbit',
      hypothesis: 'The Earth orbits the Sun'
    })
  });

  const data = await response.json();
  console.log(`Label: ${data.label}`);
  console.log(`Confidence: ${(data.confidence * 100).toFixed(1)}%`);
  console.log(`Processing time: ${data.processing_time_ms.toFixed(2)}ms`);
  console.log('\nAll scores:');
  for (const [label, score] of Object.entries(data.scores)) {
    console.log(`  ${label}: ${(score * 100).toFixed(1)}%`);
  }
  console.log();
}

/**
 * Run batch NLI inference
 */
async function nliBatch() {
  console.log('='.repeat(60));
  console.log('8. NLI Batch Inference');
  console.log('='.repeat(60));

  const pairs = [
    ['The Earth orbits the Sun', 'Earth revolves around Sun'],
    ['Water boils at 100°C', 'Water freezes at 100°C'],
    ['Cats are mammals', 'Cats are animals']
  ];

  const response = await fetch(`${BASE_URL}/api/v1/nli/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pairs, batch_size: 8 })
  });

  const data = await response.json();
  console.log(`Processed ${data.count} pairs`);
  console.log(`Total time: ${data.total_processing_time_ms.toFixed(2)}ms\n`);

  data.results.forEach((result, i) => {
    const [premise, hypothesis] = pairs[i];
    console.log(`${i+1}. Hypothesis: ${hypothesis}`);
    console.log(`   Premise: ${premise}`);
    console.log(`   Label: ${result.label} (${(result.confidence * 100).toFixed(1)}%)`);
    console.log();
  });
}

/**
 * Get rate limit statistics
 */
async function rateLimitStats() {
  console.log('='.repeat(60));
  console.log('9. Rate Limit Statistics');
  console.log('='.repeat(60));

  const response = await fetch(`${BASE_URL}/rate-limit-stats`);
  const data = await response.json();

  const stats = data.rate_limit_statistics || {};
  console.log(`Total violations: ${stats.total_violations || 0}`);
  console.log(`Total requests: ${stats.total_requests || 0}`);

  console.log('\nEndpoint violations:');
  const violations = stats.endpoint_violations || {};
  for (const [endpoint, count] of Object.entries(violations)) {
    if (count > 0) {
      console.log(`  ${endpoint}: ${count}`);
    }
  }
  console.log();
}

/**
 * Main function - run all examples
 */
async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('TruthGraph API - JavaScript Examples');
  console.log('='.repeat(60) + '\n');

  try {
    // 1. Health check
    await healthCheck();

    // 2. Simple synchronous verification
    await simpleVerify();

    // 3. Async verification with polling
    const claimId = `claim_${Date.now()}`;
    await asyncVerifyWithPolling(
      claimId,
      'The Earth is approximately 4.54 billion years old'
    );

    // 4. Generate embeddings
    await generateEmbeddings();

    // 5. Search evidence
    await searchEvidence();

    // 6. NLI inference
    await nliInference();

    // 7. NLI batch
    await nliBatch();

    // 8. Rate limit stats
    await rateLimitStats();

    console.log('='.repeat(60));
    console.log('All examples completed successfully!');
    console.log('='.repeat(60));

  } catch (error) {
    console.log(`\n✗ Error: ${error.message}`);
    console.error(error);
  }
}

// Run if executed directly (Node.js)
if (typeof require !== 'undefined' && require.main === module) {
  main();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    healthCheck,
    simpleVerify,
    asyncVerifyWithPolling,
    taskStatusPolling,
    generateEmbeddings,
    searchEvidence,
    nliInference,
    nliBatch,
    rateLimitStats
  };
}
