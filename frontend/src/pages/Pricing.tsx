import { Link } from 'react-router-dom';
import {
  CheckIcon,
  XMarkIcon,
  SparklesIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';

export function Pricing() {
  const features = [
    { name: 'Grants indexed', beta: '86,000+', enterprise: '86,000+' },
    { name: 'AI-powered matching', beta: true, enterprise: true },
    { name: 'Real-time notifications', beta: true, enterprise: true },
    { name: 'Email alerts', beta: true, enterprise: true },
    { name: 'SMS alerts', beta: true, enterprise: true },
    { name: 'Match score insights', beta: true, enterprise: true },
    { name: 'Full-text search', beta: true, enterprise: true },
    { name: 'Save & track grants', beta: true, enterprise: true },
    { name: 'Deadline reminders', beta: true, enterprise: true },
    { name: 'Slack integration', beta: false, enterprise: true },
    { name: 'API access', beta: false, enterprise: true },
    { name: 'Team collaboration', beta: false, enterprise: true },
    { name: 'Custom integrations', beta: false, enterprise: true },
    { name: 'Dedicated success manager', beta: false, enterprise: true },
    { name: 'Priority support', beta: 'Email', enterprise: '24/7 Phone & Email' },
  ];

  const faqs = [
    {
      question: 'What happens after the beta period ends?',
      answer: 'We\'ll transition to tiered pricing for new customers. However, beta subscribers keep their $200/month rate locked in forever - it\'s our way of thanking early adopters for believing in us.',
    },
    {
      question: 'Is there a free trial?',
      answer: 'Yes! Every new user gets a 14-day free trial with full access to all Beta features. No credit card required to start.',
    },
    {
      question: 'Can I cancel anytime?',
      answer: 'Absolutely. There are no long-term contracts or cancellation fees. Cancel anytime and your access continues until the end of your billing period.',
    },
    {
      question: 'What payment methods do you accept?',
      answer: 'We accept all major credit and debit cards (Visa, Mastercard, American Express, Discover) through Stripe. Enterprise customers can arrange invoicing.',
    },
    {
      question: 'Is there annual billing?',
      answer: 'Annual billing is coming soon! Contact us at billing@grantradar.com if you\'d like to pay annually and we\'ll work something out.',
    },
    {
      question: 'What if I need more than the Beta plan offers?',
      answer: 'Enterprise is perfect for larger organizations that need team collaboration, API access, or custom integrations. Contact our sales team for a custom quote.',
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      {/* Hero */}
      <section className="py-20 bg-[var(--gr-gray-50)] border-b border-[var(--gr-border-default)]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="animate-fade-in-up">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors mb-8"
            >
              &larr; Back to Home
            </Link>
            <span className="badge badge-green">Simple Pricing</span>
            <h1 className="mt-6 text-4xl lg:text-5xl font-display font-medium text-[var(--gr-text-primary)]">
              Transparent pricing.{' '}
              <span className="text-[var(--gr-blue-600)]">No surprises.</span>
            </h1>
            <p className="mt-4 text-xl text-[var(--gr-text-secondary)] max-w-2xl mx-auto">
              Start with a 14-day free trial. No credit card required.
              Lock in beta pricing forever when you subscribe.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Beta Access */}
            <div className="relative p-8 rounded-2xl bg-[var(--gr-blue-50)] border-2 border-[var(--gr-blue-200)] animate-fade-in-up">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="px-3 py-1 bg-[var(--gr-blue-600)] text-white text-xs font-bold rounded-full uppercase tracking-wider">
                  Most Popular
                </span>
              </div>

              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[var(--gr-blue-600)] rounded-lg flex items-center justify-center">
                  <SparklesIcon className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                  Beta Access
                </h3>
              </div>

              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-5xl font-display font-semibold text-[var(--gr-text-primary)]">
                  $200
                </span>
                <span className="text-[var(--gr-text-tertiary)]">/month</span>
              </div>

              <p className="text-sm text-[var(--gr-text-secondary)] mb-6">
                Lock in this rate forever. Early adopter pricing that stays with you.
              </p>

              <Link
                to="/auth?mode=signup"
                className="btn-primary w-full justify-center mb-6"
              >
                Start 14-Day Free Trial
                <ArrowRightIcon className="w-4 h-4" />
              </Link>

              <div className="flex items-center gap-4 text-sm text-[var(--gr-text-secondary)]">
                <div className="flex items-center gap-1">
                  <ShieldCheckIcon className="w-4 h-4 text-[var(--gr-green-500)]" />
                  No credit card required
                </div>
                <div className="flex items-center gap-1">
                  <CheckIcon className="w-4 h-4 text-[var(--gr-green-500)]" />
                  Cancel anytime
                </div>
              </div>
            </div>

            {/* Enterprise */}
            <div className="p-8 rounded-2xl bg-white border border-[var(--gr-border-default)] animate-fade-in-up stagger-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-[var(--gr-gray-100)] rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-[var(--gr-gray-600)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                <h3 className="text-xl font-display font-medium text-[var(--gr-text-primary)]">
                  Enterprise
                </h3>
              </div>

              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-5xl font-display font-semibold text-[var(--gr-text-primary)]">
                  Custom
                </span>
              </div>

              <p className="text-sm text-[var(--gr-text-secondary)] mb-6">
                For large organizations and teams needing advanced features.
              </p>

              <a
                href="mailto:enterprise@grantradar.com"
                className="btn-secondary w-full justify-center mb-6"
              >
                Contact Sales
              </a>

              <p className="text-sm text-[var(--gr-text-tertiary)] text-center">
                Custom pricing based on your needs
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="py-20 bg-[var(--gr-gray-50)] border-y border-[var(--gr-border-default)]">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12 animate-fade-in-up">
            <h2 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              Compare Plans
            </h2>
            <p className="mt-4 text-[var(--gr-text-secondary)]">
              See what's included in each plan.
            </p>
          </div>

          <div className="card overflow-hidden animate-fade-in-up stagger-1">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--gr-border-subtle)]">
                  <th className="text-left py-4 px-6 font-medium text-[var(--gr-text-primary)]">
                    Feature
                  </th>
                  <th className="text-center py-4 px-6 font-medium text-[var(--gr-blue-600)]">
                    Beta Access
                  </th>
                  <th className="text-center py-4 px-6 font-medium text-[var(--gr-text-secondary)]">
                    Enterprise
                  </th>
                </tr>
              </thead>
              <tbody>
                {features.map((feature, index) => (
                  <tr
                    key={feature.name}
                    className={index % 2 === 0 ? 'bg-[var(--gr-bg-secondary)]' : ''}
                  >
                    <td className="py-4 px-6 text-[var(--gr-text-primary)]">
                      {feature.name}
                    </td>
                    <td className="py-4 px-6 text-center">
                      {typeof feature.beta === 'boolean' ? (
                        feature.beta ? (
                          <CheckIcon className="w-5 h-5 text-[var(--gr-green-500)] mx-auto" />
                        ) : (
                          <XMarkIcon className="w-5 h-5 text-[var(--gr-gray-300)] mx-auto" />
                        )
                      ) : (
                        <span className="text-sm text-[var(--gr-text-secondary)]">
                          {feature.beta}
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-center">
                      {typeof feature.enterprise === 'boolean' ? (
                        feature.enterprise ? (
                          <CheckIcon className="w-5 h-5 text-[var(--gr-green-500)] mx-auto" />
                        ) : (
                          <XMarkIcon className="w-5 h-5 text-[var(--gr-gray-300)] mx-auto" />
                        )
                      ) : (
                        <span className="text-sm text-[var(--gr-text-secondary)]">
                          {feature.enterprise}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12 animate-fade-in-up">
            <h2 className="text-3xl font-display font-medium text-[var(--gr-text-primary)]">
              Pricing FAQ
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-8 animate-fade-in-up stagger-1">
            {faqs.map((faq) => (
              <div key={faq.question} className="card">
                <h3 className="font-display font-medium text-[var(--gr-text-primary)] mb-2">
                  {faq.question}
                </h3>
                <p className="text-sm text-[var(--gr-text-secondary)]">
                  {faq.answer}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-12 text-center animate-fade-in-up stagger-2">
            <p className="text-[var(--gr-text-secondary)]">
              Have more questions?{' '}
              <Link
                to="/faq"
                className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
              >
                Check out our full FAQ
              </Link>{' '}
              or{' '}
              <Link
                to="/contact"
                className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
              >
                contact us
              </Link>
              .
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-[var(--gr-blue-600)]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl lg:text-4xl font-display font-medium text-white">
            Ready to find your next grant?
          </h2>
          <p className="mt-4 text-lg text-white/80">
            Start your free trial today. No credit card required.
          </p>
          <div className="mt-8">
            <Link
              to="/auth?mode=signup"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-[var(--gr-blue-600)] font-semibold rounded-xl hover:bg-[var(--gr-gray-50)] transition-colors"
            >
              Start 14-Day Free Trial
              <ArrowRightIcon className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Pricing;
