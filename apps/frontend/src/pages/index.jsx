import React, { useState } from 'react';
import { Search, Loader2, Database, AlertCircle } from 'lucide-react';

export default function Dashboard() {
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState('raw');
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;

    setStatus('loading');
    setError(null);
    setResult(null);

    try {
      // Create task
      const res = await fetch('/api/v1/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-tenant' // MVP Auth Mock
        },
        body: JSON.stringify({
          url,
          task_type: 'scrape',
          extraction_mode: mode
        })
      });

      if (!res.ok) throw new Error('Failed to create task');

      const task = await res.json();

      // Execute task directly (blocking mode for MVP ease)
      const execRes = await fetch(`/api/v1/tasks/${task.id}/execute`, {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer test-tenant'
        }
      });

      if (!execRes.ok) throw new Error('Task execution failed');
      const data = await execRes.json();

      setResult(data);
      setStatus('success');
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="flex items-center space-x-3 mb-8">
          <Database className="w-8 h-8 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Scraper SaaS Dashboard</h1>
        </header>

        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target URL</label>
              <div className="relative">
                <input
                  type="url"
                  required
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
                <Search className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Extraction Mode</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md bg-white focus:ring-blue-500 focus:border-blue-500"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="raw">Raw HTML</option>
                <option value="content">Clean Article (Trafilatura)</option>
                <option value="schema">AI Smart Schema (GPT-4/Gemini)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={status === 'loading'}
              className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
            >
              {status === 'loading' ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
              ) : 'Start Scraping'}
            </button>
          </div>
        </form>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 flex items-center">
            <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {result && (
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex justify-between items-center">
              <span>Extraction Results</span>
              <span className="text-sm font-normal text-gray-500 bg-gray-100 px-2 py-1 rounded">
                {result.duration_ms}ms • Lane: {result.lane_used}
              </span>
            </h2>
            <div className="bg-gray-900 rounded-md p-4 overflow-x-auto">
              <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                {JSON.stringify(result.extracted_data || result, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
