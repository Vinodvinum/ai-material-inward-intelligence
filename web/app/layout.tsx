import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Material Inward Intelligence',
  description: 'AI-assisted electronics material inward and traceability PoC',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}