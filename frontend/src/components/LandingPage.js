import React, { useState, useEffect } from 'react';
import Logo from './Logo';
import './LandingPage.css';

function LandingPage({ onGetStarted }) {
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [scrollY, setScrollY] = useState(0);

  // Track mouse for parallax effects
  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth - 0.5) * 20,
        y: (e.clientY / window.innerHeight - 0.5) * 20
      });
    };
    
    const handleScroll = () => setScrollY(window.scrollY);
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('scroll', handleScroll);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const features = [
    {
      icon: '📊',
      title: 'AI-Powered Analytics',
      description: 'Upload any data file and get instant insights powered by advanced AI'
    },
    {
      icon: '💬',
      title: 'Team Collaboration',
      description: 'Real-time chat with Gmail integration for seamless team communication'
    },
    {
      icon: '📅',
      title: 'Smart Calendar',
      description: 'AI automatically detects meetings from conversations and schedules them'
    },
    {
      icon: '📋',
      title: 'Executive Briefings',
      description: 'Generate professional summaries and meeting prep in seconds'
    },
    {
      icon: '📈',
      title: 'Interactive Visualizations',
      description: 'Create beautiful charts with natural language commands'
    },
    {
      icon: '🔒',
      title: 'Enterprise Security',
      description: 'Your data is encrypted and never used for training AI models'
    }
  ];

  const tiers = [
    {
      name: 'Free',
      price: { monthly: 0, yearly: 0 },
      description: 'Perfect for trying out DataInsight Pro',
      features: [
        '10 AI queries per day',
        '2 file uploads per day',
        '1 team workspace',
        '5 calendar events',
        'Basic visualizations',
        'Community support'
      ],
      limitations: [
        'Limited to 5MB files',
        'Basic briefings only'
      ],
      cta: 'Start Free',
      popular: false
    },
    {
      name: 'Pro',
      price: { monthly: 29, yearly: 290 },
      description: 'For professionals who need more power',
      features: [
        '100 AI queries per day',
        'Unlimited file uploads',
        '5 team workspaces',
        'Unlimited calendar events',
        'Advanced visualizations',
        'Priority email support',
        'Export to PDF/Excel',
        'Custom branding'
      ],
      limitations: [],
      cta: 'Start Pro Trial',
      popular: true
    },
    {
      name: 'Enterprise',
      price: { monthly: 99, yearly: 990 },
      description: 'For teams that need everything',
      features: [
        'Unlimited AI queries',
        'Unlimited everything',
        'Unlimited team workspaces',
        'Advanced analytics',
        'API access',
        'Dedicated support',
        'Custom integrations',
        'SSO & advanced security',
        'SLA guarantee'
      ],
      limitations: [],
      cta: 'Contact Sales',
      popular: false
    }
  ];

  const testimonials = [
    {
      quote: "DataInsight Pro transformed how our team analyzes data. What used to take hours now takes minutes.",
      author: "Sarah Chen",
      role: "VP of Analytics, TechCorp",
      avatar: "SC"
    },
    {
      quote: "The AI calendar feature is a game-changer. It picks up meeting requests from our chats automatically.",
      author: "Michael Roberts",
      role: "Product Manager, StartupXYZ",
      avatar: "MR"
    },
    {
      quote: "Finally, a tool that makes data accessible to everyone on our team, not just the analysts.",
      author: "Emily Watson",
      role: "CEO, DataDriven Inc",
      avatar: "EW"
    }
  ];

  return (
    <div className="landing-page">
      {/* Animated Background */}
      <div className="animated-bg">
        <div className="gradient-orb orb-1" style={{ transform: `translate(${mousePosition.x * 2}px, ${mousePosition.y * 2}px)` }}></div>
        <div className="gradient-orb orb-2" style={{ transform: `translate(${-mousePosition.x * 1.5}px, ${-mousePosition.y * 1.5}px)` }}></div>
        <div className="gradient-orb orb-3" style={{ transform: `translate(${mousePosition.x}px, ${-mousePosition.y}px)` }}></div>
        <div className="floating-shapes">
          <div className="shape shape-1">📊</div>
          <div className="shape shape-2">📈</div>
          <div className="shape shape-3">💡</div>
          <div className="shape shape-4">🚀</div>
          <div className="shape shape-5">⚡</div>
        </div>
        <div className="grid-overlay"></div>
      </div>

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <Logo size={36} showText={true} variant="default" />
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#testimonials">Testimonials</a>
        </div>
        <div className="nav-actions">
          <button className="btn-secondary" onClick={() => onGetStarted('login')}>
            Sign In
          </button>
          <button className="btn-primary btn-glow" onClick={() => onGetStarted('signup')}>
            Get Started Free
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge animate-float">
            <span className="badge-icon">🚀</span>
            AI-Powered Business Intelligence
            <span className="badge-shine"></span>
          </div>
          <h1 className="animate-slide-up">
            Transform Your Data Into 
            <span className="gradient-text animate-gradient"> Actionable Insights</span>
          </h1>
          <p className="hero-subtitle animate-slide-up delay-1">
            Upload any file, ask questions in plain English, and get instant visualizations, 
            summaries, and AI-powered recommendations. No data science degree required.
          </p>
          <div className="hero-cta animate-slide-up delay-2">
            <button className="btn-primary btn-large btn-glow" onClick={() => onGetStarted('signup')}>
              Start Free Trial
              <span className="btn-arrow">→</span>
              <span className="btn-shine"></span>
            </button>
            <button className="btn-outline btn-large">
              <span className="play-icon">▶</span>
              Watch Demo
            </button>
          </div>
          <div className="hero-stats animate-slide-up delay-3">
            <div className="stat">
              <span className="stat-number counter">10,000+</span>
              <span className="stat-label">Active Users</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-number counter">1M+</span>
              <span className="stat-label">Queries Processed</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-number counter">99.9%</span>
              <span className="stat-label">Uptime</span>
            </div>
          </div>
        </div>
        <div className="hero-visual">
          <div 
            className="dashboard-preview-3d"
            style={{ 
              transform: `perspective(1000px) rotateY(${-5 + mousePosition.x * 0.3}deg) rotateX(${5 + mousePosition.y * 0.3}deg) translateY(${scrollY * 0.1}px)`
            }}
          >
            <div className="preview-glow"></div>
            <div className="dashboard-preview">
              <div className="preview-header">
                <div className="preview-dots">
                  <span></span><span></span><span></span>
                </div>
                <span className="preview-title">DataInsight Pro Dashboard</span>
              </div>
              <div className="preview-content">
                <div className="preview-sidebar">
                  <div className="preview-menu-item active">
                    <span>📊</span> Analysis
                  </div>
                  <div className="preview-menu-item">
                    <span>💬</span> Team Chat
                  </div>
                  <div className="preview-menu-item">
                    <span>📅</span> Calendar
                  </div>
                  <div className="preview-menu-item">
                    <span>📋</span> Briefings
                  </div>
                </div>
                <div className="preview-main">
                  <div className="preview-chart">
                    <div className="chart-bars">
                      <div className="bar" style={{height: '60%'}}></div>
                      <div className="bar" style={{height: '80%'}}></div>
                      <div className="bar" style={{height: '45%'}}></div>
                      <div className="bar" style={{height: '90%'}}></div>
                      <div className="bar" style={{height: '70%'}}></div>
                      <div className="bar" style={{height: '55%'}}></div>
                    </div>
                  </div>
                  <div className="preview-insights">
                    <div className="insight-card">
                      <div className="insight-icon">📈</div>
                      <div className="insight-text">
                        <span className="insight-value">+24%</span>
                        <span className="insight-label">Growth</span>
                      </div>
                    </div>
                    <div className="insight-card">
                      <div className="insight-icon">💰</div>
                      <div className="insight-text">
                        <span className="insight-value">$1.2M</span>
                        <span className="insight-label">Revenue</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            {/* Floating elements around dashboard */}
            <div className="floating-card card-1">
              <span>🎯</span> AI Insights Ready
            </div>
            <div className="floating-card card-2">
              <span>✨</span> New Pattern Found
            </div>
            <div className="floating-card card-3">
              <span>📊</span> Report Generated
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="section-header">
          <span className="section-badge">✨ Features</span>
          <h2>Everything You Need to Make <span className="gradient-text">Data-Driven Decisions</span></h2>
          <p>Powerful features that help you understand your data without the complexity</p>
        </div>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div 
              key={index} 
              className="feature-card"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="feature-icon-wrapper">
                <div className="feature-icon">{feature.icon}</div>
                <div className="feature-icon-bg"></div>
              </div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
              <div className="feature-hover-effect"></div>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works">
        <div className="section-header">
          <h2>Get Insights in 3 Simple Steps</h2>
          <p>No setup required. Start analyzing in under a minute.</p>
        </div>
        <div className="steps-container">
          <div className="step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h3>Upload Your Data</h3>
              <p>Drag and drop any CSV, Excel, PDF, or document file</p>
            </div>
          </div>
          <div className="step-connector"></div>
          <div className="step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h3>Ask Questions</h3>
              <p>Type questions in plain English like "What are my top products?"</p>
            </div>
          </div>
          <div className="step-connector"></div>
          <div className="step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h3>Get Insights</h3>
              <p>Receive instant answers, charts, and actionable recommendations</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="pricing-section">
        <div className="section-header">
          <h2>Simple, Transparent Pricing</h2>
          <p>Start free, upgrade when you need more</p>
          <div className="billing-toggle">
            <span className={billingCycle === 'monthly' ? 'active' : ''}>Monthly</span>
            <button 
              className={`toggle-btn ${billingCycle === 'yearly' ? 'active' : ''}`}
              onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
            >
              <span className="toggle-slider"></span>
            </button>
            <span className={billingCycle === 'yearly' ? 'active' : ''}>
              Yearly <span className="save-badge">Save 20%</span>
            </span>
          </div>
        </div>
        <div className="pricing-grid">
          {tiers.map((tier, index) => (
            <div key={index} className={`pricing-card ${tier.popular ? 'popular' : ''}`}>
              {tier.popular && <div className="popular-badge">Most Popular</div>}
              <div className="pricing-header">
                <h3>{tier.name}</h3>
                <p className="pricing-description">{tier.description}</p>
                <div className="pricing-amount">
                  <span className="currency">$</span>
                  <span className="price">{tier.price[billingCycle]}</span>
                  <span className="period">/{billingCycle === 'monthly' ? 'mo' : 'yr'}</span>
                </div>
              </div>
              <ul className="pricing-features">
                {tier.features.map((feature, i) => (
                  <li key={i} className="feature-included">
                    <span className="check">✓</span> {feature}
                  </li>
                ))}
                {tier.limitations.map((limitation, i) => (
                  <li key={i} className="feature-limited">
                    <span className="limit">○</span> {limitation}
                  </li>
                ))}
              </ul>
              <button 
                className={`pricing-cta ${tier.popular ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => onGetStarted('signup', tier.name.toLowerCase())}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="testimonials-section">
        <div className="section-header">
          <h2>Loved by Data-Driven Teams</h2>
          <p>See what our customers have to say</p>
        </div>
        <div className="testimonials-grid">
          {testimonials.map((testimonial, index) => (
            <div key={index} className="testimonial-card">
              <div className="quote-icon">"</div>
              <p className="testimonial-quote">{testimonial.quote}</p>
              <div className="testimonial-author">
                <div className="author-avatar">{testimonial.avatar}</div>
                <div className="author-info">
                  <span className="author-name">{testimonial.author}</span>
                  <span className="author-role">{testimonial.role}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2>Ready to Transform Your Data Analysis?</h2>
          <p>Join thousands of teams making smarter decisions with DataInsight Pro</p>
          <button className="btn-primary btn-large" onClick={() => onGetStarted('signup')}>
            Start Your Free Trial
            <span className="btn-arrow">→</span>
          </button>
          <p className="cta-note">No credit card required • Free forever plan available</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <Logo size={32} showText={true} variant="white" />
            <p>AI-powered business intelligence for everyone</p>
          </div>
          <div className="footer-links">
            <div className="footer-column">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="#pricing">Pricing</a>
              <a href="#testimonials">Testimonials</a>
            </div>
            <div className="footer-column">
              <h4>Company</h4>
              <a href="#">About</a>
              <a href="#">Blog</a>
              <a href="#">Careers</a>
            </div>
            <div className="footer-column">
              <h4>Support</h4>
              <a href="#">Help Center</a>
              <a href="#">Contact</a>
              <a href="#">Status</a>
            </div>
            <div className="footer-column">
              <h4>Legal</h4>
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
              <a href="#">Security</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© 2026 DataInsight Pro. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
