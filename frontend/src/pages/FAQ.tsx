import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQCategory {
  name: string;
  items: FAQItem[];
}

const faqData: FAQCategory[] = [
  {
    name: 'Getting Started',
    items: [
      {
        question: 'How does GrantRadar work?',
        answer: `GrantRadar aggregates grant opportunities from major federal sources (NIH, NSF, Grants.gov) and matches them against your organization profile.

When you sign up, you tell us about your organization type, focus areas, and funding needs. Our AI then analyzes each grant to determine how well it matches your criteria, giving each one a match score from 0-100.

You'll see your matches ranked by score, with the most relevant opportunities at the top. We also send notifications about new matches and approaching deadlines.`,
      },
      {
        question: 'What grants are included in GrantRadar?',
        answer: `We currently index grants from three major federal sources:

• **NIH Reporter**: 50,000+ health and biomedical research grants from the National Institutes of Health
• **NSF Awards**: 25,000+ science, technology, engineering, and math grants from the National Science Foundation
• **Grants.gov**: 10,000+ federal grants across all government agencies

We're actively working on adding private foundation grants and state-level funding opportunities. Subscribe to our newsletter to be notified when new sources are added.`,
      },
      {
        question: 'How often is the grant data updated?',
        answer: `Our grant database is updated daily. We pull new grants from our sources every 24 hours, and your matches are automatically recalculated when new relevant grants are found.

For approaching deadlines, we send alerts at configurable intervals (3, 7, 14, or 30 days before deadline) so you never miss an opportunity.`,
      },
      {
        question: 'How long until I see my first matches?',
        answer: `After completing your profile, you'll typically see your first matches within 2-5 minutes. Our system immediately analyzes all indexed grants against your new profile.

If you don't see matches immediately, it may be because:
• Your focus areas are very specific
• You're searching for rare grant types
• There's a temporary processing delay

You can always use the search function to manually explore grants while waiting for automated matches.`,
      },
    ],
  },
  {
    name: 'Matching & Search',
    items: [
      {
        question: 'How does the AI matching work?',
        answer: `Our matching system goes beyond simple keyword matching. Here's how it works:

1. **Profile Analysis**: We analyze your organization type, focus areas, eligibility criteria, and funding needs
2. **Grant Parsing**: Each grant is parsed to extract requirements, amounts, deadlines, and focus areas
3. **Semantic Matching**: We use natural language processing to understand the meaning behind both your profile and grant descriptions
4. **Score Calculation**: A match score (0-100) is calculated based on multiple factors including eligibility fit, focus area alignment, and funding amount relevance

The result is a ranked list of grants that actually make sense for your organization, not just ones that happen to share keywords.`,
      },
      {
        question: 'What does the match score mean?',
        answer: `The match score (0-100) indicates how well a grant aligns with your organization profile:

• **90-100**: Excellent match - highly relevant to your focus areas and eligibility
• **70-89**: Good match - strong alignment with most criteria
• **50-69**: Moderate match - some relevant aspects but may have gaps
• **Below 50**: Low match - limited relevance to your profile

We recommend focusing on grants with scores above 70 for the best use of your time. However, you can adjust your minimum score threshold in Settings.`,
      },
      {
        question: 'Can I search for grants by keyword?',
        answer: `Yes! In addition to our automated matching, you can search grants using keywords. The search supports:

• Full-text search across grant titles and descriptions
• Filtering by source (NIH, NSF, Grants.gov, or all)
• Filtering by deadline range
• Filtering by funding amount
• Sorting by match score, deadline, or amount

Search results are still ranked by match score when relevant to your profile, so you get the best of both worlds.`,
      },
      {
        question: 'How do I improve my matches?',
        answer: `To get better matches:

1. **Complete your profile**: Fill out all fields including organization type, focus areas, and eligibility criteria
2. **Be specific**: Add multiple relevant focus areas rather than just one broad category
3. **Update regularly**: Keep your profile current as your organization's priorities evolve
4. **Provide feedback**: Save grants you like and dismiss ones that aren't relevant - this helps us understand your preferences

You can update your profile anytime in Settings.`,
      },
    ],
  },
  {
    name: 'Account & Billing',
    items: [
      {
        question: 'Is there a free trial?',
        answer: `Yes! New users get a 14-day free trial with full access to all features. No credit card is required to start your trial.

During the trial, you can:
• View unlimited grant matches
• Save and track grants
• Receive email and SMS notifications
• Access all search and filter features

At the end of your trial, you can subscribe to continue using GrantRadar or your account will be downgraded to read-only access.`,
      },
      {
        question: 'How much does GrantRadar cost?',
        answer: `During our beta period, GrantRadar is **$200/month** with full access to all features.

**Beta Pricing Lock-In**: If you subscribe during beta, you'll keep this rate forever - even after we raise prices for new customers post-beta.

For larger organizations or teams, we offer custom Enterprise pricing. Contact us at sales@grantradar.com for more information.`,
      },
      {
        question: 'Can I cancel anytime?',
        answer: `Yes, you can cancel your subscription at any time with no penalties or fees.

When you cancel:
• Your access continues until the end of your current billing period
• No refunds are provided for partial months
• Your account data is retained for 30 days in case you want to resubscribe
• After 30 days, your data is permanently deleted

To cancel, go to Settings → Billing → Cancel Subscription.`,
      },
      {
        question: 'What payment methods do you accept?',
        answer: `We accept all major credit and debit cards through our secure payment processor, Stripe:

• Visa
• Mastercard
• American Express
• Discover

We do not currently support PayPal, bank transfers, or invoicing. Enterprise customers can request alternative payment arrangements.`,
      },
      {
        question: 'How do I change my profile information?',
        answer: `You can update your profile anytime in Settings:

1. Click your profile icon in the top right
2. Select "Settings"
3. Go to the "Profile" tab
4. Update your organization name, type, or focus areas
5. Click "Save Changes"

Changes to your profile will trigger a recalculation of your grant matches within a few minutes.`,
      },
    ],
  },
  {
    name: 'Privacy & Security',
    items: [
      {
        question: 'Is my data secure?',
        answer: `Yes, we take security seriously. Our security measures include:

• **Encryption**: All data is encrypted in transit (TLS 1.3) and at rest (AES-256)
• **Access Controls**: Strict internal access controls limit who can view your data
• **Infrastructure**: Hosted on SOC 2 compliant cloud infrastructure
• **Monitoring**: 24/7 monitoring for security threats
• **Regular Audits**: Periodic security assessments and penetration testing

For more details, see our Privacy Policy.`,
      },
      {
        question: 'Do you sell my information?',
        answer: `**No, we never sell your personal information.**

We only use your data to:
• Provide grant matching services
• Send you notifications
• Improve our algorithms
• Provide customer support

We share data only with essential service providers (like our email delivery service) under strict contractual protections. See our Privacy Policy for full details.`,
      },
      {
        question: 'Can I export my data?',
        answer: `Yes, you can export your data at any time. Go to Settings → Profile → Export Data to download:

• Your organization profile
• Saved grants
• Search history
• Notification preferences

Data is provided in JSON format. If you need a different format, contact support.`,
      },
      {
        question: 'How do I delete my account?',
        answer: `To delete your account:

1. Go to Settings → Profile
2. Scroll to "Danger Zone"
3. Click "Delete Account"
4. Confirm by entering your password

After deletion:
• Your account is immediately deactivated
• All personal data is deleted within 30 days
• Backups are purged within 180 days

This action cannot be undone. If you have an active subscription, it will be cancelled automatically.`,
      },
    ],
  },
  {
    name: 'Technical',
    items: [
      {
        question: 'What browsers are supported?',
        answer: `GrantRadar works best on modern browsers:

• **Chrome**: Version 90+
• **Firefox**: Version 88+
• **Safari**: Version 14+
• **Edge**: Version 90+

We recommend keeping your browser updated for the best experience. Older browsers may have limited functionality or display issues.`,
      },
      {
        question: 'Is there a mobile app?',
        answer: `Not yet, but GrantRadar is fully responsive and works great on mobile browsers. You can access all features from your phone or tablet.

A native mobile app is on our roadmap. Subscribe to our newsletter to be notified when it launches.`,
      },
      {
        question: 'Do you have an API?',
        answer: `API access is available for Enterprise customers. The API allows you to:

• Query grants programmatically
• Integrate matches into your existing systems
• Build custom dashboards and reports

For API access, contact us at enterprise@grantradar.com.`,
      },
      {
        question: 'Can I integrate with my CRM or grant management system?',
        answer: `Direct integrations are coming soon! We're working on integrations with popular platforms including:

• Salesforce
• Blackbaud
• Foundant
• Custom webhooks

Enterprise customers can request custom integrations. Contact enterprise@grantradar.com for more information.`,
      },
    ],
  },
];

