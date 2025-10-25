import { useState, useEffect } from 'react'

export default function ClaimHistory({ apiUrl, refreshKey }) {
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const fetchClaims = async () => {
      try {
        setLoading(true)
        const response = await fetch(`${apiUrl}/api/v1/claims?limit=10`)

        if (!response.ok) {
          throw new Error(`Failed to fetch claims: ${response.statusText}`)
        }

        const data = await response.json()
        setClaims(data.items)
        setTotal(data.total)
        setError(null)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchClaims()
  }, [apiUrl, refreshKey])

  if (loading) {
    return (
      <section className="card">
        <h2>Recent Claims</h2>
        <p className="loading">Loading claims...</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="card">
        <h2>Recent Claims</h2>
        <div className="alert alert-error">
          <strong>⚠ Error</strong>
          <p>{error}</p>
        </div>
      </section>
    )
  }

  return (
    <section className="card">
      <h2>Recent Claims</h2>

      {claims.length === 0 ? (
        <p className="empty-state">No claims yet. Submit your first claim!</p>
      ) : (
        <>
          <div className="claims-table">
            {claims.map(claim => (
              <div key={claim.id} className="claim-row">
                <div className="claim-header">
                  <span className="claim-id" title={claim.id}>
                    {claim.id.slice(0, 8)}...
                  </span>
                  <span className="claim-date">
                    {new Date(claim.submitted_at).toLocaleString()}
                  </span>
                </div>

                <div className="claim-text">{claim.text}</div>

                {claim.source_url && (
                  <div className="claim-source">
                    <a href={claim.source_url} target="_blank" rel="noopener noreferrer">
                      📎 Source
                    </a>
                  </div>
                )}

                <div className={`claim-verdict verdict-${claim.verdict ? claim.verdict.verdict.toLowerCase() : 'pending'}`}>
                  {claim.verdict
                    ? `${claim.verdict.verdict} (${Math.round(claim.verdict.confidence * 100)}% confidence)`
                    : 'Pending verification'
                  }
                </div>
              </div>
            ))}
          </div>

          {total > claims.length && (
            <div className="pagination">
              <p>Showing {claims.length} of {total} claims</p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
