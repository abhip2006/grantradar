import {
  AcademicCapIcon,
  BeakerIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import type { WinnersSearchResponse } from '../../types/winners';
import { formatCurrency } from './WinnerCard';

interface AggregationCardsProps {
  data?: WinnersSearchResponse;
}

export function AggregationCards({ data }: AggregationCardsProps) {
  if (!data?.aggregations) return null;

  const { by_year, by_mechanism, by_institute } = data.aggregations;

  return (
    <div className="grid md:grid-cols-3 gap-4 mb-6">
      {/* Top Mechanisms */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <BeakerIcon className="h-4 w-4 text-[var(--gr-accent-forest)]" />
          Top Mechanisms
        </h4>
        <div className="space-y-2">
          {by_mechanism.slice(0, 5).map((m) => (
            <div key={m.code} className="flex items-center justify-between text-sm">
              <span className="badge-mechanism">{m.code}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {m.count.toLocaleString()} projects
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Institutes */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <AcademicCapIcon className="h-4 w-4 text-[var(--gr-blue-500)]" />
          Top Institutes
        </h4>
        <div className="space-y-2">
          {by_institute.slice(0, 5).map((i) => (
            <div key={i.abbreviation} className="flex items-center justify-between text-sm">
              <span className="text-[var(--gr-text-secondary)]">{i.abbreviation}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {i.count.toLocaleString()} projects
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Years */}
      <div className="card-premium-subtle">
        <h4 className="font-display font-semibold text-[var(--gr-text-primary)] mb-3 flex items-center gap-2">
          <ChartBarIcon className="h-4 w-4 text-[var(--gr-accent-gold)]" />
          By Year
        </h4>
        <div className="space-y-2">
          {by_year.slice(0, 5).map((y) => (
            <div key={y.year} className="flex items-center justify-between text-sm">
              <span className="text-[var(--gr-text-secondary)]">FY {y.year}</span>
              <span className="text-[var(--gr-text-tertiary)]">
                {formatCurrency(y.total_funding)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default AggregationCards;
