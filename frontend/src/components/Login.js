import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Logo from './Logo';
import './Login.css';

function Login({ onLogin, initialMode = 'login', selectedTier = 'free', onBack }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isSignUp, setIsSignUp] = useState(initialMode === 'signup');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('auth'); // 'auth' or 'gmail'
  const [pendingUser, setPendingUser] = useState(null);

  useEffect(() => {
    setIsSignUp(initialMode === 'signup');
  }, [initialMode]);

  const tierInfo = {
    free: { name: 'Free', color: '#64748b' },
    pro: { name: 'Pro', color: '#667eea' },
    enterprise: { name: 'Enterprise', color: '#764ba2' }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = isSignUp ? '/auth/clerk-signup' : '/auth/clerk-signin';
      const payload = isSignUp 
        ? { email, password, name: name || email.split('@')[0] }
        : { email, password };
      
      const response = await axios.post(endpoint, payload);
      
      if (response.data.success) {
        const userData = {
          user_id: response.data.user_id,
          email: response.data.email,
          name: response.data.name,
          tier: selectedTier
        };
        const token = response.data.token;
        
        // Store temporarily and check Gmail status
        setPendingUser({ userData, token });
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Check if Gmail is already connected
        try {
          const gmailStatus = await axios.get('/auth/gmail/status');
          if (gmailStatus.data.connected) {
            // Gmail already connected, proceed to dashboard
            onLogin(userData, token);
          } else {
            // Need to connect Gmail
            setStep('gmail');
          }
        } catch {
          // If check fails, proceed anyway
          onLogin(userData, token);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
      setLoading(false);
    }
  };

  const connectGmail = async () => {
    try {
      const response = await axios.get('/auth/gmail/url');
      if (response.data.auth_url) {
        // Open Gmail OAuth in popup
        const popup = window.open(response.data.auth_url, 'gmail_auth', 'width=600,height=700');
        
        // Poll for popup close
        const checkPopup = setInterval(() => {
          if (popup.closed) {
            clearInterval(checkPopup);
            // Proceed to dashboard after popup closes
            if (pendingUser) {
              onLogin(pendingUser.userData, pendingUser.token);
            }
          }
        }, 500);
      }
    } catch (err) {
      console.error('Gmail connect error:', err);
      // Proceed anyway
      if (pendingUser) {
        onLogin(pendingUser.userData, pendingUser.token);
      }
    }
  };

  const skipGmail = () => {
    if (pendingUser) {
      onLogin(pendingUser.userData, pendingUser.token);
    }
  };

  // Gmail connection step
  if (step === 'gmail') {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <Logo size={40} showText={true} variant="default" />
          </div>

          <div className="gmail-step">
            <div className="gmail-icon">📧</div>
            <h2>Connect Your Gmail</h2>
            <p>Connect Gmail to send chat messages as emails to your team members.</p>
            
            <button onClick={connectGmail} className="gmail-btn">
              🔗 Connect Gmail Account
            </button>
            
            <button onClick={skipGmail} className="skip-btn">
              Skip for now →
            </button>
            
            <p className="gmail-note">
              You can always connect Gmail later from Team Chat settings.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        {onBack && (
          <button className="back-btn" onClick={onBack}>
            ← Back
          </button>
        )}
        
        <div className="login-header">
          <Logo size={40} showText={true} variant="default" />
        </div>

        {isSignUp && selectedTier && (
          <div className="selected-tier" style={{ borderColor: tierInfo[selectedTier]?.color }}>
            <span className="tier-label">Selected Plan:</span>
            <span className="tier-name" style={{ color: tierInfo[selectedTier]?.color }}>
              {tierInfo[selectedTier]?.name}
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <h2>{isSignUp ? 'Create Your Account' : 'Welcome Back'}</h2>
          
          {error && <div className="error-message">{error}</div>}
          
          {isSignUp && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
              />
            </div>
          )}
          
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={8}
            />
            {isSignUp && (
              <span className="password-hint">Minimum 8 characters</span>
            )}
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Please wait...' : (isSignUp ? 'Create Account' : 'Sign In')}
          </button>

          <p className="toggle-auth">
            {isSignUp ? 'Already have an account?' : "Don't have an account?"}
            <button type="button" onClick={() => setIsSignUp(!isSignUp)}>
              {isSignUp ? 'Sign In' : 'Sign Up Free'}
            </button>
          </p>
        </form>

        <p className="powered-by">🔒 Secured by Clerk Authentication</p>
      </div>
    </div>
  );
}

export default Login;
