import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useEffect, useState, useRef } from 'react';

/* ═══════════════════════════════════════════════════════════════════════════
   GRANTRADAR LANDING PAGE

   Aesthetic: Editorial Academic
   Inspiration: Nature Journal, The Economist, academic publications

   Typography: Cormorant Garamond (display) + Source Serif 4 (body)
   Colors: Warm ivory paper, deep forest green, muted gold accents
   Layout: Editorial asymmetry, generous whitespace, horizontal rules

   This should feel like reading a prestigious journal, not a SaaS product.
   ═══════════════════════════════════════════════════════════════════════════ */

// Custom styles injected into the page
const editorialStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,500;0,8..60,600;1,8..60,400;1,8..60,500&display=swap');

  .editorial-page {
    --paper: #faf8f3;
    --paper-dark: #f4f1e8;
    --ink: #1a1a1a;
    --ink-light: #4a4a4a;
    --ink-muted: #737373;
    --forest: #1a3a2f;
    --forest-light: #2d5a47;
    --gold: #8b7355;
    --gold-light: #c4a77d;
    --rule: #d4cfc4;
    --rule-dark: #a8a091;

    font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
    background: var(--paper);
    color: var(--ink);
  }

  .font-display {
    font-family: 'Cormorant Garamond', Georgia, serif;
  }

  .editorial-rule {
    height: 1px;
    background: var(--rule);
  }

  .editorial-rule-thick {
    height: 3px;
    background: var(--forest);
  }

  .editorial-quote {
    position: relative;
    padding-left: 1.5rem;
    border-left: 2px solid var(--gold);
  }

  .editorial-link {
    color: var(--forest);
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
    transition: all 0.2s ease;
  }

  .editorial-link:hover {
    color: var(--forest-light);
    text-decoration-thickness: 2px;
  }

  .editorial-btn {
    background: var(--forest);
    color: var(--paper);
    padding: 0.875rem 2rem;
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 500;
    letter-spacing: 0.025em;
    transition: all 0.3s ease;
    border: 1px solid var(--forest);
  }

  .editorial-btn:hover {
    background: var(--forest-light);
    border-color: var(--forest-light);
    transform: translateY(-1px);
  }

  .editorial-btn-outline {
    background: transparent;
    color: var(--forest);
    padding: 0.875rem 2rem;
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 500;
    letter-spacing: 0.025em;
    border: 1px solid var(--forest);
    transition: all 0.3s ease;
  }

  .editorial-btn-outline:hover {
    background: var(--forest);
    color: var(--paper);
  }

  /* Subtle page texture */
  .paper-texture {
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    opacity: 0.03;
    pointer-events: none;
  }

  /* Elegant fade-in animation */
  @keyframes fadeUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fade-up {
    animation: fadeUp 0.8s ease-out forwards;
  }

  .delay-1 { animation-delay: 0.1s; opacity: 0; }
  .delay-2 { animation-delay: 0.2s; opacity: 0; }
  .delay-3 { animation-delay: 0.3s; opacity: 0; }
  .delay-4 { animation-delay: 0.4s; opacity: 0; }
  .delay-5 { animation-delay: 0.5s; opacity: 0; }

  /* Feature card hover */
  .feature-card {
    transition: all 0.3s ease;
    border: 1px solid var(--rule);
  }

  .feature-card:hover {
    border-color: var(--forest);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(26, 58, 47, 0.08);
  }

  /* AI badge glow */
  .ai-badge {
    background: linear-gradient(135deg, var(--forest) 0%, var(--forest-light) 100%);
    color: var(--paper);
    font-size: 0.65rem;
    padding: 0.25rem 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-radius: 2px;
  }

  /* Platform screenshot frame */
  .screenshot-frame {
    background: var(--paper);
    border: 1px solid var(--rule);
    box-shadow: 0 20px 60px rgba(0,0,0,0.1);
  }
