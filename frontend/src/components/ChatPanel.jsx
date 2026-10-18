// src/components/ChatPanel.jsx
import { useState, useRef, useEffect } from 'react'

export default function ChatPanel({ messages, loading, onSend, onSelectChunk }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  // Auto scroll to bottom when new message arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = () => {
    if (input.trim() && !loading) {
      onSend(input.trim())
      setInput('')
    }
  }

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      borderRight: '1px solid #30363d', overflow: 'hidden',
    }}>
      {/* Messages area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px',
        display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#8b949e',
            marginTop: '80px', fontSize: '14px' }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔍</div>
            <div style={{ fontWeight: '500', marginBottom: '6px' }}>
              Ask anything about your codebase
            </div>
            <div style={{ fontSize: '12px' }}>
              Try: "How does backpropagation work?" or "What does the Value class do?"
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <Message
            key={i}
            msg={msg}
            onSelectChunk={onSelectChunk}
          />
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center',
            gap: '8px', color: '#8b949e', fontSize: '13px' }}>
            <ThinkingDots />
            <span>Agent is thinking...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: '1px solid #30363d', padding: '12px',
        display: 'flex', gap: '8px', background: '#161b22',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Ask anything about the codebase... (Enter to send)"
          rows={1}
          style={{
            flex: 1, background: '#0d1117', border: '1px solid #30363d',
            borderRadius: '8px', padding: '8px 12px', color: '#e6edf3',
            fontSize: '13px', resize: 'none', outline: 'none',
            fontFamily: 'inherit', lineHeight: '1.5',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            background: input.trim() && !loading ? '#238636' : '#21262d',
            border: 'none', borderRadius: '8px', padding: '8px 14px',
            color: input.trim() && !loading ? 'white' : '#8b949e',
            cursor: input.trim() && !loading ? 'pointer' : 'default',
            fontSize: '16px', transition: 'all 0.15s',
          }}
        >
          ↑
        </button>
      </div>
    </div>
  )
}

function Message({ msg, onSelectChunk }) {
  if (msg.role === 'system') {
    return (
      <div style={{
        textAlign: 'center', fontSize: '12px', color: '#8b949e',
        background: '#161b22', borderRadius: '6px', padding: '6px 12px',
      }}>
        {msg.content}
      </div>
    )
  }

  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div style={{
          background: '#1f6feb', borderRadius: '12px 12px 2px 12px',
          padding: '8px 14px', fontSize: '13px', maxWidth: '75%',
          color: 'white', lineHeight: '1.6',
        }}>
          {msg.content}
        </div>
      </div>
    )
  }

  // Agent message
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{
        background: '#161b22', border: '1px solid #30363d',
        borderRadius: '2px 12px 12px 12px', padding: '10px 14px',
        fontSize: '13px', lineHeight: '1.7', color: '#e6edf3',
        whiteSpace: 'pre-wrap',
      }}>
        {msg.content}
      </div>

      {/* Steps — show what tools the agent used */}
      {msg.steps && msg.steps.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {msg.steps
            .filter(s => s.type === 'tool_call')
            .map((step, i) => (
              <div
                key={i}
                onClick={() => onSelectChunk(step)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  background: '#0d1117', border: '1px solid #30363d',
                  borderRadius: '6px', padding: '5px 10px',
                  fontSize: '11px', color: '#8b949e', cursor: 'pointer',
                }}
              >
                <span style={{ color: '#3fb950' }}>⚡</span>
                <span>Called <strong style={{ color: '#e6edf3' }}>
                  {step.tool}
                </strong></span>
                <span style={{ color: '#58a6ff', marginLeft: 'auto' }}>
                  view →
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: '5px', height: '5px', borderRadius: '50%',
          background: '#8b949e',
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.2; }
          40% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}