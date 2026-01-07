import { Link } from 'react-router-dom';
import {
  SparklesIcon,
  LightBulbIcon,
  HeartIcon,
  ShieldCheckIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline';

export function About() {
  const values = [
    {
      icon: LightBulbIcon,
      title: 'Transparency',
      description: 'We believe in honest, verifiable claims. Our matching is explainable, not a black box.',
      color: 'yellow',
    },
    {
      icon: HeartIcon,
      title: 'Mission-Driven',
      description: 'We exist to help organizations that make the world better find the funding they deserve.',
      color: 'green',
    },
    {
      icon: ShieldCheckIcon,
      title: 'Privacy First',
      description: 'Your data is yours. We never sell your information to third parties.',
      color: 'blue',
    },
    {
      icon: RocketLaunchIcon,
      title: 'Continuous Improvement',
      description: 'We\'re constantly improving our algorithms and expanding our grant coverage.',
      color: 'blue',
    },
  ];

  const dataSources = [
    {
      name: 'NIH Reporter',
      description: 'National Institutes of Health research funding opportunities',
      count: '50,000+',
      url: 'https://reporter.nih.gov',
    },
    {
      name: 'NSF Awards',
      description: 'National Science Foundation grants and fellowships',
      count: '25,000+',
      url: 'https://www.nsf.gov',
    },
    {
      name: 'Grants.gov',
      description: 'Federal grant opportunities across all agencies',
      count: '10,000+',
      url: 'https://www.grants.gov',
    },
    {
      name: 'Foundation Grants',
      description: 'Private foundation funding (coming soon)',
      count: 'Coming Soon',
      url: null,
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Hero Section */}
      <section className="relative py-20 bg-[var(--gr-gray-50)] border-b border-[var(--gr-border-default)]">
        <div className="max-w-4xl mx-auto px-6">
          <div className="animate-fade-in-up">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors mb-8"
            >
              &larr; Back to Home
            </Link>
            <h1 className="text-4xl lg:text-5xl font-display font-medium text-[var(--gr-text-primary)] leading-tight">
              Helping researchers find funding{' '}
              <span className="text-[var(--gr-blue-600)]">faster</span>
            </h1>
            <p className="mt-6 text-xl text-[var(--gr-text-secondary)] leading-relaxed max-w-3xl">
              GrantRadar was built to solve a simple problem: researchers spend too much time
              searching for grants and not enough time doing research.
            </p>
          </div>
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="animate-fade-in-up">
              <span className="badge badge-blue">Our Mission</span>
              <h2 className="mt-6 text-3xl font-display font-medium text-[var(--gr-text-primary)]">
                Every great idea deserves funding
              </h2>
              <p className="mt-4 text-[var(--gr-text-secondary)] leading-relaxed">
                Grant discovery is broken. Researchers waste hundreds of hours per year
                sifting through irrelevant opportunities on scattered platforms. Important
                work goes unfunded simply because the right people never found the right grants.
              </p>
              <p className="mt-4 text-[var(--gr-text-secondary)] leading-relaxed">
                We're changing that. GrantRadar aggregates grants from major federal sources
                and uses intelligent matching to surface opportunities that actually fit your
                organization's mission, eligibility, and funding needs.
              </p>
            </div>
            <div className="animate-fade-in-up stagger-2">
              <div className="bg-[var(--gr-blue-50)] rounded-2xl p-8 border border-[var(--gr-blue-100)]">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-14 h-14 bg-[var(--gr-blue-600)] rounded-xl flex items-center justify-center">
                    <SparklesIcon className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <div className="text-3xl font-display font-semibold text-[var(--gr-blue-600)]">
                      86,000+
                    </div>
                    <div className="text-sm text-[var(--gr-text-secondary)]">
                      Grants Indexed
                    </div>
                  </div>
                </div>
                <p className="text-[var(--gr-text-secondary)]">
                  We continuously monitor and index grants from NIH, NSF, Grants.gov,
                  and are expanding to include private foundations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Data Sources */}
      <section className="py-20 bg-[var(--gr-gray-50)] border-y border-[var(--gr-border-default)]">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12 animate-fade-in-up">
            <span className="badge badge-yellow">Data Sources</span>
            <h2 className="mt-6 text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              Where our grants come from
            </h2>
            <p className="mt-4 text-[var(--gr-text-secondary)] max-w-2xl mx-auto">
              We aggregate data from trusted, authoritative sources. All grant information
              is updated daily to ensure accuracy.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            {dataSources.map((source, index) => (
              <div
                key={source.name}
                className={`card animate-fade-in-up stagger-${index + 1}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)]">
                    {source.name}
                  </h3>
                  <span className={`badge ${source.count === 'Coming Soon' ? 'badge-yellow' : 'badge-blue'}`}>
                    {source.count}
                  </span>
                </div>
                <p className="text-[var(--gr-text-secondary)] text-sm mb-4">
                  {source.description}
                </p>
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)]"
                  >
                    Visit source &rarr;
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12 animate-fade-in-up">
            <span className="badge badge-green">Our Values</span>
            <h2 className="mt-6 text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              What we believe in
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            {values.map((value, index) => {
              const colorMap: Record<string, { bg: string; icon: string }> = {
                blue: { bg: 'bg-[var(--gr-blue-50)]', icon: 'text-[var(--gr-blue-600)]' },
                yellow: { bg: 'bg-[var(--gr-yellow-50)]', icon: 'text-[var(--gr-yellow-600)]' },
                green: { bg: 'bg-green-50', icon: 'text-[var(--gr-green-600)]' },
              };
              const colors = colorMap[value.color] || colorMap.blue;

              return (
                <div
                  key={value.title}
                  className={`card animate-fade-in-up stagger-${index + 1}`}
                >
                  <div className={`w-12 h-12 ${colors.bg} rounded-xl flex items-center justify-center mb-4`}>
                    <value.icon className={`w-6 h-6 ${colors.icon}`} />
                  </div>
                  <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
                    {value.title}
                  </h3>
                  <p className="text-[var(--gr-text-secondary)]">
                    {value.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-[var(--gr-gray-50)] border-y border-[var(--gr-border-default)]">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12 animate-fade-in-up">
            <h2 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              How our matching works
            </h2>
            <p className="mt-4 text-[var(--gr-text-secondary)] max-w-2xl mx-auto">
              We don't just do keyword matching. Our system analyzes multiple factors
              to find grants that truly fit your organization.
            </p>
          </div>

          <div className="space-y-6 animate-fade-in-up stagger-1">
            {[
              {
                title: 'Organization Profile Analysis',
                description: 'We analyze your organization type, focus areas, and eligibility criteria to understand what grants you qualify for.',
              },
              {
                title: 'Grant Requirement Parsing',
                description: 'Each grant is parsed to extract eligibility requirements, funding amounts, deadlines, and focus areas.',
              },
              {
                title: 'Semantic Matching',
                description: 'Our AI compares your profile against grant requirements using semantic understanding, not just keywords.',
              },
              {
                title: 'Match Score Generation',
                description: 'Each grant receives a match score (0-100) based on how well it aligns with your organization.',
              },
              {
                title: 'Continuous Updates',
                description: 'New grants are processed daily, and your matches are automatically updated.',
              },
            ].map((step, index) => (
              <div key={step.title} className="flex gap-4 items-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--gr-blue-600)] text-white flex items-center justify-center text-sm font-semibold">
                  {index + 1}
                </div>
                <div>
                  <h3 className="font-display font-medium text-[var(--gr-text-primary)]">
                    {step.title}
                  </h3>
                  <p className="text-[var(--gr-text-secondary)] mt-1">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-6 text-center animate-fade-in-up">
          <h2 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
            Ready to find your next grant?
          </h2>
          <p className="mt-4 text-[var(--gr-text-secondary)]">
            Start your 14-day free trial. No credit card required.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to="/auth?mode=signup" className="btn-primary">
              Start Free Trial
            </Link>
            <Link to="/contact" className="btn-secondary">
              Contact Us
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

export default About;