function FAQItem({ item, isOpen, onToggle }: { item: FAQItem; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className="border-b border-[var(--gr-border-subtle)] last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full py-5 flex items-start justify-between text-left hover:bg-[var(--gr-bg-secondary)] transition-colors px-4 -mx-4 rounded-lg"
      >
        <span className="font-medium text-[var(--gr-text-primary)] pr-4">
          {item.question}
        </span>
        <ChevronDownIcon
          className={`w-5 h-5 flex-shrink-0 text-[var(--gr-text-tertiary)] transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>
      {isOpen && (
        <div className="pb-5 px-4 -mx-4">
          <div
            className="text-[var(--gr-text-secondary)] leading-relaxed whitespace-pre-line"
            dangerouslySetInnerHTML={{
              __html: item.answer
                .replace(/\*\*(.*?)\*\*/g, '<strong class="text-[var(--gr-text-primary)]">$1</strong>')
                .replace(/^• /gm, '<span class="inline-block w-2 h-2 bg-[var(--gr-blue-500)] rounded-full mr-3 align-middle"></span>')
            }}
          />
        </div>
      )}
    </div>
  );
}

export function FAQ() {
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());
  const [activeCategory, setActiveCategory] = useState(faqData[0].name);

  const toggleItem = (question: string) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(question)) {
        next.delete(question);
      } else {
        next.add(question);
      }
      return next;
    });
  };

  const activeItems = faqData.find((cat) => cat.name === activeCategory)?.items || [];

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
            Frequently Asked Questions
          </h1>
          <p className="mt-3 text-lg text-[var(--gr-text-secondary)]">
            Find answers to common questions about GrantRadar.
          </p>
        </div>

        {/* Category Tabs */}
        <div className="mb-8 animate-fade-in-up stagger-1">
          <div className="flex flex-wrap gap-2">
            {faqData.map((category) => (
              <button
                key={category.name}
                onClick={() => setActiveCategory(category.name)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeCategory === category.name
                    ? 'bg-[var(--gr-blue-600)] text-white'
                    : 'bg-[var(--gr-gray-100)] text-[var(--gr-text-secondary)] hover:bg-[var(--gr-gray-200)]'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* FAQ Items */}
        <div className="card animate-fade-in-up stagger-2">
          {activeItems.map((item) => (
            <FAQItem
              key={item.question}
              item={item}
              isOpen={openItems.has(item.question)}
              onToggle={() => toggleItem(item.question)}
            />
          ))}
        </div>

        {/* Still Have Questions */}
        <div className="mt-12 p-8 bg-[var(--gr-blue-50)] rounded-2xl border border-[var(--gr-blue-100)] text-center animate-fade-in-up stagger-3">
          <h2 className="text-2xl font-display font-medium text-[var(--gr-text-primary)]">
            Still have questions?
          </h2>
          <p className="mt-2 text-[var(--gr-text-secondary)]">
            Can't find the answer you're looking for? Our support team is here to help.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-4">
            <Link to="/contact" className="btn-primary">
              Contact Support
            </Link>
            <a href="mailto:support@grantradar.com" className="btn-secondary">
              Email Us
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}

export default FAQ;