`;

// Testimonial data - updated to mention AI features
const testimonials = [
  {
    quote: "The AI Writing Assistant transformed our R01 submissions. It analyzed our Specific Aims against funded examples and identified structural issues we'd missed. Our revision score improved by 15 percentile points.",
    author: "Dr. Sarah Chen",
    title: "Director of Research Development",
    institution: "Stanford School of Medicine",
    initials: "SC",
    stat: { value: "15pt", label: "score improvement" }
  },
  {
    quote: "The compliance scanner caught three formatting errors that would have desk-rejected our NSF CAREER proposal. The kanban pipeline keeps our entire grants office synchronized on 40+ concurrent applications.",
    author: "Prof. Marcus Williams",
    title: "Principal Investigator, Computational Biology",
    institution: "Massachusetts Institute of Technology",
    initials: "MW",
    stat: { value: "40+", label: "applications managed" }
  },
  {
    quote: "GrantRadar's AI eligibility checker saved us from pursuing an NIH K99 we didn't qualify for. The instant analysis with specific recommendations—that's the kind of intelligence we need in a grants office.",
    author: "Dr. Elena Rodriguez",
    title: "Associate Professor of Public Health",
    institution: "Johns Hopkins Bloomberg School",
    initials: "ER",
    stat: { value: "87%", label: "time saved on eligibility" }
  },
];

// AI Features data
const aiFeatures = [
  {
    title: "AI Grant Matching",
    description: "Semantic analysis of 86,000+ federal grants, matched to your research profile with explainable reasoning and confidence scores.",
    icon: "🎯",
  },
  {
    title: "AI Writing Assistant",
    description: "Analyze your Specific Aims against funded examples. Get mechanism-specific feedback on structure, scope, and alignment with funder priorities.",
    icon: "✍️",
  },
  {
    title: "AI Eligibility Checker",
    description: "Instant eligibility analysis with streaming results. Know within seconds if you qualify, with detailed requirement breakdowns.",
    icon: "✓",
  },
  {
    title: "AI Research Chat",
    description: "RAG-powered assistant that answers questions about any grant. Ask about deadlines, requirements, or funded project examples.",
    icon: "💬",
  },
  {
    title: "Compliance Scanner",
    description: "Upload your draft and get instant compliance scores. Font sizes, margins, page limits—all checked against funder requirements.",
    icon: "📋",
  },
  {
    title: "Win Probability",
    description: "ML-powered success estimation based on your career stage, resubmission status, and mechanism-specific success rates.",
    icon: "📊",
  },
];

// Platform features data
const platformFeatures = [
  {
    title: "Kanban Pipeline",
    description: "Drag-and-drop application management from discovery to submission. Track every grant through your custom workflow stages.",
    category: "Management",
  },
  {
    title: "Team Collaboration",
    description: "Role-based access control, shared pipelines, and review workflows. Keep your entire grants office synchronized.",
    category: "Collaboration",
  },
  {
    title: "Google Calendar Sync",
    description: "Automatic deadline synchronization. Every grant deadline appears in your calendar with customizable reminders.",
    category: "Integration",
  },
  {
    title: "Success Analytics",
    description: "Track success rates by mechanism, funder, and category. Identify patterns in your submission history.",
    category: "Analytics",
  },
  {
    title: "Deadline Forecasting",
    description: "ML-powered prediction of upcoming deadlines based on historical patterns and funder fiscal calendars.",
    category: "Intelligence",
  },
  {
    title: "Budget Templates",
    description: "Pre-filled budget templates by mechanism with salary caps, fringe rates, and F&A calculations.",
    category: "Compliance",
  },
];

// Stats with scroll animation
function AnimatedStat({ value, label, suffix = '' }: { value: number; label: string; suffix?: string }) {
  const [count, setCount] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isVisible) {
          setIsVisible(true);
        }
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [isVisible]);

  useEffect(() => {
    if (!isVisible) return;
    const duration = 2000;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeOut * value));
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [isVisible, value]);

  return (
    <div ref={ref} className="text-center">
      <div className="font-display text-5xl md:text-6xl font-semibold tracking-tight" style={{ color: 'var(--forest)' }}>
        {count.toLocaleString()}{suffix}
      </div>
      <div className="mt-2 text-sm uppercase tracking-widest" style={{ color: 'var(--ink-muted)' }}>
        {label}
      </div>
    </div>
  );
}

export function Landing() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <>
      <style>{editorialStyles}</style>
      <div className="editorial-page min-h-screen">
        {/* Paper texture overlay */}
        <div className="fixed inset-0 paper-texture" />

        {/* Navigation */}
        <nav className="relative z-50 border-b" style={{ borderColor: 'var(--rule)', background: 'var(--paper)' }}>
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex items-center justify-between h-20">
              <Link to="/" className="flex items-center gap-3">
                <span className="font-display text-2xl font-semibold tracking-tight" style={{ color: 'var(--forest)' }}>
                  GrantRadar
                </span>
              </Link>

              <div className="hidden md:flex items-center gap-10">
                <a href="#ai-tools" className="editorial-link text-sm">AI Tools</a>
                <a href="#platform" className="editorial-link text-sm">Platform</a>
                <a href="#evidence" className="editorial-link text-sm">Evidence</a>
                <a href="#pricing" className="editorial-link text-sm">Pricing</a>
              </div>

              <div className="flex items-center gap-6">
                <Link to="/auth" className="editorial-link text-sm">
                  Sign in
                </Link>
                <Link to="/auth?mode=signup" className="editorial-btn text-sm">
                  Begin Trial
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative py-20 md:py-28">
          <div className="max-w-6xl mx-auto px-6">
            <div className="grid lg:grid-cols-12 gap-12 lg:gap-8">
              {/* Main headline */}
              <div className="lg:col-span-7 animate-fade-up">
                <div className="editorial-rule-thick w-24 mb-8" />

                <div className="inline-block ai-badge mb-6">
                  AI-Powered Grant Intelligence
                </div>

                <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-medium leading-[1.1] tracking-tight" style={{ color: 'var(--ink)' }}>
                  From discovery
                  <br />
                  to <em className="font-normal" style={{ color: 'var(--forest)' }}>submission</em>
                </h1>

                <p className="mt-8 text-xl md:text-2xl leading-relaxed max-w-2xl" style={{ color: 'var(--ink-light)' }}>
                  The complete grant intelligence platform. AI-powered matching, writing assistance,
                  compliance scanning, and pipeline management—built for research teams.
                </p>

                <div className="mt-12 flex flex-col sm:flex-row gap-4">
                  <Link to="/auth?mode=signup" className="editorial-btn inline-block text-center">
                    Start 14-day trial →
                  </Link>
                  <a href="#ai-tools" className="editorial-btn-outline inline-block text-center">
                    Explore AI tools
                  </a>
                </div>

                <p className="mt-6 text-sm" style={{ color: 'var(--ink-muted)' }}>
                  No credit card required. Full access to all features.
                </p>
              </div>

              {/* Side column - key stats */}
              <div className="lg:col-span-5 lg:border-l lg:pl-8 animate-fade-up delay-2" style={{ borderColor: 'var(--rule)' }}>
                <div className="space-y-10">
                  <div>
                    <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                      Grant Database
                    </div>
                    <div className="font-display text-4xl font-semibold" style={{ color: 'var(--forest)' }}>
                      86,847
                    </div>
                    <div className="text-sm mt-1" style={{ color: 'var(--ink-muted)' }}>
                      active funding opportunities
                    </div>
                  </div>

                  <div className="editorial-rule" />

                  <div>
                    <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                      AI Capabilities
                    </div>
                    <div className="space-y-2 text-sm" style={{ color: 'var(--ink-light)' }}>
                      <div>Semantic Grant Matching</div>
                      <div>Writing & Aims Analysis</div>
                      <div>Compliance Scanning</div>
                      <div>Eligibility Assessment</div>
                    </div>
                  </div>

                  <div className="editorial-rule" />

                  <div>
                    <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                      Data Sources
                    </div>
                    <div className="space-y-2 text-sm" style={{ color: 'var(--ink-light)' }}>
                      <div>NIH Reporter</div>
                      <div>NSF Awards</div>
                      <div>Grants.gov</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Institutions bar */}
        <section className="py-12 border-y" style={{ borderColor: 'var(--rule)', background: 'var(--paper-dark)' }}>
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-8">
              <span className="text-xs uppercase tracking-widest" style={{ color: 'var(--ink-muted)' }}>
                Trusted by research teams at
              </span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
              {['Stanford Medicine', 'MIT', 'Johns Hopkins', 'Duke University', 'UC Berkeley', 'Northwestern'].map((name) => (
                <span key={name} className="font-display text-lg font-medium" style={{ color: 'var(--ink-muted)' }}>
                  {name}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* AI Tools Section */}
        <section id="ai-tools" className="py-24 md:py-32">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                AI-Powered Tools
              </div>
              <h2 className="font-display text-4xl md:text-5xl font-medium" style={{ color: 'var(--ink)' }}>
                Intelligence at every step
              </h2>
              <p className="mt-4 text-lg max-w-2xl mx-auto" style={{ color: 'var(--ink-light)' }}>
                From finding the right opportunity to polishing your submission—AI assistance
                trained on hundreds of thousands of funded proposals.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {aiFeatures.map((feature) => (
                <div
                  key={feature.title}
                  className="feature-card p-8"
                  style={{ background: 'var(--paper)' }}
                >
                  <div className="text-3xl mb-4">{feature.icon}</div>
                  <h3 className="font-display text-xl font-medium mb-3" style={{ color: 'var(--forest)' }}>
                    {feature.title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-light)' }}>
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>

            {/* AI Writing Assistant Feature Highlight */}
            <div className="mt-20 grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                  Featured: AI Writing Assistant
                </div>
                <h3 className="font-display text-3xl font-medium mb-6" style={{ color: 'var(--ink)' }}>
                  Your Specific Aims, analyzed
                </h3>
                <p className="text-lg leading-relaxed mb-6" style={{ color: 'var(--ink-light)' }}>
                  Paste your Specific Aims page and receive instant analysis. Our AI compares your structure,
                  scope, and approach against funded R01, R21, and CAREER proposals.
                </p>
                <ul className="space-y-3">
                  {[
                    'Structural analysis against funded examples',
                    'Mechanism-specific aims count recommendations',
                    'Scope assessment (too broad, too narrow, appropriate)',
                    'Issue detection: circular logic, overlapping aims',
                    'Follow-up Q&A chat for refinement',
                  ].map((item) => (
                    <li key={item} className="flex items-start gap-3 text-sm" style={{ color: 'var(--ink-light)' }}>
                      <span style={{ color: 'var(--forest)' }}>✓</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="screenshot-frame p-6 rounded">
                <div className="aspect-video bg-gradient-to-br rounded" style={{ background: 'linear-gradient(135deg, var(--paper-dark) 0%, var(--rule) 100%)' }}>
                  <div className="p-6">
                    <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                      Aims Analysis
                    </div>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full" style={{ background: 'var(--forest)' }} />
                        <span className="text-sm" style={{ color: 'var(--ink)' }}>Structure Score: 92/100</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full" style={{ background: 'var(--forest)' }} />
                        <span className="text-sm" style={{ color: 'var(--ink)' }}>Scope: Appropriate</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full" style={{ background: 'var(--gold)' }} />
                        <span className="text-sm" style={{ color: 'var(--ink)' }}>1 issue detected</span>
                      </div>
                    </div>
                    <div className="mt-6 p-4 rounded" style={{ background: 'var(--paper)' }}>
                      <p className="text-xs" style={{ color: 'var(--ink-light)' }}>
                        "Aim 3 appears to overlap significantly with Aim 1. Consider consolidating or
                        differentiating the experimental approaches..."
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Platform Features Section */}
        <section id="platform" className="py-24 md:py-32 border-t" style={{ borderColor: 'var(--rule)', background: 'var(--paper-dark)' }}>
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                Platform Capabilities
              </div>
              <h2 className="font-display text-4xl md:text-5xl font-medium" style={{ color: 'var(--ink)' }}>
                Everything your grants office needs
              </h2>
              <p className="mt-4 text-lg max-w-2xl mx-auto" style={{ color: 'var(--ink-light)' }}>
                Beyond discovery—a complete platform for managing applications from start to submission.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {platformFeatures.map((feature) => (
                <div key={feature.title}>
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--gold)' }}>
                    {feature.category}
                  </div>
                  <h3 className="font-display text-xl font-medium mb-2" style={{ color: 'var(--forest)' }}>
                    {feature.title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--ink-light)' }}>
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>

            {/* Kanban Feature Highlight */}
            <div className="mt-20">
              <div className="screenshot-frame p-8 rounded">
                <div className="mb-6">
                  <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--gold)' }}>
                    Application Pipeline
                  </div>
                  <h3 className="font-display text-2xl font-medium" style={{ color: 'var(--ink)' }}>
                    Visualize your entire grants workflow
                  </h3>
                </div>
                <div className="grid grid-cols-5 gap-4">
                  {['Researching', 'Writing', 'Internal Review', 'Submitted', 'Awarded'].map((stage, i) => (
                    <div key={stage}>
                      <div className="text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--ink-muted)' }}>
                        {stage}
                      </div>
                      <div className="space-y-3">
                        {Array.from({ length: Math.max(1, 3 - i) }).map((_, j) => (
                          <div
                            key={j}
                            className="p-3 rounded text-xs"
                            style={{
                              background: 'var(--paper)',
                              border: '1px solid var(--rule)',
                              color: 'var(--ink-light)'
                            }}
                          >
                            <div className="font-medium mb-1" style={{ color: 'var(--ink)' }}>
                              {['NIH R01', 'NSF CAREER', 'NIH K99', 'DOE Early Career', 'NIH R21'][i + j] || 'Grant'}
                            </div>
                            <div>Due {['Mar 15', 'Apr 1', 'Feb 28', 'May 12', 'Jun 5'][i + j] || 'TBD'}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-20 border-y" style={{ borderColor: 'var(--rule)' }}>
          <div className="max-w-6xl mx-auto px-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
              <AnimatedStat value={86847} label="Grants indexed" />
              <AnimatedStat value={94} suffix="%" label="Match accuracy" />
              <AnimatedStat value={847} label="Research teams" />
              <AnimatedStat value={12} label="Hours saved weekly" />
            </div>
          </div>
        </section>

        {/* Evidence / Testimonials */}
        <section id="evidence" className="py-24 md:py-32">
          <div className="max-w-6xl mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                Evidence
              </div>
              <h2 className="font-display text-4xl font-medium" style={{ color: 'var(--ink)' }}>
                What research teams report
              </h2>
            </div>

            <div className="space-y-16">
              {testimonials.map((testimonial, index) => (
                <div key={testimonial.author} className="grid lg:grid-cols-12 gap-8 items-start">
                  {/* Stat - alternating sides */}
                  <div className={`lg:col-span-3 ${index % 2 === 0 ? 'lg:order-1' : 'lg:order-2'}`}>
                    <div className="text-center lg:text-left">
                      <div className="font-display text-5xl font-semibold" style={{ color: 'var(--forest)' }}>
                        {testimonial.stat.value}
                      </div>
                      <div className="text-sm uppercase tracking-wide mt-1" style={{ color: 'var(--ink-muted)' }}>
                        {testimonial.stat.label}
                      </div>
                    </div>
                  </div>

                  {/* Quote */}
                  <div className={`lg:col-span-9 ${index % 2 === 0 ? 'lg:order-2' : 'lg:order-1'}`}>
                    <blockquote className="editorial-quote">
                      <p className="text-xl md:text-2xl leading-relaxed font-display" style={{ color: 'var(--ink)' }}>
                        "{testimonial.quote}"
                      </p>
                      <footer className="mt-6">
                        <div className="flex items-center gap-4">
                          <div
                            className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-medium"
                            style={{ background: 'var(--forest)', color: 'var(--paper)' }}
                          >
                            {testimonial.initials}
                          </div>
                          <div>
                            <div className="font-medium" style={{ color: 'var(--ink)' }}>
                              {testimonial.author}
                            </div>
                            <div className="text-sm" style={{ color: 'var(--ink-muted)' }}>
                              {testimonial.title}
                            </div>
                            <div className="text-sm" style={{ color: 'var(--ink-muted)' }}>
                              {testimonial.institution}
                            </div>
                          </div>
                        </div>
                      </footer>
                    </blockquote>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="py-24 md:py-32 border-t" style={{ borderColor: 'var(--rule)', background: 'var(--paper-dark)' }}>
          <div className="max-w-4xl mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-xs uppercase tracking-widest mb-4" style={{ color: 'var(--gold)' }}>
                Pricing
              </div>
              <h2 className="font-display text-4xl font-medium" style={{ color: 'var(--ink)' }}>
                Full access. No feature gates.
              </h2>
              <p className="mt-4 text-lg" style={{ color: 'var(--ink-light)' }}>
                Every AI tool, every platform feature. One subscription.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              {/* Research Lab */}
              <div className="p-10" style={{ background: 'var(--paper)', border: '1px solid var(--rule)' }}>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--gold)' }}>
                  For research labs
                </div>
                <h3 className="font-display text-2xl font-medium" style={{ color: 'var(--ink)' }}>
                  Lab Subscription
                </h3>

                <div className="mt-6 flex items-baseline">
                  <span className="font-display text-5xl font-semibold" style={{ color: 'var(--forest)' }}>$200</span>
                  <span className="ml-2" style={{ color: 'var(--ink-muted)' }}>/month</span>
                </div>

                <p className="mt-4 text-sm" style={{ color: 'var(--ink-muted)' }}>
                  Beta pricing. Locked in for all early subscribers.
                </p>

                <div className="editorial-rule my-8" />

                <ul className="space-y-3">
                  {[
                    'AI Grant Matching (86k+ grants)',
                    'AI Writing Assistant',
                    'AI Eligibility Checker',
                    'AI Research Chat',
                    'Compliance Scanner',
                    'Kanban Pipeline',
                    'Google Calendar Sync',
                    'Team Collaboration (5 seats)',
                    'Success Analytics',
                    'Budget Templates',
                    'Priority Support',
                  ].map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm" style={{ color: 'var(--ink-light)' }}>
                      <span style={{ color: 'var(--forest)' }}>✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link
                  to="/auth?mode=signup"
                  className="editorial-btn block text-center mt-10 w-full"
                >
                  Start free trial
                </Link>
              </div>

              {/* Institution */}
              <div className="p-10" style={{ background: 'var(--forest)', color: 'var(--paper)' }}>
                <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--gold-light)' }}>
                  For institutions
                </div>
                <h3 className="font-display text-2xl font-medium">
                  Enterprise License
                </h3>

                <div className="mt-6 flex items-baseline">
                  <span className="font-display text-5xl font-semibold">Custom</span>
                </div>

                <p className="mt-4 text-sm" style={{ color: 'rgba(250,248,243,0.7)' }}>
                  Volume pricing for universities and research organizations.
                </p>

                <div className="my-8" style={{ height: '1px', background: 'rgba(250,248,243,0.2)' }} />

                <ul className="space-y-3">
                  {[
                    'Everything in Lab subscription',
                    'Unlimited seats',
                    'Institution-wide profiles',
                    'SSO / SAML authentication',
                    'API access',
                    'Custom review workflows',
                    'Advanced analytics',
                    'Slack integration',
                    'Dedicated success manager',
                    'Custom onboarding',
                    'SLA guarantee',
                  ].map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(250,248,243,0.85)' }}>
                      <span style={{ color: 'var(--gold-light)' }}>✓</span>
                      {feature}
                    </li>
                  ))}
                </ul>

                <a
                  href="mailto:enterprise@grantradar.com"
                  className="block text-center mt-10 w-full py-4 px-6 font-medium"
                  style={{
                    background: 'var(--paper)',
                    color: 'var(--forest)',
                    transition: 'all 0.3s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--paper-dark)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'var(--paper)';
                  }}
                >
                  Contact sales →
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 md:py-32">
          <div className="max-w-3xl mx-auto px-6 text-center">
            <h2 className="font-display text-4xl md:text-5xl font-medium leading-tight" style={{ color: 'var(--ink)' }}>
              Stop searching.
              <br />
              <em style={{ color: 'var(--forest)' }}>Start winning.</em>
            </h2>

            <p className="mt-6 text-xl" style={{ color: 'var(--ink-light)' }}>
              Join 847 research labs using AI-powered grant intelligence to find,
              write, and win more funding.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/auth?mode=signup" className="editorial-btn">
                Start your free trial →
              </Link>
              <a href="mailto:hello@grantradar.com" className="editorial-btn-outline">
                Schedule a demo
              </a>
            </div>

            <p className="mt-8 text-sm" style={{ color: 'var(--ink-muted)' }}>
              14-day trial · No credit card required · All features included
            </p>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t" style={{ borderColor: 'var(--rule)' }}>
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="font-display text-xl font-semibold" style={{ color: 'var(--forest)' }}>
                GrantRadar
              </div>

              <div className="flex items-center gap-8 text-sm" style={{ color: 'var(--ink-muted)' }}>
                <Link to="/about" className="editorial-link">About</Link>
                <Link to="/faq" className="editorial-link">FAQ</Link>
                <Link to="/privacy" className="editorial-link">Privacy</Link>
                <Link to="/terms" className="editorial-link">Terms</Link>
                <a href="mailto:support@grantradar.com" className="editorial-link">Contact</a>
              </div>

              <p className="text-sm" style={{ color: 'var(--ink-muted)' }}>
                © {new Date().getFullYear()} GrantRadar
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

export default Landing;
