import React from 'react';

function Logo({ size = 40, showText = true, variant = 'default' }) {
  const colors = {
    default: {
      primary: '#667eea',
      secondary: '#764ba2',
      accent: '#f093fb'
    },
    white: {
      primary: '#ffffff',
      secondary: '#e2e8f0',
      accent: '#ffffff'
    },
    dark: {
      primary: '#1a1a2e',
      secondary: '#2d2d44',
      accent: '#667eea'
    }
  };

  const c = colors[variant] || colors.default;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: size * 0.3 }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Background circle with gradient */}
        <defs>
          <linearGradient id={`logoGrad-${variant}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={c.primary} />
            <stop offset="100%" stopColor={c.secondary} />
          </linearGradient>
          <linearGradient id={`barGrad-${variant}`} x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor={c.primary} />
            <stop offset="100%" stopColor={c.accent} />
          </linearGradient>
          <filter id="logoShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="4" floodOpacity="0.25"/>
          </filter>
        </defs>
        
        {/* Main rounded square background */}
        <rect
          x="5"
          y="5"
          width="90"
          height="90"
          rx="22"
          fill={`url(#logoGrad-${variant})`}
          filter="url(#logoShadow)"
        />
        
        {/* Chart bars */}
        <rect x="20" y="55" width="14" height="25" rx="4" fill="white" opacity="0.9"/>
        <rect x="38" y="40" width="14" height="40" rx="4" fill="white" opacity="0.95"/>
        <rect x="56" y="28" width="14" height="52" rx="4" fill="white"/>
        
        {/* Trend line */}
        <path
          d="M 24 50 Q 45 35, 63 22"
          stroke="white"
          strokeWidth="4"
          strokeLinecap="round"
          fill="none"
          opacity="0.9"
        />
        
        {/* Arrow head */}
        <path
          d="M 58 26 L 66 18 L 68 28"
          stroke="white"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        
        {/* Sparkle/insight dot */}
        <circle cx="76" cy="24" r="6" fill="white">
          <animate
            attributeName="opacity"
            values="1;0.5;1"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
      </svg>
      
      {showText && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <span style={{
            fontSize: size * 0.5,
            fontWeight: 800,
            background: variant === 'white' 
              ? 'white' 
              : `linear-gradient(135deg, ${c.primary} 0%, ${c.secondary} 100%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: variant === 'white' ? 'white' : 'transparent',
            backgroundClip: 'text',
            letterSpacing: '-0.02em'
          }}>
            DataInsight
          </span>
          <span style={{
            fontSize: size * 0.32,
            fontWeight: 600,
            color: variant === 'white' ? 'rgba(255,255,255,0.8)' : '#64748b',
            letterSpacing: '0.1em',
            textTransform: 'uppercase'
          }}>
            Pro
          </span>
        </div>
      )}
    </div>
  );
}

export default Logo;
