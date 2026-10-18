// src/App.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel.jsx'
import CodeViewer from './components/CodeViewer'

const API = 'https://backend-production-00821.up.railway.app'

export default function App() {
  const [messages, setMessages]       = useState([])
  const [loading, setLoading]         = useState(false)
  const [stats, setStats]             = useState(null)
  const [selectedChunk, setSelectedChunk] = useState(null)

  // Load stats when app opens
  useEffect(() => {
    axios.get(`${API}/stats`)
      .then(r => setStats(r.data))
      .catch(() => setStats(null))
  }, [])

  const sendQuestion = async (question) => {
    // Add user message immediately
    setMessages(prev => [...prev, {
      role: 'user',
      content: question
    }])
    setLoading(true)

    try {
      const response = await axios.post(`${API}/query`, { question })
      const data = response.data

      // Add agent answer
      setMessages(prev => [...prev, {
        role: 'agent',
        content: data.answer,
        steps: data.steps,
      }])

    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'agent',
        content: 'Something went wrong. Is the backend running?',
        steps: [],
      }])
    }

    setLoading(false)
  }

  const ingestRepo = async (repoUrl) => {
    setLoading(true)
    setMessages(prev => [...prev, {
      role: 'system',
      content: `Indexing ${repoUrl}...`
    }])

    try {
      const response = await axios.post(`${API}/ingest`, { repo_url: repoUrl })
      const data = response.data
      setMessages(prev => [...prev, {
        role: 'system',
        content: `✅ Indexed ${data.total_chunks} chunks from ${data.files_scanned} files`
      }])
      // Refresh stats
      const statsRes = await axios.get(`${API}/stats`)
      setStats(statsRes.data)
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'system',
        content: '❌ Failed to index repo. Check the URL.'
      }])
    }

    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <TopBar stats={stats} onIngest={ingestRepo} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <ChatPanel
          messages={messages}
          loading={loading}
          onSend={sendQuestion}
          onSelectChunk={setSelectedChunk}
        />
        <CodeViewer chunk={selectedChunk} />
      </div>
    </div>
  )
}