import { useState, useEffect, useCallback, useRef, Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import {
  MagnifyingGlassIcon,
  XMarkIcon,
  ChevronUpDownIcon,
  CheckIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';

export type MemberFilter = 'all' | 'active' | 'pending';

interface FilterOption {
  value: MemberFilter;
  label: string;
}

const FILTER_OPTIONS: FilterOption[] = [
  { value: 'all', label: 'All Members' },
  { value: 'active', label: 'Active' },
  { value: 'pending', label: 'Pending' },
];

interface MemberSearchProps {
  value: string;
  onChange: (value: string) => void;
  filter: MemberFilter;
  onFilterChange: (filter: MemberFilter) => void;
  placeholder?: string;
  debounceMs?: number;
  className?: string;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function MemberSearch({
  value,
  onChange,
  filter,
  onFilterChange,
  placeholder = 'Search members...',
  debounceMs = 300,
  className = '',
}: MemberSearchProps) {
  const [localValue, setLocalValue] = useState(value);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // Update local value when prop changes
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Debounced onChange
  const debouncedOnChange = useCallback(
    (newValue: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        onChange(newValue);
      }, debounceMs);
    },
    [onChange, debounceMs]
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    debouncedOnChange(newValue);
  };

  const handleClear = () => {
    setLocalValue('');
    onChange('');
    inputRef.current?.focus();
  };

  // Keyboard shortcut handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const shortcutKey = isMac ? 'Cmd' : 'Ctrl';

  return (
    <div className={classNames('flex items-center gap-3', className)}>
      {/* Search Input */}
      <div
        className={classNames(
          'relative flex-1 transition-all duration-200',
          isFocused ? 'ring-2 ring-blue-500 ring-offset-2 rounded-xl' : ''
        )}
      >
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
          <MagnifyingGlassIcon
            className={classNames(
              'h-5 w-5 transition-colors',
              isFocused ? 'text-blue-500' : 'text-gray-400'
            )}
          />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={localValue}
          onChange={handleInputChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className="block w-full pl-10 pr-20 py-2.5 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-blue-500 focus:bg-white hover:border-gray-300 hover:bg-gray-100 transition-colors"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-2.5">
          {localValue ? (
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-200 transition-colors"
              aria-label="Clear search"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-md bg-gray-200 text-xs font-medium text-gray-500">
              {shortcutKey}
              <span className="text-gray-400">+</span>
              K
            </kbd>
          )}
        </div>
      </div>

      {/* Filter Dropdown */}
      <Listbox value={filter} onChange={onFilterChange}>
        <div className="relative">
          <Listbox.Button className="relative flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors min-w-[140px]">
            <FunnelIcon className="w-4 h-4 text-gray-400" />
            <span className="flex-1 text-left">
              {FILTER_OPTIONS.find((opt) => opt.value === filter)?.label}
            </span>
            <ChevronUpDownIcon className="w-4 h-4 text-gray-400" />
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-10 right-0 mt-2 w-44 origin-top-right bg-white rounded-xl shadow-lg border border-gray-100 py-1 focus:outline-none">
              {FILTER_OPTIONS.map((option) => (
                <Listbox.Option
                  key={option.value}
                  value={option.value}
                  className={({ active }) =>
                    classNames(
                      'relative cursor-pointer select-none py-2.5 pl-10 pr-4',
                      active ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                    )
                  }
                >
                  {({ selected }) => (
                    <>
                      <span
                        className={classNames(
                          'block truncate',
                          selected ? 'font-medium' : 'font-normal'
                        )}
                      >
                        {option.label}
                      </span>
                      {selected && (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
                          <CheckIcon className="w-4 h-4" />
                        </span>
                      )}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
    </div>
  );
}

export default MemberSearch;
