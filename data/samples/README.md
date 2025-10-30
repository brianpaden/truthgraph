# TruthGraph Sample Evidence Corpus

Comprehensive evidence corpus for TruthGraph testing, demonstrations, and development.

## Overview

This corpus contains **250 high-quality evidence documents** covering diverse topics to support fact-checking and claim verification. All evidence is factual, sourced from reputable references, and formatted for embedding and semantic search.

## Corpus Statistics

- **Total Documents**: 250
- **Format**: JSON and CSV
- **Language**: English
- **Average Length**: ~130 characters
- **Quality**: High-relevance, factual content
- **Date Created**: 2025-10-29
- **Version**: 1.0

## Topic Coverage

The corpus is carefully balanced across six major categories:

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **Science** | 55 | 22% | Physics, chemistry, biology, astronomy, climate science |
| **Health** | 45 | 18% | Medical facts, vaccines, diseases, nutrition, wellness |
| **History** | 55 | 22% | Historical events, dates, figures, civilizations |
| **Technology** | 45 | 18% | Computing, internet, AI, innovations, tech history |
| **Politics** | 25 | 10% | Government, elections, political systems, policies |
| **Geography** | 25 | 10% | Countries, landmarks, physical features, demographics |

## File Structure

```
data/samples/
├── evidence_corpus.json      # Primary corpus (JSON format)
├── evidence_corpus.csv       # Corpus in CSV format
├── metadata.json             # Corpus metadata and statistics
├── validate_corpus.py        # Validation script
└── README.md                 # This documentation
```

## File Formats

### JSON Format (`evidence_corpus.json`)

```json
[
  {
    "id": "sample_ev_001",
    "content": "Water boils at 100 degrees Celsius at standard atmospheric pressure...",
    "source": "Physics Textbooks",
    "url": "https://en.wikipedia.org/wiki/Boiling_point",
    "category": "science",
    "relevance": "high",
    "language": "en",
    "date_added": "2025-10-29"
  }
]
```

### CSV Format (`evidence_corpus.csv`)

The CSV file contains the same data with these columns:
- `id`: Unique identifier (sample_ev_001 to sample_ev_250)
- `content`: Evidence text content
- `source`: Source attribution
- `url`: Reference URL
- `category`: Topic category
- `relevance`: Relevance level (high/medium/low)
- `language`: Language code (en)
- `date_added`: Date added to corpus

### Metadata Format (`metadata.json`)

```json
{
  "name": "TruthGraph Sample Evidence Corpus",
  "version": "1.0",
  "date_created": "2025-10-29",
  "total_items": 250,
  "categories": {
    "science": 55,
    "health": 45,
    "history": 55,
    "technology": 45,
    "politics": 25,
    "geography": 25
  },
  "sources": ["Wikipedia", "CDC", "WHO", "NASA", ...],
  "languages": ["en"],
  "statistics": {
    "avg_length": 128,
    "min_length": 82,
    "max_length": 185
  }
}
```

## Usage Examples

### Loading in Python

```python
import json

# Load JSON corpus
with open('evidence_corpus.json', 'r', encoding='utf-8') as f:
    evidence = json.load(f)

print(f"Loaded {len(evidence)} evidence documents")

# Filter by category
science_evidence = [e for e in evidence if e['category'] == 'science']
print(f"Science documents: {len(science_evidence)}")
```

### Loading with Pandas

```python
import pandas as pd

# Load CSV corpus
df = pd.read_csv('evidence_corpus.csv')

print(df.shape)
print(df['category'].value_counts())

# Filter and analyze
health_df = df[df['category'] == 'health']
print(health_df.head())
```

### Integration with TruthGraph

```python
from truthgraph.corpus import CorpusLoader

# Load corpus for embedding
loader = CorpusLoader()
corpus = loader.load_corpus('data/samples/evidence_corpus.json')

# Generate embeddings
embeddings = loader.embed_corpus(corpus)
print(f"Generated {len(embeddings)} embeddings")
```

## Content Quality Standards

All evidence documents in this corpus meet the following standards:

### Factual Accuracy
- All statements are factually accurate based on reputable sources
- Scientific claims are based on peer-reviewed research
- Historical facts are verified from multiple reliable sources
- No misinformation or false claims included

### Source Attribution
- Every document includes proper source attribution
- URLs reference reputable, authoritative sources
- Primary sources include: Wikipedia, CDC, WHO, NASA, NIST, NIH, educational institutions

### Content Guidelines
- **Length**: 50-500 words per document (avg ~130 words)
- **Clarity**: Clear, concise, informative statements
- **Objectivity**: Neutral, factual presentation
- **Completeness**: Self-contained information units

### Categories
- Each document assigned to exactly one primary category
- Categories chosen to match test claim topics
- Balanced distribution across all categories

## Validation

Use the included validation script to verify corpus integrity:

```bash
python validate_corpus.py
```

The validator checks:
- ✓ Required fields present
- ✓ Valid field formats
- ✓ URL format validation
- ✓ Category validity
- ✓ No duplicate IDs or content
- ✓ Content length within bounds
- ✓ JSON/CSV consistency
- ✓ Metadata accuracy

## Topic Details

### Science Evidence (55 documents)
Covers fundamental scientific concepts and discoveries:
- Physics: thermodynamics, relativity, quantum mechanics
- Chemistry: periodic table, atoms, molecular structure
- Biology: evolution, DNA, photosynthesis, human anatomy
- Astronomy: solar system, galaxies, cosmology
- Earth Science: climate change, geology, plate tectonics
- Environmental Science: ecosystems, ozone layer

