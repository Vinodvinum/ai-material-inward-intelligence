'use client'

import { useState } from 'react'

export default function Home() {
  const [fileName, setFileName] = useState('')
  const [status, setStatus] = useState('Ready for inward capture')

  return (
    <main className="shell">
      <nav className="nav">
        <div className="brand">Material Inward Intelligence</div>
        <div className="badge">PoC • Electronics Manufacturing</div>
      </nav>

      <section className="hero">
        <div className="eyebrow">AI-assisted goods inward</div>
        <h1>Turn a supplier label into a trusted material identity.</h1>
        <p>Capture incoming electronics material, extract label data, validate it against master and purchase-order context, and create a traceable digital record.</p>
        <div className="flow">
          {['Capture','Read','Map','Check','Trust','Trace'].map(x => <span className="step" key={x}>{x}</span>)}
        </div>
      </section>

      <section className="grid">
        <div className="card">
          <h2>Start material inward</h2>
          <div className="upload">
            <strong>Upload supplier label</strong>
            <div className="notice">Reel, bag or box label image. This public demo uses synthetic data and does not connect to customer systems.</div>
            <input type="file" accept="image/*" onChange={e => { const f=e.target.files?.[0]; setFileName(f?.name ?? ''); setStatus(f ? 'Image captured — API processing not connected in this deployment yet' : 'Ready for inward capture') }} />
            {fileName && <div className="notice"><strong>{fileName}</strong><br/>{status}</div>}
          </div>
          <a className="cta" href="https://github.com/Vinodvinum/ai-material-inward-intelligence">View engineering project</a>
        </div>

        <div className="card">
          <h2>Validation pipeline</h2>
          <div className="metric"><span>OCR / extraction</span><strong>Candidate data</strong></div>
          <div className="metric"><span>Material matching</span><strong>Master data</strong></div>
          <div className="metric"><span>PO validation</span><strong>Business rules</strong></div>
          <div className="metric"><span>Confidence</span><strong>Review routing</strong></div>
          <div className="metric"><span>Identity</span><strong>UID + traceability</strong></div>
          <p className="notice">AI/OCR proposes information; deterministic validation protects manufacturing master data. Ambiguous cases should go to human review rather than being silently accepted.</p>
        </div>
      </section>

      <div className="footer">Independent engineering PoC • Synthetic data • Not Mysoreminds' internal implementation</div>
    </main>
  )
}