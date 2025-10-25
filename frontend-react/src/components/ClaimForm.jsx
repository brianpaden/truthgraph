import { useState } from 'react'

export default function ClaimForm({ apiUrl, onSubmitted }) {
  const [text, setText] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!text.trim()) {
      setMessage({ type: 'error', text: 'Claim text is required' })
      return
    }

    setLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${apiUrl}/api/v1/claims`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          source_url: sourceUrl.trim() || null
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to submit claim: ${response.statusText}`)
      }

      const claim = await response.json()

      setMessage({
        type: 'success',
        text: `Claim submitted successfully! ID: ${claim.id.slice(0, 8)}...`
      })

      // Reset form
      setText('')
      setSourceUrl('')

      // Notify parent
      if (onSubmitted) {
        onSubmitted()
      }

      // Clear message after 5 seconds
      setTimeout(() => setMessage(null), 5000)
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card">
      <h2>Submit a Claim</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="text">Claim Text *</label>
          <textarea
            id="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows="4"
            required
            placeholder="Enter the claim you want to verify..."
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="source_url">Source URL (optional)</label>
          <input
            type="url"
            id="source_url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="https://example.com/article"
            disabled={loading}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Claim'}
        </button>
      </form>

      {message && (
        <div className={`alert alert-${message.type}`}>
          <strong>{message.type === 'success' ? '✓ Success' : '⚠ Error'}</strong>
          <p>{message.text}</p>
        </div>
      )}
    </section>
  )
}
