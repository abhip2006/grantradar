import { useMemo, useEffect, useState, useRef } from 'react';
import { motion } from 'motion/react';
import {
  TrophyIcon,
  DocumentCheckIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import type { AnalyticsSummaryResponse } from '../../types';

interface StatsSummaryProps {
  data: AnalyticsSummaryResponse;
}

// Animated number hook with easing
function useAnimatedNumber(value: number, duration: number = 1000) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValue = useRef(0);

  useEffect(() => {
    if (value === 0 && previousValue.current === 0) {
      setDisplayValue(0);
      return;
    }

    const startTime = Date.now();
    const startValue = previousValue.current;

    const animate = () => {
      const now = Date.now();
      const progress = Math.min((now - startTime) / duration, 1);
      // Cubic ease out for smooth deceleration
      const eased = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (value - startValue) * eased;
      setDisplayValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        previousValue.current = value;
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return displayValue;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

type AccentColor = 'teal' | 'emerald' | 'amber' | 'blue' | 'violet' | 'rose';

interface StatCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  accentColor: AccentColor;
  index: number;
  isAnimated?: boolean;
  animatedValue?: number;
  formatValue?: (val: number) => string;
}

const colorClasses: Record<AccentColor, { gradient: string; iconBg: string; iconColor: string; border: string }> = {
  teal: {
    gradient: 'from-teal-500/10 to-teal-500/5',
    iconBg: 'bg-gradient-to-br from-teal-500 to-teal-600',
    iconColor: 'text-white',
    border: 'hover:border-teal-300',
  },
  emerald: {
    gradient: 'from-emerald-500/10 to-emerald-500/5',
    iconBg: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
    iconColor: 'text-white',
    border: 'hover:border-emerald-300',
  },
  amber: {
    gradient: 'from-amber-500/10 to-amber-500/5',
    iconBg: 'bg-gradient-to-br from-amber-500 to-amber-600',
    iconColor: 'text-white',
    border: 'hover:border-amber-300',
  },
  blue: {
    gradient: 'from-blue-500/10 to-blue-500/5',
    iconBg: 'bg-gradient-to-br from-blue-500 to-blue-600',
    iconColor: 'text-white',
    border: 'hover:border-blue-300',
  },
  violet: {
    gradient: 'from-violet-500/10 to-violet-500/5',
    iconBg: 'bg-gradient-to-br from-violet-500 to-violet-600',
    iconColor: 'text-white',
    border: 'hover:border-violet-300',
  },
  rose: {
    gradient: 'from-rose-500/10 to-rose-500/5',
    iconBg: 'bg-gradient-to-br from-rose-500 to-rose-600',
    iconColor: 'text-white',
    border: 'hover:border-rose-300',
  },
};

function StatCard({
  label,
  value,
  subValue,
  icon,
  accentColor,
  index,
  isAnimated,
  animatedValue,
  formatValue,
}: StatCardProps) {
  const colors = colorClasses[accentColor];
  const displayValue = isAnimated && animatedValue !== undefined && formatValue
    ? formatValue(animatedValue)
    : value;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.5,
        delay: index * 0.08,
        ease: [0.16, 1, 0.3, 1],
      }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`
        metric-card-premium group cursor-default
        ${colors.border}
      `}
    >
      {/* Subtle gradient overlay */}
      <div className={`absolute inset-0 bg-gradient-to-br ${colors.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-2xl`} />

      <div className="relative flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[var(--gr-text-tertiary)] uppercase tracking-wider mb-2">
            {label}
          </p>
          <motion.p
            key={String(displayValue)}
            initial={isAnimated ? { opacity: 0.5, scale: 0.98 } : {}}
            animate={{ opacity: 1, scale: 1 }}
            className="counter-value text-[var(--gr-text-primary)] mb-1"
          >
            {displayValue}
          </motion.p>
          {subValue && (
            <p className="text-sm text-[var(--gr-text-secondary)] mt-1.5">
              {subValue}
            </p>
          )}
        </div>

        {/* Animated icon container */}
        <motion.div
          whileHover={{ scale: 1.1, rotate: 5 }}
          transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          className={`
            p-3 rounded-xl shadow-lg
            ${colors.iconBg}
          `}
        >
          <div className={`h-5 w-5 ${colors.iconColor}`}>{icon}</div>
        </motion.div>
      </div>
    </motion.div>
  );
}

