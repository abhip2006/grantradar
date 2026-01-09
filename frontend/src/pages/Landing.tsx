import { Link, Navigate } from 'react-router-dom';
import {
  ArrowRightIcon,
  SparklesIcon,
  BellAlertIcon,
  ChartBarSquareIcon,
  ShieldCheckIcon,
  CheckIcon,
  SignalIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';

/* ═══════════════════════════════════════════════════════════════════════════
   GRANTRADAR LANDING PAGE
   Aesthetic: Clean Modern - Blue, Yellow, White
   ═══════════════════════════════════════════════════════════════════════════ */

// Radar Animation Component
function RadarVisualization() {
  return (
    <div className="relative w-[500px] h-[500px] flex items-center justify-center">
      {/* Grid Pattern Background */}
      <div className="absolute inset-0 grid-pattern opacity-50" />

      {/* Concentric Rings */}
      <div className="radar-ring radar-ring-1" />
      <div className="radar-ring radar-ring-2" />
      <div className="radar-ring radar-ring-3" />
      <div className="radar-ring radar-ring-4" />

      {/* Radar Sweep Line */}
      <div className="radar-sweep" />

      {/* Central Pulse */}
      <div className="radar-pulse" />

      {/* Grant Dots - positioned around radar */}
      <div className="radar-dot" style={{ top: '15%', left: '60%', animationDelay: '0s' }} />
      <div className="radar-dot" style={{ top: '35%', left: '78%', animationDelay: '0.3s' }} />
      <div className="radar-dot" style={{ top: '65%', left: '72%', animationDelay: '0.6s' }} />
      <div className="radar-dot" style={{ top: '75%', left: '40%', animationDelay: '0.9s' }} />
      <div className="radar-dot" style={{ top: '45%', left: '22%', animationDelay: '1.2s' }} />

      {/* Floating Grant Cards */}
      <div
        className="absolute top-[10%] right-[-10%] bg-white border border-[var(--gr-border-default)] rounded-xl p-4 shadow-lg animate-fade-in-up stagger-2"
        style={{ width: '200px' }}
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-[var(--gr-green-500)] flex items-center justify-center text-sm font-bold text-white">
            94
          </div>
          <div className="flex-1">
            <div className="text-xs text-[var(--gr-green-600)] font-semibold uppercase tracking-wider">High Match</div>
          </div>
        </div>
        <div className="text-sm font-medium text-[var(--gr-text-primary)]">NSF Research Grant</div>
        <div className="text-xs text-[var(--gr-text-tertiary)] mt-1">$250K - $500K</div>
      </div>

      <div
        className="absolute bottom-[15%] left-[-15%] bg-white border border-[var(--gr-border-default)] rounded-xl p-4 shadow-lg animate-fade-in-up stagger-4"
        style={{ width: '180px' }}
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-[var(--gr-yellow-400)] flex items-center justify-center text-sm font-bold text-[var(--gr-gray-900)]">
            87
          </div>
          <div className="flex-1">
            <div className="text-xs text-[var(--gr-yellow-600)] font-semibold uppercase tracking-wider">Good Match</div>
          </div>
        </div>
        <div className="text-sm font-medium text-[var(--gr-text-primary)]">Ford Foundation</div>
        <div className="text-xs text-[var(--gr-text-tertiary)] mt-1">$100K - $200K</div>
      </div>
    </div>
  );
}

const features = [
  {
    name: 'AI-Powered Matching',
    description: 'We analyze grant requirements, eligibility criteria, and funding amounts against your organization\'s mission and focus areas.',
    icon: SparklesIcon,
    color: 'blue',
  },
  {
    name: 'Federal Grant Coverage',
    description: 'Daily updates from NIH, NSF, and Grants.gov. New opportunities indexed within 24 hours of posting.',
    icon: SignalIcon,
    color: 'yellow',
  },
  {
    name: 'Smart Alerts',
    description: 'Personalized notifications based on score thresholds and approaching deadlines.',
    icon: BellAlertIcon,
    color: 'green',
  },
  {
    name: 'Match Intelligence',
    description: 'Detailed breakdowns explain exactly why each grant matches your organization.',
    icon: ChartBarSquareIcon,
    color: 'blue',
  },
];

const stats = [
  { value: '86,000+', label: 'Grants Indexed', sublabel: 'NIH, NSF, Grants.gov' },
  { value: '3', label: 'Federal Sources', sublabel: 'Major grant databases' },
  { value: '<5 min', label: 'To First Match', sublabel: 'After profile setup' },
  { value: 'Daily', label: 'Data Updates', sublabel: 'Always current' },
];

const pricingTiers = [
  {
    name: 'Beta Access',
    price: 200,
    period: '/month',
    description: 'Early adopter pricing. Lock in forever.',
    features: [
      'Unlimited grant matches',
      'Federal & foundation grants',
      'Real-time notifications',
      'Match score insights',
      'Email & SMS alerts',
      'Priority support',
    ],
    cta: 'Start Free Trial',
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations & teams.',
    features: [
      'Everything in Beta',
      'State grant coverage',
      'Team collaboration',
      'API access',
      'Custom integrations',
      'Dedicated success manager',
    ],
    cta: 'Contact Sales',
    featured: false,
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();

  // Redirect authenticated users to dashboard - they don't need the marketing page
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-md border-b border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[var(--gr-blue-600)] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg font-display">G</span>
            </div>
            <span className="text-xl font-display font-semibold text-[var(--gr-text-primary)]">
              GrantRadar
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors">
              Features
            </a>
            <a href="#pricing" className="text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors">
              Pricing
            </a>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/auth"
              className="text-sm font-medium text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] transition-colors"
            >
              Sign In
            </Link>
            <Link to="/auth?mode=signup" className="btn-primary">
              Start Free Trial
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 overflow-hidden bg-[var(--gr-gray-50)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left Content */}
            <div className="relative z-10">
              <div className="animate-fade-in-up">
                <span className="badge badge-yellow">
                  <span className="w-2 h-2 rounded-full bg-[var(--gr-yellow-500)] animate-pulse" />
                  Beta Launch - $200/mo
                </span>
              </div>

              <h1 className="mt-8 text-5xl lg:text-6xl font-display font-medium text-[var(--gr-text-primary)] leading-[1.1] animate-fade-in-up stagger-1">
                Find grants that{' '}
                <span className="text-[var(--gr-blue-600)]">
                  actually match
                </span>{' '}
                your mission
              </h1>

              <p className="mt-6 text-lg text-[var(--gr-text-secondary)] leading-relaxed max-w-xl animate-fade-in-up stagger-2">
                Stop wasting hours on irrelevant opportunities. GrantRadar uses AI to continuously
                scan thousands of sources and surface the grants that fit your organization's
                focus, eligibility, and funding needs.
              </p>

              <div className="mt-10 flex flex-wrap items-center gap-4 animate-fade-in-up stagger-3">
                <Link to="/auth?mode=signup" className="btn-primary">
                  Start 14-Day Free Trial
                  <ArrowRightIcon className="w-4 h-4" />
                </Link>
                <a href="#features" className="btn-secondary">
                  See How It Works
                </a>
              </div>

              <div className="mt-12 flex items-center gap-8 animate-fade-in-up stagger-4">
                <div className="flex items-center gap-2">
                  <ShieldCheckIcon className="w-5 h-5 text-[var(--gr-green-500)]" />
                  <span className="text-sm text-[var(--gr-text-secondary)]">No credit card required</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckIcon className="w-5 h-5 text-[var(--gr-green-500)]" />
                  <span className="text-sm text-[var(--gr-text-secondary)]">Cancel anytime</span>
                </div>
              </div>
            </div>

            {/* Right - Radar Visualization */}
            <div className="relative hidden lg:flex items-center justify-center">
              <RadarVisualization />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="relative py-20 bg-white border-y border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div
                key={stat.label}
                className={`text-center animate-fade-in-up stagger-${index + 1}`}
              >
                <div className="text-4xl lg:text-5xl font-display font-semibold text-[var(--gr-blue-600)]">
                  {stat.value}
                </div>
                <div className="mt-2 text-[var(--gr-text-primary)] font-medium">
                  {stat.label}
                </div>
                <div className="text-sm text-[var(--gr-text-tertiary)]">
                  {stat.sublabel}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="badge badge-blue">Grant Intelligence</span>
            <h2 className="mt-6 text-4xl font-display font-medium text-[var(--gr-text-primary)]">
              Built for serious grant seekers
            </h2>
            <p className="mt-4 text-lg text-[var(--gr-text-secondary)]">
              Our platform goes beyond simple keyword matching. We understand your
              organization's nuances and find opportunities others miss.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((feature, index) => {
              const colorMap: Record<string, { bg: string; icon: string; border: string }> = {
                blue: { bg: 'bg-[var(--gr-blue-50)]', icon: 'text-[var(--gr-blue-600)]', border: 'border-l-[var(--gr-blue-500)]' },
                yellow: { bg: 'bg-[var(--gr-yellow-50)]', icon: 'text-[var(--gr-yellow-600)]', border: 'border-l-[var(--gr-yellow-400)]' },
                green: { bg: 'bg-green-50', icon: 'text-[var(--gr-green-600)]', border: 'border-l-[var(--gr-green-500)]' },
              };
              const colors = colorMap[feature.color] || colorMap.blue;

              return (
                <div
                  key={feature.name}
                  className={`card border-l-4 ${colors.border} animate-fade-in-up stagger-${index + 1}`}
                >
                  <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center mb-6`}>
                    <feature.icon className={`w-6 h-6 ${colors.icon}`} />
                  </div>
                  <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-3">
                    {feature.name}
                  </h3>
                  <p className="text-[var(--gr-text-secondary)] leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 bg-[var(--gr-gray-50)] border-y border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-4xl font-display font-medium text-[var(--gr-text-primary)]">
              Three steps to better funding
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Build Your Profile',
                description: 'Tell us about your organization, focus areas, and eligibility criteria. Takes under 5 minutes.',
              },
              {
                step: '02',
                title: 'We Scan Everything',
                description: 'Our AI analyzes 86,000+ grants from NIH, NSF, and Grants.gov, scoring each against your profile.',
              },
              {
                step: '03',
                title: 'Get Matched',
                description: 'Receive curated grants ranked by match score, with detailed explanations of why each one fits.',
              },
            ].map((item, index) => (
              <div key={item.step} className={`relative animate-fade-in-up stagger-${index + 1}`}>
                <div className="text-7xl font-display font-bold text-[var(--gr-gray-200)] absolute -top-4 -left-2">
                  {item.step}
                </div>
                <div className="relative pt-12">
                  <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-3">
                    {item.title}
                  </h3>
                  <p className="text-[var(--gr-text-secondary)]">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="badge badge-green">Simple Pricing</span>
            <h2 className="mt-6 text-4xl font-display font-medium text-[var(--gr-text-primary)]">
              Transparent. No surprises.
            </h2>
            <p className="mt-4 text-lg text-[var(--gr-text-secondary)]">
              Lock in beta pricing forever. Cancel anytime.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {pricingTiers.map((tier, index) => (
              <div
                key={tier.name}
                className={`relative p-8 rounded-2xl animate-fade-in-up stagger-${index + 1} ${
                  tier.featured
                    ? 'bg-[var(--gr-blue-50)] border-2 border-[var(--gr-blue-200)]'
                    : 'bg-white border border-[var(--gr-border-default)]'
                }`}
              >
                {tier.featured && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 bg-[var(--gr-blue-600)] text-white text-xs font-bold rounded-full uppercase tracking-wider">
                      Most Popular
                    </span>
                  </div>
                )}

                <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                  {tier.name}
                </h3>

                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-5xl font-display font-semibold text-[var(--gr-text-primary)]">
                    {typeof tier.price === 'number' ? `$${tier.price}` : tier.price}
                  </span>
                  <span className="text-[var(--gr-text-tertiary)]">{tier.period}</span>
                </div>

                <p className="mt-2 text-sm text-[var(--gr-text-secondary)]">
                  {tier.description}
                </p>

                <ul className="mt-8 space-y-4">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <CheckIcon className={`w-5 h-5 flex-shrink-0 ${tier.featured ? 'text-[var(--gr-blue-600)]' : 'text-[var(--gr-green-500)]'}`} />
                      <span className="text-[var(--gr-text-secondary)]">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  to={tier.featured ? '/auth?mode=signup' : '#'}
                  className={`mt-8 block text-center py-3 px-6 rounded-xl font-medium transition-all ${
                    tier.featured
                      ? 'btn-primary w-full justify-center'
                      : 'btn-secondary w-full justify-center'
                  }`}
                >
                  {tier.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24 bg-[var(--gr-gray-50)] border-t border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="badge badge-blue">Beta Feedback</span>
            <h2 className="mt-6 text-4xl font-display font-medium text-[var(--gr-text-primary)]">
              What researchers are saying
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                quote: "Finally, a grant search tool that understands my research focus. The match scores actually make sense.",
                author: "Beta Tester",
                role: "Research University",
              },
              {
                quote: "Saved me hours of searching through Grants.gov. I found two relevant NIH grants in my first week.",
                author: "Beta Tester",
                role: "Nonprofit Organization",
              },
              {
                quote: "The deadline reminders alone are worth it. No more missed opportunities due to scattered tracking.",
                author: "Beta Tester",
                role: "Academic Institution",
              },
            ].map((testimonial, index) => (
              <div
                key={index}
                className={`card animate-fade-in-up stagger-${index + 1}`}
              >
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-5 h-5 text-[var(--gr-yellow-400)]" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <p className="text-[var(--gr-text-secondary)] mb-6 leading-relaxed">
                  "{testimonial.quote}"
                </p>
                <div className="border-t border-[var(--gr-border-subtle)] pt-4">
                  <div className="text-sm font-medium text-[var(--gr-text-primary)]">
                    {testimonial.author}
                  </div>
                  <div className="text-xs text-[var(--gr-text-tertiary)]">
                    {testimonial.role}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 bg-white border-t border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="relative overflow-hidden rounded-3xl bg-[var(--gr-blue-600)] p-12 lg:p-16">
            {/* Decorative elements */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

            <div className="relative z-10 max-w-2xl">
              <h2 className="text-4xl lg:text-5xl font-display font-medium text-white">
                Ready to find your next grant?
              </h2>
              <p className="mt-4 text-lg text-white/80">
                Start your 14-day free trial. No credit card required.
                Join researchers already discovering funding faster.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link
                  to="/auth?mode=signup"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[var(--gr-blue-600)] font-semibold rounded-xl hover:bg-[var(--gr-gray-50)] transition-colors"
                >
                  Start Free Trial
                  <ArrowRightIcon className="w-4 h-4" />
                </Link>
                <Link
                  to="/auth"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-transparent text-white font-semibold rounded-xl border-2 border-white/30 hover:border-white/50 transition-colors"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-white border-t border-[var(--gr-border-default)]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[var(--gr-blue-600)] rounded-lg flex items-center justify-center">
                <span className="text-white font-bold font-display">G</span>
              </div>
              <span className="font-display font-medium text-[var(--gr-text-primary)]">GrantRadar</span>
            </div>

            <div className="flex items-center gap-8 text-sm text-[var(--gr-text-tertiary)]">
              <Link to="/about" className="hover:text-[var(--gr-text-secondary)] transition-colors">About</Link>
              <Link to="/pricing" className="hover:text-[var(--gr-text-secondary)] transition-colors">Pricing</Link>
              <Link to="/faq" className="hover:text-[var(--gr-text-secondary)] transition-colors">FAQ</Link>
              <Link to="/privacy" className="hover:text-[var(--gr-text-secondary)] transition-colors">Privacy</Link>
              <Link to="/terms" className="hover:text-[var(--gr-text-secondary)] transition-colors">Terms</Link>
              <Link to="/contact" className="hover:text-[var(--gr-text-secondary)] transition-colors">Contact</Link>
            </div>

            <p className="text-sm text-[var(--gr-text-tertiary)]">
              &copy; {new Date().getFullYear()} GrantRadar. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Landing;
