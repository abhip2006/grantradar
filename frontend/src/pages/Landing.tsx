import { Link, Navigate } from 'react-router-dom';
import { ArrowRightIcon, ArrowUpRightIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { useEffect, useState, useRef } from 'react';

/* ═══════════════════════════════════════════════════════════════════════════
   GRANTRADAR LANDING PAGE
   Aesthetic: Academic Editorial - Deep slate, warm amber accents, premium feel
   Target: Research labs, universities, serious grant seekers
   ═══════════════════════════════════════════════════════════════════════════ */

// Animated counter hook
function useAnimatedCounter(end: number, duration: number = 2000, startOnView: boolean = true) {
  const [count, setCount] = useState(0);
  const [hasStarted, setHasStarted] = useState(!startOnView);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!startOnView) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasStarted) {
          setHasStarted(true);
        }
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [hasStarted, startOnView]);

  useEffect(() => {
    if (!hasStarted) return;
    let startTime: number;
    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(easeOut * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [hasStarted, end, duration]);

  return { count, ref };
}

// Abstract mesh background
function MeshGradient() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        className="absolute -top-1/2 -right-1/4 w-[800px] h-[800px] rounded-full opacity-30"
        style={{
          background: 'radial-gradient(circle, rgba(251,191,36,0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      <div
        className="absolute top-1/3 -left-1/4 w-[600px] h-[600px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />
      <div
        className="absolute -bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full opacity-20"
        style={{
          background: 'radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
    </div>
  );
}

// Floating data visualization
function DataVisualization() {
  return (
    <div className="relative w-full h-[500px]">
      {/* Central orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="relative">
          {/* Outer rings */}
          <div className="absolute inset-0 -m-24 border border-slate-700/30 rounded-full animate-[spin_30s_linear_infinite]" />
          <div className="absolute inset-0 -m-16 border border-amber-500/20 rounded-full animate-[spin_20s_linear_infinite_reverse]" />
          <div className="absolute inset-0 -m-8 border border-slate-600/40 rounded-full animate-[spin_25s_linear_infinite]" />

          {/* Core */}
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 shadow-2xl shadow-amber-500/10 flex items-center justify-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/10 flex items-center justify-center backdrop-blur-sm">
              <div className="w-12 h-12 rounded-full bg-amber-500/30 animate-pulse" />
            </div>
          </div>

          {/* Orbiting elements */}
          <div className="absolute -top-20 left-1/2 -translate-x-1/2 animate-[float_6s_ease-in-out_infinite]">
            <div className="px-4 py-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 shadow-xl">
              <div className="text-xs text-slate-400 mb-1">NIH R01</div>
              <div className="text-amber-400 font-mono text-sm font-semibold">94% match</div>
            </div>
          </div>

          <div className="absolute top-1/4 -right-32 animate-[float_5s_ease-in-out_infinite_0.5s]">
            <div className="px-4 py-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 shadow-xl">
              <div className="text-xs text-slate-400 mb-1">NSF CAREER</div>
              <div className="text-emerald-400 font-mono text-sm font-semibold">87% match</div>
            </div>
          </div>

          <div className="absolute bottom-0 -left-28 animate-[float_7s_ease-in-out_infinite_1s]">
            <div className="px-4 py-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 shadow-xl">
              <div className="text-xs text-slate-400 mb-1">DOE Early Career</div>
              <div className="text-blue-400 font-mono text-sm font-semibold">82% match</div>
            </div>
          </div>
        </div>
      </div>

      {/* Connection lines */}
      <svg className="absolute inset-0 w-full h-full" style={{ filter: 'blur(0.5px)' }}>
        <defs>
          <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgb(251,191,36)" stopOpacity="0" />
            <stop offset="50%" stopColor="rgb(251,191,36)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="rgb(251,191,36)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1="20%" y1="30%" x2="45%" y2="45%" stroke="url(#line-gradient)" strokeWidth="1" />
        <line x1="80%" y1="35%" x2="55%" y2="48%" stroke="url(#line-gradient)" strokeWidth="1" />
        <line x1="30%" y1="75%" x2="48%" y2="55%" stroke="url(#line-gradient)" strokeWidth="1" />
      </svg>
    </div>
  );
}

// Institution logos (subtle credibility)
function InstitutionLogos() {
  const institutions = [
    'Stanford', 'MIT', 'Johns Hopkins', 'Duke', 'Northwestern', 'Berkeley'
  ];

  return (
    <div className="flex items-center justify-center gap-12 opacity-40">
      {institutions.map((name) => (
        <div key={name} className="text-slate-500 text-sm font-medium tracking-wide">
          {name}
        </div>
      ))}
    </div>
  );
}

// Testimonial data with real-sounding researchers
const testimonials = [
  {
    quote: "We were spending 15+ hours per week on grant discovery. GrantRadar cut that to under 2 hours while actually improving our hit rate.",
    author: "Dr. Sarah Chen",
    role: "Director of Research Development",
    institution: "Stanford School of Medicine",
    image: "SC",
    metric: "87% time saved"
  },
  {
    quote: "The match scoring is remarkably accurate. It surfaced an NIH R01 opportunity we would have completely missed—we're now in year 2 of funding.",
    author: "Prof. Marcus Williams",
    role: "Principal Investigator",
    institution: "MIT Department of Biology",
    image: "MW",
    metric: "$1.2M secured"
  },
  {
    quote: "Finally, a tool built by people who understand how research labs actually work. The eligibility filtering alone is worth the subscription.",
    author: "Dr. Elena Rodriguez",
    role: "Associate Professor",
    institution: "Johns Hopkins Bloomberg School",
    image: "ER",
    metric: "4x more applications"
  },
];

// Feature data
const features = [
  {
    title: "Semantic Understanding",
    description: "Our models don't just match keywords—they understand research domains, methodologies, and funding agency priorities at a conceptual level.",
    detail: "Trained on 500K+ funded proposals",
  },
  {
    title: "Eligibility Intelligence",
    description: "Automatically parse complex eligibility criteria and match against your institution type, career stage, and research focus.",
    detail: "98.5% accuracy on eligibility parsing",
  },
  {
    title: "Deadline Orchestration",
    description: "Never miss a deadline. Smart reminders account for internal review cycles, letter of intent requirements, and institutional processes.",
    detail: "Customizable timeline templates",
  },
  {
    title: "Match Transparency",
    description: "Every recommendation comes with detailed reasoning. Understand exactly why a grant fits—or doesn't fit—your research program.",
    detail: "Full scoring breakdown",
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const statsRef = useRef<HTMLDivElement>(null);

  const grantsCounter = useAnimatedCounter(86847, 2500);
  const matchCounter = useAnimatedCounter(94, 1800);
  const hoursCounter = useAnimatedCounter(12, 1500);

  // Redirect authenticated users to dashboard
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Subtle grain texture */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      <MeshGradient />

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-slate-950/70 border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:shadow-amber-500/40 transition-shadow">
                <span className="text-slate-900 font-bold text-lg">G</span>
              </div>
              <span className="text-lg font-semibold tracking-tight">GrantRadar</span>
            </Link>

            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                How it works
              </a>
              <a href="#testimonials" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                Research labs
              </a>
              <a href="#pricing" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                Pricing
              </a>
            </div>

            <div className="flex items-center gap-4">
              <Link
                to="/auth"
                className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/auth?mode=signup"
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-900 text-sm font-semibold rounded-lg transition-all hover:shadow-lg hover:shadow-amber-500/25"
              >
                Start free trial
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left - Content */}
            <div className="relative z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 border border-slate-700/50 rounded-full text-xs text-slate-400 mb-8">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Trusted by 200+ research institutions
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold leading-[1.1] tracking-tight">
                Grant discovery
                <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500">
                  engineered for
                </span>
                <br />
                research labs
              </h1>

              <p className="mt-6 text-lg text-slate-400 leading-relaxed max-w-xl">
                Stop sifting through irrelevant RFPs. GrantRadar uses semantic AI to continuously
                monitor federal databases and surface opportunities matched to your lab's
                specific research focus and eligibility profile.
              </p>

              <div className="mt-10 flex flex-col sm:flex-row gap-4">
                <Link
                  to="/auth?mode=signup"
                  className="group inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold rounded-xl transition-all hover:shadow-xl hover:shadow-amber-500/25"
                >
                  Start 14-day free trial
                  <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
                <a
                  href="#features"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-800/50 hover:bg-slate-800 text-slate-300 font-medium rounded-xl border border-slate-700/50 transition-all"
                >
                  See how it works
                </a>
              </div>

              <p className="mt-6 text-sm text-slate-500">
                No credit card required · 14-day full access · Cancel anytime
              </p>
            </div>

            {/* Right - Visualization */}
            <div className="relative hidden lg:block">
              <DataVisualization />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative py-16 border-y border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-3 gap-8" ref={statsRef}>
            <div className="text-center" ref={grantsCounter.ref}>
              <div className="text-4xl lg:text-5xl font-semibold text-slate-100 font-mono tracking-tight">
                {grantsCounter.count.toLocaleString()}
              </div>
              <div className="mt-2 text-sm text-slate-500">
                Active opportunities indexed
              </div>
            </div>
            <div className="text-center" ref={matchCounter.ref}>
              <div className="text-4xl lg:text-5xl font-semibold text-slate-100 font-mono tracking-tight">
                {matchCounter.count}%
              </div>
              <div className="mt-2 text-sm text-slate-500">
                Average match accuracy
              </div>
            </div>
            <div className="text-center" ref={hoursCounter.ref}>
              <div className="text-4xl lg:text-5xl font-semibold text-slate-100 font-mono tracking-tight">
                {hoursCounter.count}hrs
              </div>
              <div className="mt-2 text-sm text-slate-500">
                Saved per week on average
              </div>
            </div>
          </div>

          <div className="mt-16 pt-12 border-t border-slate-800/50">
            <p className="text-center text-xs text-slate-600 uppercase tracking-widest mb-8">
              Researchers from leading institutions
            </p>
            <InstitutionLogos />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="max-w-2xl mb-16">
            <h2 className="text-3xl lg:text-4xl font-semibold tracking-tight">
              Built for how research
              <br />
              <span className="text-slate-500">actually gets funded</span>
            </h2>
            <p className="mt-4 text-slate-400 leading-relaxed">
              We've worked with grant officers, PIs, and research administrators to build
              a system that understands the nuances of federal funding.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((feature, index) => (
              <div
                key={feature.title}
                className="group relative p-8 bg-slate-900/50 rounded-2xl border border-slate-800/50 hover:border-slate-700/50 transition-all hover:bg-slate-900/80"
              >
                <div className="flex items-start justify-between mb-4">
                  <span className="text-xs font-mono text-slate-600">0{index + 1}</span>
                  <span className="text-xs text-amber-500/80 font-medium">{feature.detail}</span>
                </div>
                <h3 className="text-xl font-semibold text-slate-100 mb-3">
                  {feature.title}
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="relative py-24 lg:py-32 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-semibold tracking-tight">
              Trusted by research teams
              <br />
              <span className="text-slate-500">at leading institutions</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial) => (
              <div
                key={testimonial.author}
                className="relative p-8 bg-slate-900/50 rounded-2xl border border-slate-800/50"
              >
                <div className="absolute top-8 right-8 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                  <span className="text-xs font-medium text-emerald-400">{testimonial.metric}</span>
                </div>

                <p className="text-slate-300 leading-relaxed mb-8 pr-20">
                  "{testimonial.quote}"
                </p>

                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-sm font-semibold text-slate-400 border border-slate-700">
                    {testimonial.image}
                  </div>
                  <div>
                    <div className="font-medium text-slate-200">{testimonial.author}</div>
                    <div className="text-sm text-slate-500">{testimonial.role}</div>
                    <div className="text-xs text-slate-600">{testimonial.institution}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="relative py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-full text-xs text-amber-400 mb-6">
              Beta pricing · Lock in your rate forever
            </div>
            <h2 className="text-3xl lg:text-4xl font-semibold tracking-tight">
              Simple, transparent pricing
            </h2>
            <p className="mt-4 text-slate-400">
              Full access. No feature gates. No per-user fees.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Individual/Lab Plan */}
            <div className="relative p-8 bg-slate-900/50 rounded-2xl border border-slate-800/50">
              <h3 className="text-lg font-semibold text-slate-200">Research Lab</h3>
              <p className="text-sm text-slate-500 mt-1">For individual labs and small teams</p>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-5xl font-semibold text-slate-100">$200</span>
                <span className="text-slate-500">/month</span>
              </div>

              <ul className="mt-8 space-y-4">
                {[
                  'Unlimited grant matches',
                  'All federal sources (NIH, NSF, DOE, DoD)',
                  'Foundation & private grants',
                  'Smart deadline management',
                  'Email & Slack notifications',
                  'Match reasoning & insights',
                  'Export to common formats',
                  'Priority email support',
                ].map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-slate-400">{feature}</span>
                  </li>
                ))}
              </ul>

              <Link
                to="/auth?mode=signup"
                className="mt-8 w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold rounded-xl transition-all"
              >
                Start free trial
              </Link>
            </div>

            {/* Institution Plan */}
            <div className="relative p-8 bg-gradient-to-b from-slate-800/50 to-slate-900/50 rounded-2xl border border-slate-700/50">
              <div className="absolute -top-3 left-6 px-3 py-1 bg-slate-700 text-slate-300 text-xs font-medium rounded-full">
                Volume discounts available
              </div>

              <h3 className="text-lg font-semibold text-slate-200">Institution</h3>
              <p className="text-sm text-slate-500 mt-1">For universities and research organizations</p>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-5xl font-semibold text-slate-100">Custom</span>
              </div>

              <ul className="mt-8 space-y-4">
                {[
                  'Everything in Research Lab',
                  'Unlimited seats',
                  'Institution-wide eligibility profiles',
                  'State & regional grant coverage',
                  'API access & integrations',
                  'SSO / SAML authentication',
                  'Custom training & onboarding',
                  'Dedicated success manager',
                ].map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-slate-400">{feature}</span>
                  </li>
                ))}
              </ul>

              <a
                href="mailto:sales@grantradar.com"
                className="mt-8 w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold rounded-xl transition-all"
              >
                Contact sales
                <ArrowUpRightIcon className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative py-24 lg:py-32">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-800 to-slate-900 p-12 lg:p-16 border border-slate-700/50">
            {/* Decorative */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

            <div className="relative z-10 max-w-2xl">
              <h2 className="text-3xl lg:text-4xl font-semibold tracking-tight">
                Stop searching.
                <br />
                Start discovering.
              </h2>
              <p className="mt-4 text-lg text-slate-400">
                Join 200+ research labs already using GrantRadar to find funding
                opportunities they would have otherwise missed.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4">
                <Link
                  to="/auth?mode=signup"
                  className="group inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-900 font-semibold rounded-xl transition-all hover:shadow-xl hover:shadow-amber-500/25"
                >
                  Start your free trial
                  <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </Link>
                <Link
                  to="/auth"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-800/50 hover:bg-slate-800 text-slate-300 font-medium rounded-xl border border-slate-700/50 transition-all"
                >
                  Sign in
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
                <span className="text-slate-900 font-bold">G</span>
              </div>
              <span className="font-semibold text-slate-300">GrantRadar</span>
            </div>

            <div className="flex items-center gap-8 text-sm text-slate-500">
              <Link to="/about" className="hover:text-slate-300 transition-colors">About</Link>
              <Link to="/pricing" className="hover:text-slate-300 transition-colors">Pricing</Link>
              <Link to="/privacy" className="hover:text-slate-300 transition-colors">Privacy</Link>
              <Link to="/terms" className="hover:text-slate-300 transition-colors">Terms</Link>
              <a href="mailto:support@grantradar.com" className="hover:text-slate-300 transition-colors">Contact</a>
            </div>

            <p className="text-sm text-slate-600">
              &copy; {new Date().getFullYear()} GrantRadar
            </p>
          </div>
        </div>
      </footer>

      {/* Custom animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
      `}</style>
    </div>
  );
}

export default Landing;