export function StatsSummary({ data }: StatsSummaryProps) {
  // Animated values
  const animatedApplications = useAnimatedNumber(data.total_applications);
  const animatedSuccessRate = useAnimatedNumber(data.overall_success_rate);
  const animatedFunding = useAnimatedNumber(data.total_funding_awarded);
  const animatedConversion = useAnimatedNumber(data.pipeline_conversion_rate);

  const stats = useMemo(() => {
    return [
      {
        label: 'Total Applications',
        value: data.total_applications,
        subValue: `${data.total_in_pipeline} in pipeline`,
        icon: <ChartBarIcon className="h-5 w-5" />,
        accentColor: 'teal' as const,
        isAnimated: true,
        animatedValue: animatedApplications,
        formatValue: (val: number) => Math.round(val).toLocaleString(),
      },
      {
        label: 'Win Rate',
        value: `${data.overall_success_rate.toFixed(1)}%`,
        subValue: `${data.total_awarded} awarded / ${data.total_submitted} submitted`,
        icon: <TrophyIcon className="h-5 w-5" />,
        accentColor: 'emerald' as const,
        isAnimated: true,
        animatedValue: animatedSuccessRate,
        formatValue: (val: number) => `${val.toFixed(1)}%`,
      },
      {
        label: 'Funding Awarded',
        value: formatCurrency(data.total_funding_awarded),
        subValue: data.avg_funding_per_award
          ? `Avg: ${formatCurrency(data.avg_funding_per_award)}`
          : undefined,
        icon: <CurrencyDollarIcon className="h-5 w-5" />,
        accentColor: 'amber' as const,
        isAnimated: true,
        animatedValue: animatedFunding,
        formatValue: formatCurrency,
      },
      {
        label: 'Pipeline Conversion',
        value: `${data.pipeline_conversion_rate.toFixed(1)}%`,
        subValue: 'From research to award',
        icon: <ArrowTrendingUpIcon className="h-5 w-5" />,
        accentColor: 'blue' as const,
        isAnimated: true,
        animatedValue: animatedConversion,
        formatValue: (val: number) => `${val.toFixed(1)}%`,
      },
      {
        label: 'Top Funder',
        value: data.top_funder || 'N/A',
        subValue: data.top_funder ? 'Highest success rate' : 'No data yet',
        icon: <StarIcon className="h-5 w-5" />,
        accentColor: 'violet' as const,
        isAnimated: false,
      },
      {
        label: 'Top Category',
        value: data.top_category || 'N/A',
        subValue: data.top_category ? 'Best performing area' : 'No data yet',
        icon: <DocumentCheckIcon className="h-5 w-5" />,
        accentColor: 'rose' as const,
        isAnimated: false,
      },
    ];
  }, [data, animatedApplications, animatedSuccessRate, animatedFunding, animatedConversion]);

  return (
    <div className="space-y-5">
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center gap-3"
      >
        <h3 className="text-lg font-display font-semibold text-[var(--gr-text-primary)]">
          Performance Summary
        </h3>
        <div className="h-px flex-1 bg-gradient-to-r from-[var(--gr-border-subtle)] to-transparent" />
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, index) => (
          <StatCard
            key={stat.label}
            label={stat.label}
            value={stat.value}
            subValue={stat.subValue}
            icon={stat.icon}
            accentColor={stat.accentColor}
            index={index}
            isAnimated={stat.isAnimated}
            animatedValue={stat.animatedValue}
            formatValue={stat.formatValue}
          />
        ))}
      </div>
    </div>
  );
}

export default StatsSummary;