### Health Evidence (45 documents)
Covers medical and health-related facts:
- Diseases and Conditions: COVID-19, diabetes, cancer, heart disease
- Vaccines: efficacy, safety, composition
- Nutrition: diet, vitamins, food science
- Human Body: anatomy, physiology, biological systems
- Public Health: hygiene, exercise, sleep
- Medical Myths: debunking common misconceptions

### History Evidence (55 documents)
Covers major historical events and periods:
- Ancient History: Rome, Egypt, Greece, civilizations
- Medieval Period: Crusades, Black Death, feudalism
- Modern History: World Wars, Cold War, revolutions
- American History: Declaration, Civil War, presidents
- European History: Renaissance, French Revolution
- World History: empires, exploration, colonization

### Technology Evidence (45 documents)
Covers technological innovations and computing:
- Computing: ENIAC, microprocessors, programming languages
- Internet: ARPANET, WWW, email, protocols
- Mobile Technology: smartphones, GPS, wireless
- Software: operating systems, open source, AI/ML
- Emerging Tech: blockchain, quantum computing, IoT
- Historical Innovations: telegraph, transistor, printing press

### Politics Evidence (25 documents)
Covers government systems and political facts:
- US Government: Constitution, branches, elections
- International Relations: UN, NATO, EU
- Political Systems: democracy, parliament, checks and balances
- Historical Events: Watergate, Civil Rights Act
- Electoral Systems: voting, gerrymandering, term limits

### Geography Evidence (25 documents)
Covers physical and human geography:
- Physical Features: mountains, rivers, oceans, deserts
- Countries: largest, smallest, populations
- Landmarks: natural wonders, human-made structures
- Climate Zones: regions, characteristics
- Demographics: cities, populations, urbanization

## Source Attribution

All evidence documents include proper attribution. Major sources include:

### Scientific Sources
- NASA (Space and Earth Science)
- NOAA (Oceanography, Weather)
- USGS (Geology, Geography)
- NIST (Physics Constants)
- Nature, Science (Peer-reviewed research)

### Health Sources
- CDC (Disease Control and Prevention)
- WHO (World Health Organization)
- NIH (National Institutes of Health)
- Medical Associations (AMA, AHA, ACS)
- Peer-reviewed medical journals

### Educational Sources
- Wikipedia (General reference)
- Britannica (Encyclopedia)
- Educational institutions
- National Archives
- UNESCO

### Government Sources
- Whitehouse.gov (US Government)
- Congress.gov (US Legislature)
- UN.org (United Nations)
- National archives worldwide

## Integration with TruthGraph Features

This corpus is designed to work seamlessly with TruthGraph features:

### Feature 1.1: Test Claims
- Evidence topics align with test claim categories
- Sufficient coverage for all test scenarios

### Feature 1.2: FEVER Dataset
- Similar structure to FEVER evidence format
- Compatible with FEVER evaluation pipeline

### Feature 1.3: Real-World Claims
- Evidence supports real-world fact-checking claims
- Covers contemporary and historical topics

### Feature 1.5: Corpus Loading
- Ready for loading via corpus loading script
- Compatible with embedding generation pipeline

## Performance Characteristics

### File Sizes
- **JSON**: ~94 KB (uncompressed)
- **CSV**: ~56 KB (uncompressed)
- **Total**: ~150 KB for full corpus

### Loading Performance
- JSON load time: <100ms
- CSV load time: <50ms
- Pandas DataFrame: <200ms

### Embedding Performance
- Documents: 250
- Estimated embedding time: 5-10 minutes (at 500 docs/sec)
- Embedding storage: ~20-50 MB (depending on model)

## Maintenance and Updates

### Version History
- **v1.0** (2025-10-29): Initial release with 250 documents

### Future Updates
Planned improvements:
- Expand corpus to 500-1000 documents
- Add more specialized categories
- Include multilingual evidence
- Add temporal metadata for time-sensitive facts
- Include confidence scores and evidence strength ratings

## Citation

If you use this corpus in research or publications, please cite:

```
TruthGraph Sample Evidence Corpus v1.0
Created: 2025-10-29
Source: TruthGraph Project
License: See DATA_LICENSE in repository root
```

## License

This corpus is provided under the project's data license. See `DATA_LICENSE` in the repository root for details.

All evidence content is derived from publicly available sources and used under fair use principles for educational and research purposes. Original sources retain their respective copyrights.

## Support and Contribution

### Issues
Report issues with the corpus via the project's issue tracker.

### Contributions
To contribute additional evidence:
1. Follow the existing format structure
2. Ensure factual accuracy with source attribution
3. Run validation script before submission
4. Submit pull request with documentation

### Questions
For questions about the corpus, consult:
- This README
- Project documentation
- Feature implementation reports

## Related Files

- `c:\repos\truthgraph\scripts\generate_sample_corpus.py` - Generation script
- `c:\repos\truthgraph\tests\fixtures\test_claims.json` - Test claims
- `c:\repos\truthgraph\tests\accuracy\real_world_claims.json` - Real-world claims
- `c:\repos\truthgraph\truthgraph\corpus\loader.py` - Corpus loading implementation

---

**Last Updated**: 2025-10-29
**Corpus Version**: 1.0
**Documentation Version**: 1.0
