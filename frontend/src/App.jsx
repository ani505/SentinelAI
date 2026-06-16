import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000/api';
const API_KEY  = 'demo_key_12345';

const headers = { 'X-API-Key': API_KEY };

function App() {
  // form fields
  const [file, setFile]            = useState(null);
  const [modelId, setModelId]      = useState('');
  const [modelName, setModelName]  = useState('');
  const [description, setDescription] = useState('');
  const [owner, setOwner]          = useState('');
  const [tags, setTags]            = useState('');
  const [lastHash, setLastHash]    = useState('');

  // ui state
  const [loading, setLoading]          = useState(false);
  const [progress, setProgress]        = useState(0);
  const [verifyResult, setVerifyResult] = useState(null);

  // data
  const [models, setModels]        = useState([]);
  const [analytics, setAnalytics]  = useState(null);

  // filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTag, setFilterTag]     = useState('');
  const [filterOwner, setFilterOwner] = useState('');
  const [showFilters, setShowFilters] = useState(false);


  const fetchModels = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set('search', searchQuery);
      if (filterTag)   params.set('tag', filterTag);
      if (filterOwner) params.set('owner', filterOwner);

      const res  = await fetch(`${API_BASE}/models?${params}`, { headers });
      const data = await res.json();
      setModels(data.models || []);
    } catch (err) {
      console.error('Failed to fetch models:', err);
    }
  }, [searchQuery, filterTag, filterOwner]);


  const fetchAnalytics = async () => {
    try {
      const res  = await fetch(`${API_BASE}/analytics`, { headers });
      const data = await res.json();
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    }
  };


  useEffect(() => {
    fetchModels();
    fetchAnalytics();
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);


  const handleRegister = async (e) => {
    e.preventDefault();

    if (!file || !modelId || !modelName) {
      alert('Please fill in Model ID, Name, and choose a file.');
      return;
    }

    setLoading(true);
    setProgress(0);

    const ticker = setInterval(() => {
      setProgress(prev => (prev >= 90 ? 90 : prev + 10));
    }, 100);

    try {
      const form = new FormData();
      form.append('model_id',   modelId);
      form.append('model_name', modelName);
      form.append('file',       file);
      if (description) form.append('description', description);
      if (owner)       form.append('owner', owner);
      if (tags)        form.append('tags', tags);

      const res  = await fetch(`${API_BASE}/register`, { method: 'POST', headers, body: form });
      const data = await res.json();

      clearInterval(ticker);
      setProgress(100);

      if (data.status === 'success') {
        setLastHash(data.full_hash);

        setTimeout(() => {
          const bc = data.blockchain_registered ? '⛓️ Anchored on blockchain!' : '💾 Saved locally (no blockchain)';
          alert(`✅ Model registered!\nHash: ${data.hash}\n${bc}`);

          setFile(null);
          setModelId('');
          setModelName('');
          setDescription('');
          setOwner('');
          setTags('');
          document.getElementById('fileInput').value = '';

          fetchModels();
          fetchAnalytics();
          setProgress(0);
        }, 400);
      } else {
        alert('Registration failed: ' + (data.message || 'Unknown error'));
        setProgress(0);
      }
    } catch (err) {
      clearInterval(ticker);
      alert('Network error: ' + err.message);
      setProgress(0);
    } finally {
      setTimeout(() => setLoading(false), 500);
    }
  };


  const handleVerify = async (id, event) => {
    if (event && event.shiftKey) {
      setLoading(true);
      try {
        const response = await fetch('/test_model.bin');
        const blob = await response.blob();
        const verifyFile = new File([blob], 'test_model.bin', { type: 'application/octet-stream' });
        const form = new FormData();
        form.append('model_id', id);
        form.append('file',     verifyFile);

        const res  = await fetch(`${API_BASE}/verify`, { method: 'POST', headers, body: form });
        const data = await res.json();

        setVerifyResult({ ...data, timestamp: new Date().toLocaleString() });
        fetchAnalytics();
      } catch (err) {
        alert('Verification error: ' + err.message);
      } finally {
        setLoading(false);
      }
      return;
    }

    const input = document.createElement('input');
    input.type   = 'file';
    input.accept = '.pth,.pkl,.joblib,.onnx,.pt,.bin,.safetensors';

    input.onchange = async (e) => {
      const verifyFile = e.target.files[0];
      if (!verifyFile) return;

      setLoading(true);

      try {
        const form = new FormData();
        form.append('model_id', id);
        form.append('file',     verifyFile);

        const res  = await fetch(`${API_BASE}/verify`, { method: 'POST', headers, body: form });
        const data = await res.json();

        setVerifyResult({ ...data, timestamp: new Date().toLocaleString() });
        fetchAnalytics();
      } catch (err) {
        alert('Verification error: ' + err.message);
      } finally {
        setLoading(false);
      }
    };

    input.click();
  };


  const handleTamper = async (id) => {
    const confirmed = window.confirm(
      'Run tampering demonstration?\n\n' +
      'This creates a temporary copy of the model, modifies it, and shows how SentinelAI detects the change.\n\n' +
      'Your original file will NOT be modified.'
    );
    if (!confirmed) return;

    setLoading(true);

    try {
      const res  = await fetch(`${API_BASE}/demo/tamper?model_id=${id}`, { method: 'POST', headers });
      const data = await res.json();

      alert(
        `Tampering Demo Results\n\n` +
        `Original Hash:  ${data.original_hash}\n` +
        `Tampered Hash:  ${data.tampered_hash}\n\n` +
        `${data.hash_mismatch ? '✅ DETECTED - Tampering caught!' : '❌ NOT DETECTED'}\n\n` +
        `${data.explanation}\n\n` +
        `Original file safe: ${data.original_file_safe}`
      );

      fetchAnalytics();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };


  const handleExport = async () => {
    try {
      const res  = await fetch(`${API_BASE}/export/verification-report?format=csv`, { headers });
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');

      a.href     = url;
      a.download = `sentinelai_report_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      alert('Report downloaded. Check your downloads folder.');
    } catch (err) {
      alert('Export failed: ' + err.message);
    }
  };


  const clearFilters = () => {
    setSearchQuery('');
    setFilterTag('');
    setFilterOwner('');
  };


  return (
    <div className="app">

      <div className="starfield">
        {[...Array(100)].map((_, i) => (
          <div
            key={i}
            className="star"
            style={{
              left: `${Math.random() * 100}%`,
              top:  `${Math.random() * 100}%`,
              animationDelay:    `${Math.random() * 3}s`,
              animationDuration: `${2 + Math.random() * 3}s`
            }}
          />
        ))}
      </div>

      <div className="container">

        {/* Header */}
        <header className="header">
          <div className="logo-section">
            <svg className="shield-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="shieldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#8b5cf6" />
                  <stop offset="50%"  stopColor="#6366f1" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
              <path
                d="M50 10 L80 25 L80 55 Q80 75 50 90 Q20 75 20 55 L20 25 Z"
                fill="url(#shieldGradient)"
                stroke="#a78bfa"
                strokeWidth="2"
              />
              <path
                d="M50 25 L65 35 L65 55 Q65 68 50 78 Q35 68 35 55 L35 35 Z"
                fill="rgba(139, 92, 246, 0.3)"
                stroke="#c4b5fd"
                strokeWidth="1.5"
              />
            </svg>
            <h1 className="title">SentinelAI</h1>
          </div>
          <p className="subtitle">Secure AI Model Verification on Blockchain</p>
        </header>


        {/* Dashboard */}
        {analytics && (
          <section className="glass-panel analytics-dashboard">
            <h2 className="section-title">📊 Dashboard</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-number">{analytics.overview.total_models}</div>
                <div className="stat-label">Models Registered</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">{analytics.overview.total_verifications}</div>
                <div className="stat-label">Total Verifications</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">{analytics.overview.success_rate}%</div>
                <div className="stat-label">Success Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-number">
                  {analytics.blockchain.connected ? '🟢' : '🔴'}
                </div>
                <div className="stat-label">Blockchain Status</div>
              </div>
            </div>
          </section>
        )}


        {/* Register */}
        <section className="glass-panel">
          <h2 className="section-title">Register AI Model</h2>
          <form onSubmit={handleRegister} className="register-form">
            <input
              type="text"
              className="glass-input"
              placeholder="Model ID (e.g. resnet18_v1) *"
              value={modelId}
              onChange={e => setModelId(e.target.value)}
              required
            />
            <input
              type="text"
              className="glass-input"
              placeholder="Model Name (e.g. ResNet18 Classifier) *"
              value={modelName}
              onChange={e => setModelName(e.target.value)}
              required
            />
            <textarea
              className="glass-input"
              placeholder="Description (optional)"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows="2"
            />
            <input
              type="text"
              className="glass-input"
              placeholder="Owner / Author (optional)"
              value={owner}
              onChange={e => setOwner(e.target.value)}
            />
            <input
              type="text"
              className="glass-input"
              placeholder="Tags, comma-separated (e.g. pytorch, vision, production)"
              value={tags}
              onChange={e => setTags(e.target.value)}
            />

            <div className="file-input-wrapper">
              <input
                id="fileInput"
                type="file"
                className="glass-file-input"
                onChange={e => setFile(e.target.files[0])}
                accept=".pth,.pkl,.joblib,.onnx,.pt,.bin,.safetensors"
                required
              />
              <label htmlFor="fileInput" className="file-label">
                <span className="file-button">Choose File</span>
                <span className="file-name">{file ? file.name : 'No file chosen'}</span>
              </label>
            </div>

            <button
              type="button"
              id="loadDemoBtn"
              className="glass-button"
              onClick={async () => {
                try {
                  const response = await fetch('/test_model.bin');
                  const blob = await response.blob();
                  const dummyFile = new File([blob], 'test_model.bin', { type: 'application/octet-stream' });
                  setFile(dummyFile);
                } catch (err) {
                  alert('Error loading demo file: ' + err.message);
                }
              }}
              style={{ marginTop: '10px', width: '100%', padding: '10px', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', borderRadius: '8px', cursor: 'pointer' }}
            >
              📂 Use Demo Model File
            </button>

            <button
              type="submit"
              className={`blockchain-button ${loading ? 'registering' : ''}`}
              disabled={loading}
            >
              <span className="button-icon">🔗</span>
              <span className="button-text">
                {loading ? '⏳ Registering...' : 'Register on Blockchain'}
              </span>
              {loading && (
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
              )}
              <div className="glow-ring" />
            </button>
          </form>

          {lastHash && (
            <div className="result success">
              <h3>✅ Registration Successful</h3>
              <p><strong>Hash:</strong> {lastHash.substring(0, 16)}...</p>
              <p className="small">Full: {lastHash}</p>
            </div>
          )}
        </section>


        {/* Model List */}
        <section className="glass-panel">
          <div className="section-header">
            <div className="header-left">
              <span className="icon">📦</span>
              <h2 className="section-title-inline">Registered Models</h2>
            </div>
            <div className="header-right">
              <button onClick={() => setShowFilters(f => !f)} className="glass-button">
                <span className="icon">{showFilters ? '🔼' : '🔽'}</span>
                <span>{showFilters ? 'Hide' : 'Show'} Filters</span>
              </button>
              <button onClick={handleExport} className="glass-button">
                <span className="icon">📥</span>
                <span>Export Report</span>
              </button>
            </div>
          </div>

          <div className="models-count">{models.length} Models Registered</div>

          {showFilters && (
            <div className="filters">
              <input
                type="text"
                placeholder="🔍 Search by ID, name, or description..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="search-input"
              />
              <input
                type="text"
                placeholder="Filter by tag..."
                value={filterTag}
                onChange={e => setFilterTag(e.target.value)}
                className="filter-input"
              />
              <input
                type="text"
                placeholder="Filter by owner..."
                value={filterOwner}
                onChange={e => setFilterOwner(e.target.value)}
                className="filter-input"
              />
              {(searchQuery || filterTag || filterOwner) && (
                <button onClick={clearFilters} className="clear-filters">
                  ✖ Clear
                </button>
              )}
            </div>
          )}

          {models.length > 0 ? (
            <div className="models-list">
              {models.map(model => (
                <div key={model.model_id} className="model-card">
                  <div className="model-info">
                    <h4>{model.model_id}</h4>
                    <p className="model-name">{model.model_name}</p>
                    {model.description && (
                      <p className="model-description">{model.description}</p>
                    )}
                    <div className="model-meta">
                      {model.owner && (
                        <span className="badge">👤 {model.owner}</span>
                      )}
                      {model.tags && model.tags.map(tag => (
                        <span key={tag} className="badge tag">🏷️ {tag}</span>
                      ))}
                      <span className="badge">v{model.latest_version}</span>
                    </div>
                  </div>
                  <div className="model-actions">
                    <button
                      onClick={(e) => handleVerify(model.model_id, e)}
                      disabled={loading}
                      className="action-button verify"
                    >
                      ✅ Verify
                    </button>
                    <button
                      onClick={() => handleVerify(model.model_id, { shiftKey: true })}
                      disabled={loading}
                      className="action-button verify"
                      style={{ fontSize: '10px', background: 'rgba(99, 102, 241, 0.4)', borderColor: '#8b5cf6', padding: '5px' }}
                      title="Verify using the demo file"
                    >
                      ⚡ Demo Verify
                    </button>
                    <button
                      onClick={() => handleTamper(model.model_id)}
                      disabled={loading}
                      className="action-button danger"
                    >
                      🚨 Demo Tamper
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="rocket-icon">🚀</div>
              <h3>No models yet</h3>
              <p>
                {searchQuery || filterTag || filterOwner
                  ? 'No models match your filters'
                  : 'Start by registering your first AI model above'}
              </p>
            </div>
          )}
        </section>


        {/* Verification Result */}
        {verifyResult && (
          <section className="glass-panel">
            <h2 className="section-title">🔍 Verification Result</h2>
            <div className={verifyResult.is_valid ? 'result success' : 'result failure'}>
              <h3>{verifyResult.status}</h3>
              <p><strong>Model ID:</strong> {verifyResult.model_id}</p>
              <p><strong>Version:</strong> {verifyResult.version}</p>
              <p><strong>Registered Hash:</strong> {verifyResult.registered_hash}</p>
              <p><strong>Current Hash:</strong> {verifyResult.current_hash}</p>
              <p><strong>Blockchain Verified:</strong> {verifyResult.blockchain_verified ? '✅ Yes' : '❌ No'}</p>
              <p><strong>Checked at:</strong> {verifyResult.timestamp}</p>
              {verifyResult.etherscan_url && (
                <p>
                  <a href={verifyResult.etherscan_url} target="_blank" rel="noopener noreferrer">
                    🔗 View on Etherscan
                  </a>
                </p>
              )}
              <p className="small">
                {verifyResult.is_valid
                  ? '✅ No tampering detected - model integrity confirmed'
                  : '🚨 Hash mismatch - model may have been tampered with'}
              </p>
            </div>
          </section>
        )}


        <footer className="footer">
          <p className="footer-text">
            <span className="icon">🔐</span>
            Setting The Standard For Deployed AI Authenticity
          </p>
        </footer>

      </div>
    </div>
  );
}

export default App;
