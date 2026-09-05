'use client'

import { useState } from 'react'

type Result = {
  uid?: string | null
  ocr_text?: string
  ocr_confidence?: number
  extracted?: Record<string, unknown>
  material_match?: { match?: Record<string, unknown> | null; score?: number; match_basis?: string }
  validation?: { status?: string; overall_confidence?: number; review_required?: boolean; reasons?: string[] }
  persisted?: boolean
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'https://ai-material-inward-intelligence.onrender.com').replace(/\/$/, '')

export default function Home() {
  const [fileName, setFileName] = useState('')
  const [status, setStatus] = useState('Ready for inward capture')
  const [result, setResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleProcess(file: File) {
    setLoading(true); setResult(null); setStatus('Connecting to processing service…')
    try {
      const body = new FormData()
      body.append('image', file)
      body.append('persist', 'true')
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 90000)
      let response: Response
      try {
        response = await fetch(`${API_BASE}/inward/process`, { method: 'POST', body, signal: controller.signal })
      } finally {
        window.clearTimeout(timeout)
      }
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `Processing service returned HTTP ${response.status}`)
      setResult(data)
      setStatus(data.validation?.status === 'VALIDATED' ? 'Material validated successfully' : 'Human review required')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setStatus('Processing timed out. The backend may be waking up; try the upload once more.')
      } else if (error instanceof TypeError) {
        setStatus(`Cannot reach processing service at ${API_BASE}. Check backend/CORS deployment.`)
      } else {
        setStatus(error instanceof Error ? error.message : 'Unable to reach processing API')
      }
    } finally {
      setLoading(false)
    }
  }

  const checks = result?.validation?.reasons || []

  return (
    <main className="shell">
      <nav className="nav"><div className="brand">Material Inward Intelligence</div><div className="badge">PoC • Electronics Manufacturing</div></nav>
      <section className="hero"><div className="eyebrow">AI-assisted goods inward</div><h1>Turn a supplier label into a trusted material identity.</h1><p>Capture incoming electronics material, extract label data, validate it against master and purchase-order context, and create a traceable digital record.</p><div className="flow">{['Capture','Read','Map','Check','Trust','Trace'].map(x => <span className="step" key={x}>{x}</span>)}</div></section>
      <section className="grid">
        <div className="card"><h2>Start material inward</h2><div className="upload"><strong>Upload supplier label</strong><div className="notice">Use a reel, bag or box label image. Public demo data only.</div><input type="file" accept="image/*" disabled={loading} onChange={e => { const f = e.target.files?.[0]; if (f) { setFileName(f.name); handleProcess(f) } }} />{fileName && <div className="notice"><strong>{fileName}</strong><br />{status}</div>}</div><div className="notice">Processing API: <code>{API_BASE}</code></div><a className="cta" href="https://github.com/Vinodvinum/ai-material-inward-intelligence" target="_blank" rel="noreferrer">View engineering project</a></div>
        <div className="card"><h2>Validation pipeline</h2><div className="metric"><span>OCR / extraction</span><strong>Candidate data</strong></div><div className="metric"><span>Material matching</span><strong>Master data</strong></div><div className="metric"><span>PO validation</span><strong>Business rules</strong></div><div className="metric"><span>Confidence</span><strong>Review routing</strong></div><div className="metric"><span>Identity</span><strong>UID + traceability</strong></div>
          {result && <>
            <div className="notice"><strong>Status: {result.validation?.status}</strong><br />OCR confidence: {Math.round((result.ocr_confidence ?? 0) * 100)}%<br />Overall confidence: {Math.round((result.validation?.overall_confidence ?? 0) * 100)}%<br />Material match: {Math.round((result.material_match?.score ?? 0) * 100)}%{result.uid && <><br />UID: {result.uid}</>}</div>
            <div className="notice"><strong>Extracted candidate data</strong><pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(result.extracted || {}, null, 2)}</pre></div>
            <div className="notice"><strong>OCR text</strong><pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{result.ocr_text || '(no OCR text returned)'}</pre></div>
            {checks.length > 0 && <div className="notice"><strong>Review reasons</strong><ul>{checks.map((reason, i) => <li key={i}>{reason}</li>)}</ul></div>}
          </>}
          <p className="notice">OCR proposes information; deterministic validation protects manufacturing master data. Ambiguous cases go to human review.</p>
        </div>
      </section>
      <div className="footer">Independent engineering PoC • Synthetic data • Not Mysoreminds' internal implementation</div>
    </main>
  )
}
