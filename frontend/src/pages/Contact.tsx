import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  EnvelopeIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import { useToast } from '../contexts/ToastContext';

interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

export function Contact() {
  const { showToast } = useToast();
  const [formData, setFormData] = useState<ContactFormData>({
    name: '',
    email: '',
    subject: 'general',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const subjects = [
    { value: 'general', label: 'General Inquiry' },
    { value: 'support', label: 'Technical Support' },
    { value: 'billing', label: 'Billing Question' },
    { value: 'enterprise', label: 'Enterprise Sales' },
    { value: 'partnership', label: 'Partnership Opportunity' },
    { value: 'feedback', label: 'Product Feedback' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setSubmitted(true);
        showToast('Message sent successfully!', 'success');
      } else {
        throw new Error('Failed to send message');
      }
    } catch (error) {
      showToast('Failed to send message. Please try again or email us directly.', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[var(--gr-bg-primary)] flex items-center justify-center px-6">
        <div className="max-w-md w-full text-center animate-fade-in-up">
          <div className="w-16 h-16 bg-[var(--gr-green-100)] rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircleIcon className="w-8 h-8 text-[var(--gr-green-600)]" />
          </div>
          <h1 className="text-3xl font-display font-medium text-[var(--gr-text-primary)] mb-4">
            Message Sent!
          </h1>
          <p className="text-[var(--gr-text-secondary)] mb-8">
            Thank you for reaching out. We'll get back to you within 24 hours.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/" className="btn-primary">
              Back to Home
            </Link>
            <button
              onClick={() => {
                setSubmitted(false);
                setFormData({ name: '', email: '', subject: 'general', message: '' });
              }}
              className="btn-secondary"
            >
              Send Another Message
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <main className="max-w-6xl mx-auto px-6 py-12 md:py-20">
        {/* Header */}
        <div className="mb-12 animate-fade-in-up">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-secondary)] transition-colors mb-6"
          >
            &larr; Back to Home
          </Link>
          <h1 className="text-4xl font-display font-medium text-[var(--gr-text-primary)]">
            Contact Us
          </h1>
          <p className="mt-3 text-lg text-[var(--gr-text-secondary)]">
            Have a question or need help? We're here for you.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-12">
          {/* Contact Info */}
          <div className="lg:col-span-1 space-y-8 animate-fade-in-up stagger-1">
            {/* Email */}
            <div className="card">
              <div className="w-12 h-12 bg-[var(--gr-blue-50)] rounded-xl flex items-center justify-center mb-4">
                <EnvelopeIcon className="w-6 h-6 text-[var(--gr-blue-600)]" />
              </div>
              <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
                Email Us
              </h3>
              <p className="text-[var(--gr-text-secondary)] text-sm mb-3">
                For general inquiries and support
              </p>
              <a
                href="mailto:support@grantradar.com"
                className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium"
              >
                support@grantradar.com
              </a>
            </div>

            {/* Response Time */}
            <div className="card">
              <div className="w-12 h-12 bg-[var(--gr-green-50)] rounded-xl flex items-center justify-center mb-4">
                <ClockIcon className="w-6 h-6 text-[var(--gr-green-600)]" />
              </div>
              <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
                Response Time
              </h3>
              <p className="text-[var(--gr-text-secondary)] text-sm">
                We typically respond within <strong className="text-[var(--gr-text-primary)]">24 hours</strong> during business days.
              </p>
            </div>

            {/* FAQ Link */}
            <div className="card bg-[var(--gr-gray-50)]">
              <div className="w-12 h-12 bg-[var(--gr-yellow-50)] rounded-xl flex items-center justify-center mb-4">
                <ChatBubbleLeftRightIcon className="w-6 h-6 text-[var(--gr-yellow-600)]" />
              </div>
              <h3 className="text-lg font-display font-medium text-[var(--gr-text-primary)] mb-2">
                Quick Answers
              </h3>
              <p className="text-[var(--gr-text-secondary)] text-sm mb-3">
                Find answers to common questions in our FAQ.
              </p>
              <Link
                to="/faq"
                className="text-[var(--gr-blue-600)] hover:text-[var(--gr-blue-700)] font-medium inline-flex items-center gap-1"
              >
                Visit FAQ &rarr;
              </Link>
            </div>
          </div>

          {/* Contact Form */}
          <div className="lg:col-span-2 animate-fade-in-up stagger-2">
            <div className="card">
              <h2 className="text-xl font-display font-medium text-[var(--gr-text-primary)] mb-6">
                Send us a message
              </h2>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid sm:grid-cols-2 gap-6">
                  {/* Name */}
                  <div>
                    <label htmlFor="name" className="label">
                      Your Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      className="input"
                      placeholder="Jane Smith"
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label htmlFor="email" className="label">
                      Email Address <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                      className="input"
                      placeholder="jane@university.edu"
                    />
                  </div>
                </div>

                {/* Subject */}
                <div>
                  <label htmlFor="subject" className="label">
                    Subject <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    className="input"
                  >
                    {subjects.map((subject) => (
                      <option key={subject.value} value={subject.value}>
                        {subject.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Message */}
                <div>
                  <label htmlFor="message" className="label">
                    Message <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    rows={6}
                    className="input resize-none"
                    placeholder="How can we help you?"
                  />
                </div>

                {/* Submit */}
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[var(--gr-text-tertiary)]">
                    <span className="text-red-500">*</span> Required fields
                  </p>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn-primary"
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Sending...
                      </>
                    ) : (
                      'Send Message'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Contact;
