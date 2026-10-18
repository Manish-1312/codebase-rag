// src/components/CodeViewer.jsx
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python'
import javascript from 'react-syntax-highlighter/dist/esm/languages/hljs/javascript'

SyntaxHighlighter.registerLanguage('python', python)
SyntaxHighlighter.registerLanguage('javascript', javascript)

export default function CodeViewer({ chunk }) {
  if (!chunk) {
    return (
      <div style={{
        width: '300px', background: '#161b22',
        borderLeft: '1px solid #30363d',
        display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexDirection: 'column',
        gap: '8px', color: '#8b949e', fontSize: '13px',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: '24px' }}>📄</div>
        <div>Click a tool call to view code</div>
      </div>
    )
  }

  const input = chunk.input || {}
  const query = input.query || input.file_name || ''

  return (
    <div style={{
      width: '300px', background: '#161b22', flexShrink: 0,
      display: 'flex', flexDirection: 'column',
      borderLeft: '1px solid #30363d', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid #30363d',
        fontSize: '11px', color: '#8b949e', fontWeight: '500',
        textTransform: 'uppercase', letterSpacing: '0.05em',
        display: 'flex', alignItems: 'center', gap: '6px',
      }}>
        <span style={{ color: '#3fb950' }}>⚡</span>
        {chunk.tool}
      </div>

      {/* Query used */}
      <div style={{
        padding: '8px 14px', borderBottom: '1px solid #30363d',
        fontSize: '12px', color: '#58a6ff', fontFamily: 'monospace',
      }}>
        "{query}"
      </div>

      {/* Code */}
      <div style={{ flex: 1, overflow: 'auto', fontSize: '11px' }}>
        <SyntaxHighlighter
          language="python"
          style={atomOneDark}
          customStyle={{
            background: 'transparent',
            padding: '12px',
            margin: 0,
            fontSize: '11px',
            lineHeight: '1.7',
          }}
        >
          {JSON.stringify(input, null, 2)}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}