import { useState, useEffect } from 'react'
import ClaimForm from './components/ClaimForm'
import ClaimHistory from './components/ClaimHistory'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleClaimSubmitted = () => {
    // Trigger refresh of claim history
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div className="app">
      <header>
        <div className="container">
          <h1>🔍 TruthGraph v0</h1>
          <p className="tagline">Check facts locally and privately (React)</p>
        </div>
      </header>

      <main className="container">
        <div className="content-grid">
          <ClaimForm apiUrl={API_URL} onSubmitted={handleClaimSubmitted} />
          <ClaimHistory apiUrl={API_URL} refreshKey={refreshKey} />
        </div>
      </main>

      <footer>
        <div className="container">
          <p>TruthGraph v0 • Open Source • Local-First • React Frontend</p>
        </div>
      </footer>
    </div>
  )
}

export default App
