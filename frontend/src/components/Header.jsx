import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { logout } from "../features/auth/authSlice.js";

const NAV_ITEMS = [
  { key: "qms", label: "QMS", functional: false },
  { key: "dashboard", label: "Dashboard", functional: true },
  { key: "deviations", label: "Deviations", functional: true },
  { key: "capas", label: "CAPAs", functional: false },
  { key: "change_control", label: "Change Control", functional: false },
  { key: "audits", label: "Audits", functional: false },
  { key: "documents", label: "Documents", functional: false },
  { key: "reports", label: "Reports", functional: false },
];

export default function Header({ activeView, onViewChange, onShowToast }) {
  const dispatch = useDispatch();
  const { user } = useSelector((s) => s.auth);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [companyMenuOpen, setCompanyMenuOpen] = useState(false);

  const handleNavClick = (item) => {
    if (item.functional) {
      onViewChange(item.key);
    } else {
      if (onShowToast) {
        onShowToast(`${item.label} module is planned and coming soon.`);
      }
    }
  };

  const handleSignOut = () => {
    dispatch(logout());
  };

  const getInitials = (name) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Brand + Navigation Items */}
        <div className="flex items-center gap-6">
          {/* Logo Area */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-sm shadow-sm">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </div>
            <span className="text-base font-bold tracking-tight text-slate-900">PharmaOne-AI</span>
          </div>

          {/* Navigation Items in Exact Order */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Main Navigation">
            {NAV_ITEMS.map((item) => {
              const isActive = activeView === item.key;
              const isQms = item.key === "qms";

              if (isQms) {
                return (
                  <span
                    key={item.key}
                    className="px-2.5 py-1 text-xs font-semibold text-slate-400 select-none cursor-default"
                  >
                    {item.label}
                  </span>
                );
              }

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => handleNavClick(item)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-slate-100 text-blue-700 font-semibold"
                      : item.functional
                      ? "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                      : "text-slate-400 hover:text-slate-500 cursor-pointer"
                  }`}
                  title={!item.functional ? "Coming soon" : undefined}
                >
                  {item.label}
                  {!item.functional && (
                    <span className="ml-1 text-[9px] text-slate-400">·</span>
                  )}
                </button>
              );
            })}

          </nav>
        </div>

        {/* Right side: Company Selector, Notifications, User Menu */}
        <div className="flex items-center gap-3">
          {/* Active Company Selector / Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setCompanyMenuOpen(!companyMenuOpen)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100 transition-colors focus:outline-none"
              aria-expanded={companyMenuOpen}
              id="company-menu-button"
            >
              <svg className="h-3.5 w-3.5 text-slate-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span className="font-medium text-slate-800 text-[11px] truncate max-w-[200px] sm:max-w-xs" title={user?.company_name || "Vasundha Pharma Chem Limited"}>
                {user?.company_name || "Vasundha Pharma Chem Limited"}
              </span>
              <svg className="h-3 w-3 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {companyMenuOpen && (
              <div className="absolute right-0 sm:left-0 mt-2 w-64 origin-top-left rounded-lg border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  Organization
                </div>
                <div className="px-3 py-2 flex items-center justify-between text-xs text-slate-800 bg-blue-50/60 font-medium">
                  <span className="truncate">{user?.company_name || "Vasundha Pharma Chem Limited"}</span>
                  <span className="ml-2 text-[10px] text-blue-700 bg-blue-100 rounded px-1.5 py-0.5 font-semibold">Active</span>
                </div>
              </div>
            )}
          </div>

          {/* Notification / Bell Icon */}
          <button
            type="button"
            className="relative rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none"
            aria-label="Notifications"
            onClick={() => onShowToast && onShowToast("No new deviation alerts")}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-blue-500 ring-2 ring-white" />
          </button>

          {/* User Menu / Avatar */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 rounded-full focus:outline-none"
              id="user-menu-button"
              aria-expanded={userMenuOpen}
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold border border-blue-200">
                {getInitials(user?.full_name)}
              </div>
              <div className="hidden lg:block text-left text-xs">
                <div className="font-semibold text-slate-800 leading-tight">{user?.full_name || "User"}</div>
                <div className="text-[10px] text-slate-400 font-medium leading-none">{user?.role || "Staff"}</div>
              </div>
              <svg className="h-3.5 w-3.5 text-slate-400 hidden lg:block" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 origin-top-right rounded-lg border border-slate-200 bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                <div className="border-b border-slate-100 px-4 py-2.5">
                  <p className="text-xs font-semibold text-slate-800">{user?.full_name || "Priyanshu"}</p>
                  <p className="text-[11px] text-slate-500 truncate">{user?.email || "priyanshu@gmail.com"}</p>
                </div>

                <div className="py-1">
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onShowToast?.("Profile settings view coming soon");
                    }}
                    className="block w-full px-4 py-2 text-left text-xs text-slate-700 hover:bg-slate-50"
                  >
                    Profile
                  </button>
                </div>

                <div className="border-t border-slate-100 py-1">
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="block w-full px-4 py-2 text-left text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
