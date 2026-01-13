import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import './Analysis.css';

// Helper function to format column names
const formatColumnName = (col) => {
  if (!col) return 'Column';
  // If it's a generic col_X name, make it more readable
  if (/^col_\d+$/i.test(col)) {
    return `Column ${parseInt(col.replace(/col_/i, '')) + 1}`;
  }
  // Otherwise return as-is (it's a real column name)
  return col;
};

function Analysis({ user }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null); // New: upload progress
  const [jobId, setJobId] = useState(null); // New: background job tracking
  const [uploadedFile, setUploadedFile] = useState(null);
  const [columns, setColumns] = useState([]);
  const [summary, setSummary] = useState(null);
  const [dataPreview, setDataPreview] = useState(null);
  const [fileType, setFileType] = useState(null);
  const [query, setQuery] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [aiResponse, setAiResponse] = useState('');
  const [modelUsed, setModelUsed] = useState(null);
  const [vizQuery, setVizQuery] = useState('');
  const [generating, setGenerating] = useState(false);
  const [plotData, setPlotData] = useState(null);
  const [chartTitle, setChartTitle] = useState('');
  
  // Model selection state
  const [models, setModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('auto');
  
  // Share to chat state
  const [groups, setGroups] = useState([]);
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [sharing, setSharing] = useState(false);

  // Fetch chat groups and models
  const fetchGroups = useCallback(async () => {
    try {
      console.log('[Analysis] Fetching groups...');
      const response = await axios.get('/chat/groups');
      console.log('[Analysis] Groups response:', response.data);
      setGroups(response.data.groups || []);
    } catch (err) {
      console.error('Failed to fetch groups:', err);
      // Don't fail silently - groups might just not exist yet
      setGroups([]);
    }
  }, []);

  const fetchModels = useCallback(async () => {
    try {
      console.log('[Analysis] Fetching models from /models...');
      const response = await axios.get('/models');
      console.log('[Analysis] Models response:', response.data);
      setModels(response.data.models || {});
      
      // Ensure 'auto' option is always available
      if (!response.data.models?.auto) {
        setModels(prev => ({
          auto: { name: '🤖 Auto (Smart Selection)' },
          ...prev
        }));
      }
    } catch (err) {
      console.error('Failed to fetch models:', err);
      console.error('Error details:', err.response?.data);
      
      // Fallback models if API fails
      setModels({
        auto: { name: '🤖 Auto (Smart Selection)' },
        'llama-3.1-70b-versatile': { name: 'Llama 3.1 70B' },
        'llama-3.1-8b-instant': { name: 'Llama 3.1 8B' }
      });
    }
  }, []);

  useEffect(() => {
    fetchGroups();
    fetchModels();
  }, [fetchGroups, fetchModels]);

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  // Upload file with speed optimization
  const uploadFile = async () => {
    if (!file) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', user.user_id);
    
    try {
      // 🚀 Use the new optimized quick upload endpoint
      const response = await axios.post('/upload/quick', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Handle quick upload response
      if (response.data.status === 'preview_ready') {
        setUploadedFile(response.data.filename);
        
        // Extract columns from preview data
        let extractedColumns = response.data.preview?.columns || [];
        
        // For documents with tables, extract columns from the first table
        if (response.data.preview?.tables && response.data.preview.tables.length > 0) {
          extractedColumns = response.data.preview.tables[0].columns || [];
        }
        
        setColumns(extractedColumns);
        setSummary(null); // Will be available after background processing
        setDataPreview(response.data.preview || null);
        setFileType(response.data.preview?.type || 'unknown');
        
        // Show success message with job info
        setUploadProgress('✅ Preview ready! Full processing continues in background...');
        
        // Poll for completion (optional - for executive summary)
        if (response.data.job_id) {
          setJobId(response.data.job_id);
          pollJobStatus(response.data.job_id);
        }
      } else {
        // Fallback to old response format
        setUploadedFile(response.data.filename);
        setColumns(response.data.columns || []);
        setSummary(response.data.executive_summary);
        setDataPreview(response.data.preview || null);
        setFileType(response.data.file_type || 'unknown');
      }
    } catch (err) {
      console.error('Upload failed:', err);
      
      // If quick upload fails, try legacy upload as fallback
      if (err.response?.status === 404) {
        console.log('Quick upload not available, trying legacy upload...');
        try {
          const legacyResponse = await axios.post('/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          setUploadedFile(legacyResponse.data.filename);
          setColumns(legacyResponse.data.columns || []);
          setSummary(legacyResponse.data.executive_summary);
          setDataPreview(legacyResponse.data.preview || null);
          setFileType(legacyResponse.data.file_type || 'unknown');
        } catch (legacyErr) {
          alert('Upload failed: ' + (legacyErr.response?.data?.detail || legacyErr.message));
        }
      } else {
        alert('Upload failed: ' + (err.response?.data?.detail || err.message));
      }
    } finally {
      setUploading(false);
    }
  };

  // Poll job status for background processing completion
  const pollJobStatus = async (jobId) => {
    const maxPolls = 60; // Poll for up to 60 seconds
    let pollCount = 0;
    
    const poll = async () => {
      try {
        const response = await axios.get(`/upload/status/${jobId}`);
        const status = response.data;
        
        // Update progress message
        setUploadProgress(`🔄 ${status.message} (${status.progress}%)`);
        
        if (status.status === 'completed') {
          setUploadProgress('✅ Processing complete!');
          if (status.result?.executive_summary) {
            setSummary(status.result.executive_summary);
          }
          setJobId(null);
          console.log('✅ Background processing completed');
          return;
        } else if (status.status === 'failed') {
          setUploadProgress('❌ Processing failed: ' + (status.error || 'Unknown error'));
          setJobId(null);
          console.error('❌ Background processing failed:', status.error);
          return;
        }
        
        // Continue polling if still processing
        if (status.status === 'processing' && pollCount < maxPolls) {
          pollCount++;
          setTimeout(poll, 1000); // Poll every second
        } else if (pollCount >= maxPolls) {
          setUploadProgress('⏰ Processing is taking longer than expected...');
          setJobId(null);
        }
      } catch (err) {
        console.error('Failed to check job status:', err);
        setUploadProgress('⚠️ Unable to check processing status');
        setJobId(null);
      }
    };
    
    // Start polling after a short delay
    setTimeout(poll, 2000);
  };

  // Ask AI
  const askAI = async () => {
    if (!query.trim() || !uploadedFile) return;
    
    setAnalyzing(true);
    setModelUsed(null);
    setAiResponse('');
    try {
      const response = await axios.post('/query', null, {
        params: {
          user_query: query,
          user_id: user.user_id,
          file_id: uploadedFile,
          model: selectedModel
        }
      });
      
      const data = response.data;
      
      // Extract just the answer - handle various response formats
      let answer = '';
      if (typeof data === 'string') {
        answer = data;
      } else if (data.answer) {
        answer = data.answer;
      } else if (data.text) {
        answer = data.text;
      } else {
        // Last resort - stringify but try to extract answer first
        answer = JSON.stringify(data, null, 2);
      }
      
      setAiResponse(answer);
      setModelUsed(data.model_used || selectedModel);
    } catch (err) {
      console.error('Query failed:', err);
      setAiResponse('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setAnalyzing(false);
    }
  };

  // Generate visualization using AI
  const generateChart = async () => {
    if (!uploadedFile || !vizQuery.trim()) {
      alert('Please describe the chart you want');
      return;
    }
    
    setGenerating(true);
    setPlotData(null);
    
    const formData = new FormData();
    formData.append('user_id', user.user_id);
    formData.append('file_id', uploadedFile);
    formData.append('query', vizQuery);
    
    try {
      const response = await axios.post('/visualize/nl', formData, {
        timeout: 60000 // 60 second timeout for AI generation
      });
      
      if (response.data.success && response.data.plot) {
        const parsed = JSON.parse(response.data.plot);
        setPlotData(parsed);
        setChartTitle(parsed.layout?.title?.text || 'Generated Chart');
      } else {
        alert(response.data.error || 'Failed to generate chart');
      }
    } catch (err) {
      console.error('Visualization failed:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Unknown error';
      alert('Visualization failed: ' + errorMsg);
    } finally {
      setGenerating(false);
    }
  };

  // Share chart to chat group
  const shareToChat = async () => {
    if (!plotData || !selectedGroup) {
      alert('Please select a group to share to');
      return;
    }
    
    setSharing(true);
    try {
      const response = await axios.post('/chat/share-chart', {
        group_id: parseInt(selectedGroup),
        chart_json: JSON.stringify(plotData),
        chart_title: chartTitle || 'Shared Chart'
      });
      
      if (response.data.success) {
        alert('Chart shared to chat!');
        setShowShareModal(false);
        setSelectedGroup('');
      }
    } catch (err) {
      console.error('Failed to share chart:', err);
      alert('Failed to share: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSharing(false);
    }
  };

  return (
    <div className="analysis-container">
      {/* File Upload Section */}
      <div className="analysis-card">
        <h2>📁 Upload Data</h2>
        <div className="upload-area">
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.pdf,.docx"
            onChange={handleFileChange}
            id="file-input"
          />
          <label htmlFor="file-input" className="file-label">
            {file ? file.name : 'Choose a file (CSV, Excel, PDF, DOCX)'}
          </label>
          <button 
            onClick={uploadFile} 
            disabled={!file || uploading}
            className="upload-btn"
          >
            {uploading ? '⏳ Processing...' : '🚀 Quick Process'}
          </button>
        </div>
        
        {/* Upload Progress Indicator */}
        {uploadProgress && (
          <div className="upload-progress">
            <div className="progress-message">{uploadProgress}</div>
            {jobId && (
              <div className="progress-note">
                <small>💡 You can continue using the app while processing completes in the background</small>
              </div>
            )}
          </div>
        )}
        
        {uploadedFile && (
          <div className="upload-success">
            ✅ Uploaded: <strong>{uploadedFile}</strong>
            <span className="column-count">{columns.length} columns</span>
            {dataPreview?.is_preview && (
              <span className="preview-badge">📋 Preview Mode</span>
            )}
          </div>
        )}
      </div>

      {/* Executive Summary */}
      {summary && (
        <div className="analysis-card">
          <h2>📋 Executive Summary</h2>
          {summary.headline && <h3 className="summary-headline">{summary.headline}</h3>}
          <ul className="summary-bullets">
            {summary.bullets?.map((bullet, i) => (
              <li key={i}>{bullet}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Data Preview Section */}
      {dataPreview && (
        <div className="analysis-card">
          <h2>📊 Data Preview</h2>
          {dataPreview.type === 'table' && dataPreview.data && (
            <div className="data-preview-table-wrapper">
              <table className="data-preview-table">
                <thead>
                  <tr>
                    {dataPreview.columns?.map((col, i) => (
                      <th key={i}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dataPreview.data.slice(0, 10).map((row, i) => (
                    <tr key={i}>
                      {dataPreview.columns?.map((col, j) => (
                        <td key={j}>{row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {dataPreview.total_rows > 10 && (
                <p className="preview-note">Showing 10 of {dataPreview.total_rows} rows</p>
              )}
            </div>
          )}
          {dataPreview.type === 'text' && (
            <div className="data-preview-text">
              <p>{dataPreview.content}</p>
            </div>
          )}
          {dataPreview.type === 'document' && (
            <div className="data-preview-document">
              {dataPreview.tables && dataPreview.tables.length > 0 ? (
                <>
                  <p className="preview-info">📑 Structured data found in document ({dataPreview.total_rows || 'multiple'} rows)</p>
                  {dataPreview.tables.map((table, idx) => (
                    <div key={idx} className="document-table">
                      {dataPreview.tables.length > 1 && <h4>Table {idx + 1}</h4>}
                      <div className="data-preview-table-wrapper">
                        <table className="data-preview-table">
                          <thead>
                            <tr>
                              {table.columns?.map((col, i) => (
                                <th key={i}>{formatColumnName(col)}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {table.data?.slice(0, 10).map((row, i) => (
                              <tr key={i}>
                                {table.columns?.map((col, j) => (
                                  <td key={j}>{row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {table.data?.length > 10 && (
                          <p className="preview-note">Showing 10 of {table.data.length} rows</p>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <div className="document-summary">
                  <p className="preview-info">📄 Document Content</p>
                  {dataPreview.summary ? (
                    <div className="document-text-content">
                      {dataPreview.summary.split('\n').map((line, i) => (
                        line.trim() ? <p key={i}>{line}</p> : null
                      ))}
                    </div>
                  ) : dataPreview.content ? (
                    <div className="document-text-content">
                      {dataPreview.content.split('\n').map((line, i) => (
                        line.trim() ? <p key={i}>{line}</p> : null
                      ))}
                    </div>
                  ) : (
                    <p className="no-preview">No preview available</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AI Query Section */}
      {uploadedFile && (
        <div className="analysis-card">
          <h2>🤖 Ask AI</h2>
          <div className="query-area">
            <textarea
              placeholder="Ask a question about your data... e.g., What are the top selling products?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
            />
            <div className="query-controls">
              <div className="model-select-wrapper">
                <label>Model:</label>
                <select 
                  value={selectedModel} 
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="model-select"
                >
                  {Object.entries(models).map(([id, info]) => (
                    <option key={id} value={id}>
                      {id === 'auto' ? '🤖 Auto' : info.name}
                    </option>
                  ))}
                </select>
              </div>
              <button 
                onClick={askAI} 
                disabled={!query.trim() || analyzing}
                className="analyze-btn"
              >
                {analyzing ? 'Analyzing...' : '🔍 Analyze'}
              </button>
            </div>
          </div>
          
          {aiResponse && (
            <div className="ai-response">
              <div className="response-header">
                <div className="response-title">
                  <span className="response-icon">✨</span>
                  <h4>AI Analysis</h4>
                </div>
                {modelUsed && (
                  <span className="model-badge">
                    🤖 {models[modelUsed]?.name || modelUsed}
                  </span>
                )}
              </div>
              <div className="response-content">
                {aiResponse.split('\n').map((line, i) => {
                  // Format numbered lists
                  if (/^\d+\./.test(line.trim())) {
                    return <p key={i} className="response-list-item">{line}</p>;
                  }
                  // Format bullet points
                  if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
                    return <p key={i} className="response-bullet">{line}</p>;
                  }
                  // Regular paragraph
                  return line.trim() ? <p key={i}>{line}</p> : null;
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Visualization Section - Show for all file types */}
      {uploadedFile && (
        <div className="analysis-card">
          <h2>📊 Visualizations</h2>
          {columns.length > 0 ? (
            <p className="viz-hint">Describe the chart you want in plain English. AI will generate it for you!</p>
          ) : (
            <p className="viz-hint">📄 Document uploaded. If your document contains tables or numerical data, describe the chart you want below.</p>
          )}
          <div className="viz-controls">
            <input
              type="text"
              placeholder="e.g., Show me a pie chart of sales by region, or bar chart of revenue by month..."
              value={vizQuery}
              onChange={(e) => setVizQuery(e.target.value)}
              className="viz-query"
              onKeyPress={(e) => e.key === 'Enter' && generateChart()}
            />
            <button 
              onClick={generateChart} 
              disabled={generating || !vizQuery.trim()}
              className="generate-btn"
            >
              {generating ? '🔄 Generating...' : '✨ Generate Chart'}
            </button>
          </div>
          
          {columns.length > 0 && (
            <div className="viz-examples">
              <span>Try:</span>
              <button onClick={() => setVizQuery('Show total sales by customer as a bar chart')}>📊 Sales by Customer</button>
              <button onClick={() => setVizQuery('Create a pie chart showing distribution of order quantities')}>🥧 Pie Chart</button>
              <button onClick={() => setVizQuery('Line chart of revenue over time')}>📈 Trend Line</button>
              <button onClick={() => setVizQuery('Scatter plot comparing price vs quantity')}>⚡ Scatter Plot</button>
            </div>
          )}
          
          <div className="chart-container">
            {plotData ? (
              <>
                <div className="chart-actions">
                  <button 
                    className="share-chart-btn"
                    onClick={() => {
                      fetchGroups(); // Refresh groups when opening modal
                      setShowShareModal(true);
                    }}
                  >
                    📤 Share to Chat
                  </button>
                </div>
                <Plot
                  data={plotData.data}
                  layout={{
                    ...plotData.layout,
                    autosize: true,
                    margin: { t: 50, r: 30, b: 50, l: 60 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)'
                  }}
                  config={{ responsive: true, displayModeBar: true }}
                  style={{ width: '100%', height: '400px' }}
                />
              </>
            ) : (
              <div className="chart-placeholder">
                <span className="placeholder-icon">📊</span>
                <p>Describe the chart you want above and click "Generate Chart"</p>
                <p className="placeholder-hint">AI will analyze your data and create the visualization</p>
              </div>
            )}
          </div>

          {/* Share to Chat Modal */}
          {showShareModal && (
            <div className="modal-overlay" onClick={() => setShowShareModal(false)}>
              <div className="share-modal" onClick={e => e.stopPropagation()}>
                <h3>📤 Share Chart to Chat</h3>
                <div className="form-group">
                  <label>Chart Title</label>
                  <input
                    type="text"
                    value={chartTitle}
                    onChange={(e) => setChartTitle(e.target.value)}
                    placeholder="Enter chart title..."
                  />
                </div>
                <div className="form-group">
                  <label>Select Chat Group <button type="button" className="refresh-groups-btn" onClick={fetchGroups}>🔄</button></label>
                  <select 
                    value={selectedGroup} 
                    onChange={(e) => setSelectedGroup(e.target.value)}
                  >
                    <option value="">Choose a group...</option>
                    {groups.map(group => (
                      <option key={group.id} value={group.id}>{group.name}</option>
                    ))}
                  </select>
                  {groups.length === 0 && (
                    <p className="no-groups-hint">
                      No groups found. Create a group in Team Workspace first.
                    </p>
                  )}
                </div>
                <div className="modal-actions">
                  <button 
                    className="cancel-btn"
                    onClick={() => setShowShareModal(false)}
                  >
                    Cancel
                  </button>
                  <button 
                    className="share-btn"
                    onClick={shareToChat}
                    disabled={sharing || !selectedGroup}
                  >
                    {sharing ? 'Sharing...' : '📤 Share'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Analysis;
