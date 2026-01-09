import { Fragment, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Transition, Popover } from '@headlessui/react';
import {
  Bars3Icon,
  XMarkIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  ChevronDownIcon,
  ChartBarIcon,
  CalendarDaysIcon,
  ClockIcon,
  BoltIcon,
  BuildingLibraryIcon,
  DocumentTextIcon,
  SparklesIcon,
  PuzzlePieceIcon,
  ViewColumnsIcon,
  HomeIcon,
  UserGroupIcon,
  BriefcaseIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { NotificationBellContainer } from './notifications';

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Navigation item type
interface NavItem {
  name: string;
  href: string;
  icon?: React.ElementType;
  description?: string;
}

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Core navigation - always visible
  const coreNavigation: NavItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'Portfolio', href: '/portfolio', icon: BriefcaseIcon },
    { name: 'Pipeline', href: '/kanban', icon: ViewColumnsIcon },
    { name: 'Team', href: '/team', icon: UserGroupIcon },
  ];

  // Tools dropdown items
  const toolsNavigation: NavItem[] = [
    { name: 'Deadlines', href: '/deadlines', icon: ClockIcon, description: 'Track upcoming deadlines' },
    { name: 'Calendar', href: '/calendar', icon: CalendarDaysIcon, description: 'Visual calendar view' },
    { name: 'Analytics', href: '/analytics', icon: ChartBarIcon, description: 'Insights & metrics' },
    { name: 'Forecast', href: '/forecast', icon: BoltIcon, description: 'Funding predictions' },
  ];

  // Resources dropdown items
  const resourcesNavigation: NavItem[] = [
    { name: 'Funders', href: '/funders', icon: BuildingLibraryIcon, description: 'Funder insights & profiles' },
    { name: 'Templates', href: '/templates', icon: DocumentTextIcon, description: 'Application templates' },
    { name: 'AI Tools', href: '/ai-tools', icon: SparklesIcon, description: 'AI-powered assistance' },
    { name: 'Integrations', href: '/integrations', icon: PuzzlePieceIcon, description: 'Connect your tools' },
  ];

  // Public navigation
  const publicNavigation: NavItem[] = [
    { name: 'Features', href: '/#features' },
    { name: 'Pricing', href: '/pricing' },
  ];

  // Check if current path is in a group
  const isGroupActive = (items: NavItem[]) => {
    return items.some(item => location.pathname === item.href);
  };

  // Desktop dropdown component
  const DropdownMenu = ({ label, items, isActive }: { label: string; items: NavItem[]; isActive: boolean }) => (
    <Popover className="relative">
      {({ open }) => (
        <>
          <Popover.Button
            className={classNames(
              'inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 outline-none',
              open || isActive
                ? 'text-[var(--gr-blue-600)] bg-[var(--gr-blue-50)]'
                : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)]'
            )}
          >
            {label}
            <ChevronDownIcon
              className={classNames(
                'w-4 h-4 transition-transform duration-200',
                open ? 'rotate-180' : ''
              )}
            />
          </Popover.Button>

          <Transition
            as={Fragment}
            enter="transition ease-out duration-200"
            enterFrom="opacity-0 translate-y-1"
            enterTo="opacity-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="opacity-100 translate-y-0"
            leaveTo="opacity-0 translate-y-1"
          >
            <Popover.Panel className="absolute left-0 z-50 mt-2 w-64 origin-top-left">
              <div className="overflow-hidden rounded-xl bg-white shadow-lg ring-1 ring-black/5">
                <div className="p-2">
                  {items.map((item) => {
                    const Icon = item.icon;
                    const isItemActive = location.pathname === item.href;
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={classNames(
                          'flex items-start gap-3 rounded-lg p-3 transition-colors',
                          isItemActive
                            ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)]'
                            : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]'
                        )}
                      >
                        {Icon && (
                          <Icon className={classNames(
                            'w-5 h-5 flex-shrink-0 mt-0.5',
                            isItemActive ? 'text-[var(--gr-blue-600)]' : ''
                          )} />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium">{item.name}</p>
                          {item.description && (
                            <p className="text-xs text-[var(--gr-text-tertiary)] mt-0.5">{item.description}</p>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            </Popover.Panel>
          </Transition>
        </>
      )}
    </Popover>
  );

  return (
    <nav className="bg-white border-b border-[var(--gr-border-default)] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and main nav */}
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center flex-shrink-0 gap-2.5 group">
              <div className="h-9 w-9 bg-gradient-to-br from-[var(--gr-blue-500)] to-[var(--gr-blue-700)] rounded-xl flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
                <span className="text-white font-bold text-lg font-display">G</span>
              </div>
              <span className="text-xl font-display font-semibold text-[var(--gr-text-primary)] hidden sm:block">
                GrantRadar
              </span>
            </Link>

            {/* Desktop Navigation */}
            {isAuthenticated && (
              <div className="hidden lg:flex items-center gap-1">
                {/* Core nav items */}
                {coreNavigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={classNames(
                      'inline-flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                      location.pathname === item.href
                        ? 'text-[var(--gr-blue-600)] bg-[var(--gr-blue-50)]'
                        : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)]'
                    )}
                  >
                    {item.name}
                  </Link>
                ))}

                {/* Divider */}
                <div className="w-px h-6 bg-[var(--gr-border-default)] mx-2" />

                {/* Dropdown menus */}
                <DropdownMenu
                  label="Tools"
                  items={toolsNavigation}
                  isActive={isGroupActive(toolsNavigation)}
                />
                <DropdownMenu
                  label="Resources"
                  items={resourcesNavigation}
                  isActive={isGroupActive(resourcesNavigation)}
                />
              </div>
            )}

            {/* Public navigation */}
            {!isAuthenticated && (
              <div className="hidden sm:flex items-center gap-1">
                {publicNavigation.map((item) => (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] px-3 py-2 text-sm font-medium rounded-lg hover:bg-[var(--gr-bg-hover)] transition-all"
                  >
                    {item.name}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {isAuthenticated && (
              <NotificationBellContainer />
            )}
            {isAuthenticated ? (
              <Menu as="div" className="relative">
                <Menu.Button className="flex items-center gap-2 rounded-lg px-3 py-2 text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--gr-blue-500)] transition-all">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--gr-blue-400)] to-[var(--gr-blue-600)] flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user?.organization_name?.charAt(0).toUpperCase() || 'U'}
                    </span>
                  </div>
                  <span className="hidden md:block text-sm font-medium max-w-[150px] truncate">
                    {user?.organization_name || 'Account'}
                  </span>
                  <ChevronDownIcon className="w-4 h-4 hidden md:block" />
                </Menu.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Menu.Items className="absolute right-0 mt-2 w-60 origin-top-right rounded-xl bg-white border border-[var(--gr-border-default)] shadow-lg py-1 focus:outline-none">
                    <div className="px-4 py-3 border-b border-[var(--gr-border-subtle)]">
                      <p className="text-sm font-medium text-[var(--gr-text-primary)]">{user?.organization_name}</p>
                      <p className="text-xs text-[var(--gr-text-tertiary)] truncate mt-0.5">{user?.email}</p>
                    </div>
                    <div className="py-1">
                      <Menu.Item>
                        {({ active }) => (
                          <Link
                            to="/settings"
                            className={classNames(
                              active ? 'bg-[var(--gr-bg-hover)]' : '',
                              'flex items-center gap-3 px-4 py-2.5 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                            )}
                          >
                            <Cog6ToothIcon className="h-5 w-5" />
                            Settings
                          </Link>
                        )}
                      </Menu.Item>
                      <Menu.Item>
                        {({ active }) => (
                          <button
                            onClick={logout}
                            className={classNames(
                              active ? 'bg-[var(--gr-bg-hover)]' : '',
                              'flex w-full items-center gap-3 px-4 py-2.5 text-sm text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)]'
                            )}
                          >
                            <ArrowRightOnRectangleIcon className="h-5 w-5" />
                            Sign out
                          </button>
                        )}
                      </Menu.Item>
                    </div>
                  </Menu.Items>
                </Transition>
              </Menu>
            ) : (
              <>
                <Link
                  to="/auth"
                  className="text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] text-sm font-medium px-4 py-2 rounded-lg hover:bg-[var(--gr-bg-hover)] transition-all"
                >
                  Sign in
                </Link>
                <Link
                  to="/auth?mode=signup"
                  className="btn-primary"
                >
                  Get Started
                </Link>
              </>
            )}

            {/* Mobile menu button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden inline-flex items-center justify-center p-2 rounded-lg text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--gr-blue-500)]"
            >
              <span className="sr-only">Open main menu</span>
              {mobileMenuOpen ? (
                <XMarkIcon className="block h-6 w-6" />
              ) : (
                <Bars3Icon className="block h-6 w-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <Transition
        show={mobileMenuOpen}
        as={Fragment}
        enter="transition ease-out duration-200"
        enterFrom="opacity-0 -translate-y-4"
        enterTo="opacity-100 translate-y-0"
        leave="transition ease-in duration-150"
        leaveFrom="opacity-100 translate-y-0"
        leaveTo="opacity-0 -translate-y-4"
      >
        <div className="lg:hidden border-t border-[var(--gr-border-subtle)] bg-white">
          {isAuthenticated ? (
            <div className="py-3 px-4 space-y-1 max-h-[calc(100vh-8rem)] overflow-y-auto">
              {/* Core navigation */}
              <div className="pb-2 mb-2 border-b border-[var(--gr-border-subtle)]">
                <p className="px-3 py-2 text-xs font-semibold text-[var(--gr-text-tertiary)] uppercase tracking-wider">
                  Main
                </p>
                {coreNavigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={classNames(
                        location.pathname === item.href
                          ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)]'
                          : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]',
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium'
                      )}
                    >
                      {Icon && <Icon className="w-5 h-5" />}
                      {item.name}
                    </Link>
                  );
                })}
              </div>

              {/* Tools */}
              <div className="pb-2 mb-2 border-b border-[var(--gr-border-subtle)]">
                <p className="px-3 py-2 text-xs font-semibold text-[var(--gr-text-tertiary)] uppercase tracking-wider">
                  Tools
                </p>
                {toolsNavigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={classNames(
                        location.pathname === item.href
                          ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)]'
                          : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]',
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium'
                      )}
                    >
                      {Icon && <Icon className="w-5 h-5" />}
                      {item.name}
                    </Link>
                  );
                })}
              </div>

              {/* Resources */}
              <div className="pb-2">
                <p className="px-3 py-2 text-xs font-semibold text-[var(--gr-text-tertiary)] uppercase tracking-wider">
                  Resources
                </p>
                {resourcesNavigation.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={classNames(
                        location.pathname === item.href
                          ? 'bg-[var(--gr-blue-50)] text-[var(--gr-blue-700)]'
                          : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]',
                        'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium'
                      )}
                    >
                      {Icon && <Icon className="w-5 h-5" />}
                      {item.name}
                    </Link>
                  );
                })}
              </div>

              {/* User section */}
              <div className="pt-3 mt-2 border-t border-[var(--gr-border-subtle)]">
                <div className="flex items-center gap-3 px-3 py-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--gr-blue-400)] to-[var(--gr-blue-600)] flex items-center justify-center">
                    <span className="text-white font-medium">
                      {user?.organization_name?.charAt(0).toUpperCase() || 'U'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--gr-text-primary)] truncate">
                      {user?.organization_name}
                    </p>
                    <p className="text-xs text-[var(--gr-text-tertiary)] truncate">
                      {user?.email}
                    </p>
                  </div>
                </div>
                <Link
                  to="/settings"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  <Cog6ToothIcon className="h-5 w-5" />
                  Settings
                </Link>
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="flex w-full items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  Sign out
                </button>
              </div>
            </div>
          ) : (
            <div className="py-3 px-4 space-y-1">
              {publicNavigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-3 rounded-lg text-sm font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  {item.name}
                </Link>
              ))}
              <div className="pt-3 mt-2 border-t border-[var(--gr-border-subtle)] space-y-2">
                <Link
                  to="/auth"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-3 rounded-lg text-sm font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  Sign in
                </Link>
                <Link
                  to="/auth?mode=signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block btn-primary w-full text-center"
                >
                  Get Started
                </Link>
              </div>
            </div>
          )}
        </div>
      </Transition>
    </nav>
  );
}

export default Navbar;
