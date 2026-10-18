// src/components/TopBar.jsx
import { useState } from 'react'

export default function TopBar({ stats, onIngest }) {
  const [repoUrl, setRepoUrl] = useState('')
  const [showInput, setShowInput] = useState(false)

  const handleIngest = () => {
    if (repoUrl.trim()) {
      onIngest(repoUrl.trim())
      setRepoUrl('')
      setShowInput(false)
    }
  }

  return (
    <div style={{
      background: '#161b22',
      borderBottom: '1px solid #30363d',
      padding: '0 16px',
      height: '48px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexShrink: 0,
    }}>
      {/* Left — title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ fontSize: '15px', fontWeight: '600', color: '#e6edf3' }}>
          🔍 Codebase RAG
        </span>
        {stats && (
          <span style={{
            fontSize: '11px', background: '#21262d',
            border: '1px solid #30363d', borderRadius: '20px',
            padding: '2px 8px', color: '#8b949e'
          }}>
            {stats.total_chunks} chunks indexed
          </span>
        )}
      </div>

      {/* Right — ingest button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {showInput && (
          <input
            value={repoUrl}
            onChange={e => setRepoUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleIngest()}
            placeholder="https://github.com/owner/repo"
            style={{
              background: '#0d1117', border: '1px solid #30363d',
              borderRadius: '6px', padding: '4px 10px',
              color: '#e6edf3', fontSize: '12px', width: '280px',
              outline: 'none',
            }}
            autoFocus
          />
        )}
        <button
          onClick={() => showInput ? handleIngest() : setShowInput(true)}
          style={{
            background: '#238636', border: 'none', borderRadius: '6px',
            padding: '5px 12px', color: 'white', fontSize: '12px',
            cursor: 'pointer', fontWeight: '500',
          }}
        >
          {showInput ? 'Index' : '+ Index Repo'}
        </button>
        {showInput && (
          <button
            onClick={() => setShowInput(false)}
            style={{
              background: 'transparent', border: '1px solid #30363d',
              borderRadius: '6px', padding: '5px 10px',
              color: '#8b949e', fontSize: '12px', cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  )
}