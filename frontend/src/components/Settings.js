import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './Settings.css';

function Settings({ user }) {
  const [keys, setKeys] = useState({
    groq_api_key: '',
    cohere_api_key: '',
    pinecone_api_key: '',
    pinecone_index: ''
  });
  const [savedKeys, setSavedKeys] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState({});
  const [testResults, setTestResults] = useState({});
  const [showKeys, setShowKeys] = useState({});
  const [usage, setUsage] = useState(null);
  
  // Model selection state
  const [models, setModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('auto');
  const [savingModel, setSavingModel] = useState(false);

  // Fetch current keys, usage, and model preference
  const fetchSettings = useCallback(async () => {
    try {
      const [keysRes, usageRes, modelsRes, prefsRes] = await Promise.all([
        axios.get('/user/api-keys'),
        axios.get('/user/usage'),
        axios.get('/models'),
        axios.get('/user/preferences')
      ]);
      
      setSavedKeys(keysRes.data.keys || {});
      setUsage(usageRes.data);
      setModels(modelsRes.data.models || {});
      setSelectedModel(prefsRes.data.model || 'auto');
      
      // Pre-fill masked keys
      const masked = {};
      Object.keys(keysRes.data.keys || {}).forEach(key => {
        if (keysRes.data.keys[key]) {
          masked[key] = '••••••••••••••••';
        }
      });
      setKeys(prev => ({ ...prev, ...masked }));
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Save model preference
  const saveModelPreference = async (model) => {
    setSavingModel(true);
    try {
      await axios.post('/user/preferences/model', { model });
      setSelectedModel(model);
    } catch (err) {
      alert('Failed to save model preference');
    } finally {
      setSavingModel(false);
    }
  };

  // Save a single key
  const saveKey = async (keyName) => {
    if (!keys[keyName] || keys[keyName] === '••••••••••••••••') return;
    
    setSaving(true);
    try {
      await axios.post('/user/api-keys', {
        key_name: keyName,
        key_value: keys[keyName]
      });
      
      setSavedKeys(prev => ({ ...prev, [keyName]: true }));
      setKeys(prev => ({ ...prev, [keyName]: '••••••••••••••••' }));
      setTestResults(prev => ({ ...prev, [keyName]: null }));
    } catch (err) {
      alert('Failed to save key: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  // Delete a key
  const deleteKey = async (keyName) => {
    if (!window.confirm(`Delete your ${keyName.replace(/_/g, ' ')}?`)) return;
    
    try {
      await axios.delete(`/user/api-keys/${keyName}`);
      setSavedKeys(prev => {
        const updated = { ...prev };
        delete updated[keyName];
        return updated;
      });
      setKeys(prev => ({ ...prev, [keyName]: '' }));
      setTestResults(prev => ({ ...prev, [keyName]: null }));
    } catch (err) {
      alert('Failed to delete key');
    }
  };

  // Test a key
  const testKey = async (keyName) => {
    setTesting(prev => ({ ...prev, [keyName]: true }));
    setTestResults(prev => ({ ...prev, [keyName]: null }));
    
    try {
      const response = await axios.post('/user/api-keys/test', { key_name: keyName });
      setTestResults(prev => ({ 
        ...prev, 
        [keyName]: { success: response.data.valid, message: response.data.message }
      }));
    } catch (err) {
      setTestResults(prev => ({ 
        ...prev, 
        [keyName]: { success: false, message: err.response?.data?.detail || 'Test failed' }
      }));
    } finally {
      setTesting(prev => ({ ...prev, [keyName]: false }));
    }
  };

  const keyConfigs = [
    {
      name: 'groq_api_key',
      label: 'Groq API Key',
      description: 'Powers AI responses and analysis. Get free key at groq.com',
      link: 'https://console.groq.com/keys',
      icon: '🤖'
    },
    {
      name: 'cohere_api_key',
      label: 'Cohere API Key',
      description: 'Used for text embeddings in RAG search. Get free key at cohere.com',
      link: 'https://dashboard.cohere.com/api-keys',
      icon: '🔍'
    },
    {
      name: 'pinecone_api_key',
      label: 'Pinecone API Key',
      description: 'Vector database for document search. Get free key at pinecone.io',
      link: 'https://app.pinecone.io',
      icon: '🌲'
    },
    {
      name: 'pinecone_index',
      label: 'Pinecone Index Name',
      description: 'Your Pinecone index name (create one in Pinecone dashboard)',
      link: 'https://app.pinecone.io',
      icon: '📁'
    }
  ];

  if (loading) {
    return (
      <div className="settings-container">
        <div className="settings-loading">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      {/* Usage Stats */}
      <div className="settings-card usage-card">
        <h2>📊 Your Usage</h2>
        <div className="usage-stats">
          <div className="usage-stat">
            <span className="usage-value">{usage?.tokens_used || 0}</span>
            <span className="usage-label">Tokens Used (30 days)</span>
          </div>
          <div className="usage-stat">
            <span className="usage-value">{user.tier === 'free' ? '10' : '∞'}</span>
            <span className="usage-label">Daily Query Limit</span>
          </div>
          <div className="usage-stat">
            <span className={`usage-badge ${user.tier}`}>{user.tier || 'Free'}</span>
            <span className="usage-label">Current Plan</span>
          </div>
        </div>
        
        {user.tier === 'free' && (
          <div className="usage-tip">
            💡 <strong>Tip:</strong> Add your own API keys below to get unlimited usage on the Free plan!
          </div>
        )}
      </div>

      {/* Model Selection Section */}
      <div className="settings-card model-card">
        <div className="card-header">
          <h2>🤖 AI Model</h2>
          <p>Choose which model powers your analysis (all use same Groq API key)</p>
        </div>
        
        <div className="model-selector">
          <div className="model-options">
            {Object.entries(models).map(([modelId, modelInfo]) => (
              <div 
                key={modelId}
                className={`model-option ${selectedModel === modelId ? 'selected' : ''}`}
                onClick={() => saveModelPreference(modelId)}
              >
                <div className="model-option-header">
                  <span className="model-icon">
                    {modelId === 'auto' ? '🤖' : 
                     modelId.includes('70b') ? '🧠' : 
                     modelId.includes('mixtral') ? '⚡' : '💬'}
                  </span>
                  <div className="model-name">{modelInfo.name}</div>
                  {selectedModel === modelId && <span className="model-check">✓</span>}
                </div>
                <div className="model-description">{modelInfo.description}</div>
                <div className="model-badges">
                  {modelInfo.speed && (
                    <span className={`model-badge speed-${modelInfo.speed}`}>
                      {modelInfo.speed === 'fast' ? '⚡ Fast' : 
                       modelInfo.speed === 'medium' ? '🔄 Medium' : '🎯 Varies'}
                    </span>
                  )}
                  {modelInfo.quality && (
                    <span className={`model-badge quality-${modelInfo.quality}`}>
                      {modelInfo.quality === 'excellent' ? '⭐ Best' : 
                       modelInfo.quality === 'very good' ? '✨ Great' : 
                       modelInfo.quality === 'good' ? '👍 Good' : '🎯 Optimal'}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {savingModel && <div className="model-saving">Saving preference...</div>}
          
          <div className="model-tip">
            💡 <strong>Auto mode</strong> picks the best model for each task automatically:
            <ul>
              <li>Quick questions → Fast model (8B)</li>
              <li>Complex analysis → Best quality (70B)</li>
              <li>Meeting prep → Balanced (70B)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* API Keys Section */}
      <div className="settings-card">
        <div className="card-header">
          <h2>🔑 API Keys</h2>
          <p>Add your own API keys to use your own quotas (optional)</p>
        </div>

        <div className="keys-list">
          {keyConfigs.map((config) => (
            <div key={config.name} className="key-item">
              <div className="key-header">
                <div className="key-info">
                  <span className="key-icon">{config.icon}</span>
                  <div>
                    <h4>{config.label}</h4>
                    <p>{config.description}</p>
                    <a href={config.link} target="_blank" rel="noopener noreferrer" className="key-link">
                      Get API Key →
                    </a>
                  </div>
                </div>
                {savedKeys[config.name] && (
                  <span className="key-saved-badge">✓ Saved</span>
                )}
              </div>
              
              <div className="key-input-row">
                <div className="key-input-wrapper">
                  <input
                    type={showKeys[config.name] ? 'text' : 'password'}
                    value={keys[config.name] || ''}
                    onChange={(e) => setKeys(prev => ({ ...prev, [config.name]: e.target.value }))}
                    placeholder={`Enter your ${config.label}`}
                    className="key-input"
                  />
                  <button 
                    className="toggle-visibility"
                    onClick={() => setShowKeys(prev => ({ ...prev, [config.name]: !prev[config.name] }))}
                  >
                    {showKeys[config.name] ? '👁️' : '👁️‍🗨️'}
                  </button>
                </div>
                
                <div className="key-actions">
                  <button 
                    className="btn-save"
                    onClick={() => saveKey(config.name)}
                    disabled={saving || !keys[config.name] || keys[config.name] === '••••••••••••••••'}
                  >
                    {saving ? '...' : 'Save'}
                  </button>
                  
                  {savedKeys[config.name] && (
                    <>
                      <button 
                        className="btn-test"
                        onClick={() => testKey(config.name)}
                        disabled={testing[config.name]}
                      >
                        {testing[config.name] ? '...' : 'Test'}
                      </button>
                      <button 
                        className="btn-delete"
                        onClick={() => deleteKey(config.name)}
                      >
                        🗑️
                      </button>
                    </>
                  )}
                </div>
              </div>
              
              {testResults[config.name] && (
                <div className={`test-result ${testResults[config.name].success ? 'success' : 'error'}`}>
                  {testResults[config.name].success ? '✓' : '✗'} {testResults[config.name].message}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Security Note */}
      <div className="settings-card security-note">
        <h3>🔒 Security</h3>
        <ul>
          <li>Your API keys are encrypted before storage</li>
          <li>Keys are only used for your requests</li>
          <li>You can delete your keys anytime</li>
          <li>We never share your keys with third parties</li>
        </ul>
      </div>
    </div>
  );
}

export default Settings;
