import { Fragment } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  XMarkIcon,
  UserCircleIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = isAuthenticated
    ? [
        { name: 'Dashboard', href: '/dashboard' },
        { name: 'Saved', href: '/dashboard?filter=saved' },
      ]
    : [
        { name: 'Features', href: '/#features' },
        { name: 'Pricing', href: '/#pricing' },
      ];

  return (
    <nav className="bg-[var(--gr-bg-secondary)] border-b border-[var(--gr-border-subtle)] sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and main nav */}
          <div className="flex">
            <Link to="/" className="flex items-center flex-shrink-0 gap-2">
              <div className="h-8 w-8 bg-[var(--gr-blue-600)] rounded-lg flex items-center justify-center shadow-md">
                <span className="text-white font-bold text-lg font-display">G</span>
              </div>
              <span className="text-xl font-display font-semibold text-[var(--gr-text-primary)]">
                GrantRadar
              </span>
            </Link>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-1">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={classNames(
                    location.pathname === item.href
                      ? 'text-[var(--gr-blue-600)] bg-[var(--gr-blue-600)]/10'
                      : 'text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)]',
                    'inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all duration-[var(--gr-transition-fast)]'
                  )}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </div>

          {/* Right side */}
          <div className="hidden sm:ml-6 sm:flex sm:items-center sm:space-x-3">
            {isAuthenticated ? (
              <Menu as="div" className="relative">
                <Menu.Button className="flex items-center gap-2 rounded-lg px-3 py-2 text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--gr-blue-600)] transition-all">
                  <UserCircleIcon className="h-6 w-6" />
                  <span className="hidden lg:block text-sm font-medium">
                    {user?.organization_name}
                  </span>
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
                  <Menu.Items className="absolute right-0 mt-2 w-56 origin-top-right rounded-xl bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] shadow-[var(--gr-shadow-lg)] py-1 focus:outline-none">
                    <div className="px-4 py-3 border-b border-[var(--gr-border-subtle)]">
                      <p className="text-sm font-medium text-[var(--gr-text-primary)]">{user?.organization_name}</p>
                      <p className="text-xs text-[var(--gr-text-tertiary)] truncate">{user?.email}</p>
                    </div>
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
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center sm:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-lg text-[var(--gr-text-secondary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--gr-blue-600)]"
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
        <div className="sm:hidden border-t border-[var(--gr-border-subtle)] bg-[var(--gr-bg-elevated)]">
          <div className="pt-2 pb-3 space-y-1 px-4">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={classNames(
                  location.pathname === item.href
                    ? 'bg-[var(--gr-blue-600)]/10 text-[var(--gr-blue-600)]'
                    : 'text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]',
                  'block px-4 py-3 rounded-lg text-base font-medium'
                )}
              >
                {item.name}
              </Link>
            ))}
          </div>
          {isAuthenticated ? (
            <div className="pt-4 pb-3 border-t border-[var(--gr-border-subtle)] px-4">
              <div className="flex items-center gap-3 mb-4">
                <UserCircleIcon className="h-10 w-10 text-[var(--gr-text-tertiary)]" />
                <div>
                  <div className="text-base font-medium text-[var(--gr-text-primary)]">
                    {user?.organization_name}
                  </div>
                  <div className="text-sm text-[var(--gr-text-tertiary)]">
                    {user?.email}
                  </div>
                </div>
              </div>
              <div className="space-y-1">
                <Link
                  to="/settings"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg text-base font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  <Cog6ToothIcon className="h-5 w-5" />
                  Settings
                </Link>
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="flex w-full items-center gap-3 px-4 py-3 rounded-lg text-base font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  Sign out
                </button>
              </div>
            </div>
          ) : (
            <div className="pt-4 pb-3 border-t border-[var(--gr-border-subtle)] px-4 space-y-2">
              <Link
                to="/auth"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-4 py-3 rounded-lg text-base font-medium text-[var(--gr-text-secondary)] hover:bg-[var(--gr-bg-hover)] hover:text-[var(--gr-text-primary)]"
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
          )}
        </div>
      </Transition>
    </nav>
  );
}

export default Navbar;
