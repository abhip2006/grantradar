import { Link } from 'react-router-dom';

export function PrivacyPolicy() {
  const lastUpdated = 'January 7, 2026';

  const sections = [
    {
      title: 'Information We Collect',
      content: `When you use GrantRadar, we collect information to provide and improve our services:

**Account Information**: When you create an account, we collect your email address, organization name, organization type, and focus areas. This information helps us match you with relevant grant opportunities.

**Usage Data**: We collect information about how you interact with our platform, including grants you view, save, or dismiss, search queries, and notification preferences.

**Grant Preferences**: Information about your funding needs, eligibility criteria, and research focus areas that you provide to improve matching accuracy.

**Technical Data**: We automatically collect certain technical information including IP address, browser type, device information, and cookies to ensure platform security and optimize performance.`,
    },
    {
      title: 'How We Use Your Information',
      content: `We use your information to:

• **Provide Grant Matching**: Analyze your profile against our grant database to surface relevant opportunities
• **Send Notifications**: Alert you about new matches, approaching deadlines, and important updates
• **Improve Our Services**: Analyze usage patterns to enhance matching algorithms and user experience
• **Customer Support**: Respond to your inquiries and provide technical assistance
• **Security**: Detect and prevent fraud, abuse, and security incidents
• **Legal Compliance**: Comply with applicable laws and regulations`,
    },
    {
      title: 'Data Sharing',
      content: `**We do not sell your personal information.** We may share your information only in these limited circumstances:

• **Service Providers**: With trusted third parties who help us operate our platform (e.g., email delivery, payment processing). These providers are contractually required to protect your data.
• **Legal Requirements**: When required by law, subpoena, or to protect the rights and safety of GrantRadar and our users.
• **Business Transfers**: In connection with a merger, acquisition, or sale of assets, with appropriate confidentiality protections.
• **With Your Consent**: When you explicitly authorize us to share information.`,
    },
    {
      title: 'Data Security',
      content: `We implement industry-standard security measures to protect your information:

• **Encryption**: All data is encrypted in transit (TLS 1.3) and at rest (AES-256)
• **Access Controls**: Strict access controls limit who can access your data
• **Infrastructure**: Our systems are hosted on secure, SOC 2 compliant infrastructure
• **Monitoring**: Continuous monitoring for security threats and vulnerabilities
• **Regular Audits**: Periodic security assessments and penetration testing

While we strive to protect your information, no system is completely secure. We encourage you to use strong passwords and keep your account credentials confidential.`,
    },
    {
      title: 'Your Rights',
      content: `You have the following rights regarding your personal information:

• **Access**: Request a copy of the personal data we hold about you
• **Correction**: Update or correct inaccurate information in your account
• **Deletion**: Request deletion of your account and associated data
• **Export**: Download your data in a portable format
• **Opt-Out**: Unsubscribe from marketing communications at any time
• **Restrict Processing**: Request limitations on how we use your data

To exercise these rights, contact us at privacy@grantradar.com or through your account settings.`,
    },
    {
      title: 'Cookies & Tracking',
      content: `We use cookies and similar technologies to:

• **Essential Cookies**: Enable core functionality like authentication and security
• **Preference Cookies**: Remember your settings and preferences
• **Analytics Cookies**: Understand how users interact with our platform

You can control cookies through your browser settings. Note that disabling certain cookies may affect platform functionality.

We do not use third-party advertising cookies or sell data to advertisers.`,
    },
    {
      title: 'Data Retention',
      content: `We retain your information for as long as your account is active or as needed to provide services. After account deletion:

• **Account Data**: Deleted within 30 days
• **Usage Logs**: Anonymized or deleted within 90 days
• **Backups**: Removed from backup systems within 180 days

We may retain certain information longer if required by law or for legitimate business purposes (e.g., resolving disputes, enforcing agreements).`,
    },
    {
      title: 'International Users',
      content: `GrantRadar is operated from the United States. If you are accessing our services from outside the US, please be aware that your information may be transferred to, stored, and processed in the United States where our servers are located.

By using GrantRadar, you consent to the transfer of your information to the United States and the application of US data protection laws.`,
    },
    {
      title: 'Children\'s Privacy',
      content: `GrantRadar is not intended for users under 18 years of age. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately at privacy@grantradar.com.`,
    },
    {
      title: 'Changes to This Policy',
      content: `We may update this Privacy Policy from time to time. We will notify you of material changes by:

• Posting the updated policy on our website
• Sending you an email notification
• Displaying a notice in your account dashboard

Your continued use of GrantRadar after changes become effective constitutes acceptance of the updated policy.`,
    },
    {
      title: 'Contact Us',
      content: `If you have questions about this Privacy Policy or our data practices, please contact us:

**Email**: privacy@grantradar.com
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
            Privacy Policy
          </h1>
          <p className="mt-3 text-[var(--gr-text-secondary)]">
            Last updated: {lastUpdated}
          </p>
        </div>

        {/* Introduction */}
        <div className="mb-12 animate-fade-in-up stagger-1">
          <p className="text-lg text-[var(--gr-text-secondary)] leading-relaxed">
            At GrantRadar, we take your privacy seriously. This Privacy Policy explains how we collect,
            use, share, and protect your personal information when you use our grant discovery platform.
            By using GrantRadar, you agree to the terms of this policy.
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
              <div className="prose prose-gray max-w-none">
                <div
                  className="text-[var(--gr-text-secondary)] leading-relaxed whitespace-pre-line"
                  dangerouslySetInnerHTML={{
                    __html: section.content
                      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-[var(--gr-text-primary)]">$1</strong>')
                      .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] underline">$1</a>')
                      .replace(/^• /gm, '<span class="inline-block w-2 h-2 bg-[var(--gr-blue-500)] rounded-full mr-3 align-middle"></span>')
                  }}
                />
              </div>
            </section>
          ))}
        </div>

        {/* Footer CTA */}
        <div className="mt-16 pt-8 border-t border-[var(--gr-border-subtle)]">
          <p className="text-[var(--gr-text-secondary)]">
            Have questions about our privacy practices?{' '}
            <Link
              to="/contact"
              className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
            >
              Contact us
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}

export default PrivacyPolicy;
