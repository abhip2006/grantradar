import { Link } from 'react-router-dom';

export function Terms() {
  const lastUpdated = 'January 7, 2026';
  const effectiveDate = 'January 7, 2026';

  const sections = [
    {
      title: '1. Acceptance of Terms',
      content: `By accessing or using GrantRadar ("Service"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of these terms, you may not access the Service.

These Terms apply to all visitors, users, and others who access or use the Service. By using GrantRadar, you represent that you are at least 18 years of age and have the legal capacity to enter into these Terms.`,
    },
    {
      title: '2. Description of Service',
      content: `GrantRadar is a grant discovery platform that uses artificial intelligence to match organizations with relevant funding opportunities. Our Service includes:

• **Grant Database**: Access to aggregated grant opportunities from federal, state, and private foundation sources
• **AI Matching**: Automated analysis to match your organization profile with relevant grants
• **Notifications**: Alerts about new matches, deadlines, and updates
• **Dashboard**: Tools to track, save, and manage grant opportunities

GrantRadar does not guarantee funding success. We provide information and matching services to help you discover opportunities, but grant approval decisions are made solely by the funding organizations.`,
    },
    {
      title: '3. Account Registration',
      content: `To use GrantRadar, you must create an account. You agree to:

• Provide accurate, current, and complete information during registration
• Maintain and promptly update your account information
• Keep your password secure and confidential
• Notify us immediately of any unauthorized access to your account
• Accept responsibility for all activities that occur under your account

We reserve the right to suspend or terminate accounts that violate these Terms or provide false information.`,
    },
    {
      title: '4. Subscription and Billing',
      content: `**Free Trial**: New users receive a 14-day free trial with full access to all features. No credit card is required to start your trial.

**Beta Pricing**: During our beta period, subscriptions are billed at $200/month. Beta users who subscribe will retain this rate ("locked-in pricing") even after the beta period ends and standard pricing takes effect.

**Billing**: Subscriptions are billed monthly in advance. By subscribing, you authorize us to charge your payment method on a recurring basis.

**Cancellation**: You may cancel your subscription at any time through your account settings. Cancellation takes effect at the end of your current billing period. No refunds are provided for partial months.

**Price Changes**: We may change subscription prices with 30 days' notice. Price changes do not apply to users with locked-in beta pricing.`,
    },
    {
      title: '5. Acceptable Use',
      content: `You agree not to use GrantRadar to:

• Violate any applicable laws or regulations
• Infringe on the intellectual property rights of others
• Transmit malware, viruses, or other harmful code
• Attempt to gain unauthorized access to our systems
• Scrape, harvest, or collect data from our Service without permission
• Interfere with or disrupt the Service or servers
• Impersonate others or provide false information
• Use the Service for any illegal or unauthorized purpose
• Share your account credentials with others
• Resell or redistribute our Service without authorization

We reserve the right to terminate accounts that violate these guidelines.`,
    },
    {
      title: '6. Intellectual Property',
      content: `**Our Content**: The GrantRadar platform, including its design, features, and content, is owned by GrantRadar and protected by intellectual property laws. You may not copy, modify, distribute, or create derivative works without our written permission.

**Grant Data**: Grant information displayed on our platform is sourced from public databases and third-party providers. We do not claim ownership of this data but provide it under license agreements with our sources.

**Your Content**: You retain ownership of any content you submit to GrantRadar (e.g., organization profiles). By submitting content, you grant us a license to use it to provide our Services.`,
    },
    {
      title: '7. Disclaimer of Warranties',
      content: `THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED.

We do not warrant that:
• The Service will be uninterrupted, secure, or error-free
• Grant information will be accurate, complete, or current
• Results from using the Service will meet your requirements
• Any errors in the Service will be corrected

Grant matching is based on algorithmic analysis and may not identify all relevant opportunities. We recommend supplementing GrantRadar with your own research.`,
    },
    {
      title: '8. Limitation of Liability',
      content: `TO THE MAXIMUM EXTENT PERMITTED BY LAW, GRANTRADAR SHALL NOT BE LIABLE FOR:

• Any indirect, incidental, special, consequential, or punitive damages
• Loss of profits, data, use, goodwill, or other intangible losses
• Any damages arising from your use or inability to use the Service
• Any damages arising from unauthorized access to your account
• Any damages exceeding the amount paid by you to GrantRadar in the twelve (12) months preceding the claim

Some jurisdictions do not allow limitations on implied warranties or liability, so these limitations may not apply to you.`,
    },
    {
      title: '9. Indemnification',
      content: `You agree to indemnify, defend, and hold harmless GrantRadar, its officers, directors, employees, and agents from any claims, damages, losses, liabilities, and expenses (including attorneys' fees) arising from:

• Your use of the Service
• Your violation of these Terms
• Your violation of any third-party rights
• Any content you submit to the Service`,
    },
    {
      title: '10. Termination',
      content: `We may terminate or suspend your account immediately, without prior notice, if you breach these Terms or for any other reason at our sole discretion.

Upon termination:
• Your right to use the Service ceases immediately
• We may delete your account and associated data
• Provisions that should survive termination will remain in effect (e.g., liability limitations, indemnification)

You may terminate your account at any time through your account settings or by contacting support.`,
    },
    {
      title: '11. Governing Law',
      content: `These Terms shall be governed by and construed in accordance with the laws of the State of Delaware, United States, without regard to its conflict of law provisions.

Any disputes arising from these Terms or the Service shall be resolved exclusively in the state or federal courts located in Delaware. You consent to the personal jurisdiction of these courts.`,
    },
    {
      title: '12. Changes to Terms',
      content: `We reserve the right to modify these Terms at any time. We will notify you of material changes by:

• Posting the updated Terms on our website
• Sending an email to your registered address
• Displaying a notice in your account dashboard

Your continued use of the Service after changes become effective constitutes acceptance of the new Terms. If you do not agree to the changes, you must stop using the Service.`,
    },
    {
      title: '13. Miscellaneous',
      content: `**Entire Agreement**: These Terms constitute the entire agreement between you and GrantRadar regarding the Service.

**Severability**: If any provision of these Terms is found unenforceable, the remaining provisions will continue in effect.

**Waiver**: Our failure to enforce any right or provision does not constitute a waiver of that right.

**Assignment**: You may not assign your rights under these Terms without our consent. We may assign our rights without restriction.

**Force Majeure**: We are not liable for delays or failures caused by circumstances beyond our reasonable control.`,
    },
    {
      title: '14. Contact Information',
      content: `For questions about these Terms, please contact us:

**Email**: legal@grantradar.com
**Support**: support@grantradar.com

Or use our [Contact Form](/contact).`,
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <main className="max-w-4xl mx-auto px-6 py-12 md:py-20">
        {/* Header */}
        <div className="mb-12 animate-fade-in-up">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors mb-6"
          >
            &larr; Back to Home
          </Link>
          <h1 className="text-4xl font-display font-medium text-[var(--gr-text-primary)]">
            Terms of Service
          </h1>
          <p className="mt-3 text-[var(--gr-text-secondary)]">
            Last updated: {lastUpdated} | Effective: {effectiveDate}
          </p>
        </div>

        {/* Introduction */}
        <div className="mb-12 p-6 bg-[var(--gr-blue-50)] rounded-xl border border-[var(--gr-blue-100)] animate-fade-in-up stagger-1">
          <p className="text-[var(--gr-text-secondary)] leading-relaxed">
            <strong className="text-[var(--gr-text-primary)]">Important:</strong> Please read these Terms of Service
            carefully before using GrantRadar. By using our Service, you agree to be bound by these Terms.
            If you have any questions, please contact us at legal@grantradar.com.
          </p>
        </div>

        {/* Sections */}
        <div className="space-y-10">
          {sections.map((section, index) => (
            <section
              key={section.title}
              className={`animate-fade-in-up stagger-${Math.min(index + 2, 6)}`}
            >
              <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)] mb-4">
                {section.title}
              </h2>
              <div
                className="text-[var(--gr-text-secondary)] leading-relaxed whitespace-pre-line"
                dangerouslySetInnerHTML={{
                  __html: section.content
                    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-[var(--gr-text-primary)]">$1</strong>')
                    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] underline">$1</a>')
                    .replace(/^• /gm, '<span class="inline-block w-2 h-2 bg-[var(--gr-blue-500)] rounded-full mr-3 align-middle"></span>')
                }}
              />
            </section>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t border-[var(--gr-border-subtle)]">
          <div className="flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
            <p className="text-[var(--gr-text-secondary)]">
              Questions about these terms?{' '}
              <Link
                to="/contact"
                className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
              >
                Contact us
              </Link>
            </p>
            <Link
              to="/privacy"
              className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
            >
              Read our Privacy Policy &rarr;
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Terms;
